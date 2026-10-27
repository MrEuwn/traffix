"""D2 forecasting invariants: leakage, split integrity, metric definitions, artefact consistency."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.forecast import evaluate as fe
from ml.forecast.features import (
    FEATURE_COLUMNS,
    HORIZON_MINUTES,
    assert_no_leakage,
    build_windows,
    engineer_features,
)


@pytest.fixture(scope="module")
def series() -> pd.DataFrame:
    raw = pd.read_csv(fe.HYBRID_RAW)
    agg = fe.aggregate_approaches(raw)
    agg["intersectionId"] = fe.SERIES_ID
    return agg


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return fe.load_series()


@pytest.fixture(scope="module")
def v4_frame() -> pd.DataFrame:
    return fe.load_v4()


@pytest.mark.parametrize("horizon", list(HORIZON_MINUTES))
def test_v4_splits_keep_windows_inside_one_intersection(v4_frame, horizon):
    masks = fe.split_masks(v4_frame, horizon)
    rows = np.flatnonzero(masks["test"])
    assert v4_frame.loc[rows, "intersectionId"].nunique() == 6
    # The longest window (60 rows) ending at any eligible row stays inside its own series.
    assert (v4_frame["pos"].to_numpy()[rows] >= 59).all()
    preds = fe.baseline_predictions(v4_frame, rows, horizon)
    same = v4_frame["intersectionId"].to_numpy()
    seasonal_idx = rows + HORIZON_MINUTES[horizon] - 1440
    assert (same[seasonal_idx] == same[rows]).all()
    assert np.isfinite(preds["moving_average_15"]).all()


def test_feature_manifest_has_no_target_columns():
    assert len(FEATURE_COLUMNS) == 41
    assert_no_leakage(FEATURE_COLUMNS)
    with pytest.raises(ValueError):
        assert_no_leakage([*FEATURE_COLUMNS, "target_volume_15m"])


def test_features_match_data_team_notebook_output(frame):
    ready = pd.read_csv(fe.LSTM_READY)
    ready = ready[ready["intersectionId"] == fe.SERIES_ID]
    ours = frame.set_index("timestamp_wib").loc[pd.to_datetime(ready["timestamp_wib"])]
    diff = np.abs(ours[FEATURE_COLUMNS].to_numpy(float) - ready[FEATURE_COLUMNS].to_numpy(float))
    assert diff.max() < 1e-6


def test_changing_the_future_never_changes_past_features(series):
    """Perturb every raw input after minute `cut`; features up to `cut` must not move."""
    cut = len(series) // 2
    base = engineer_features(series, with_targets=False)
    poisoned = series.copy()
    poisoned.loc[poisoned.index[cut + 1:], ["volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh"]] *= 9
    after = engineer_features(poisoned, with_targets=False)
    before = base[FEATURE_COLUMNS].iloc[: cut + 1].to_numpy(float)
    later = after[FEATURE_COLUMNS].iloc[: cut + 1].to_numpy(float)
    assert np.nanmax(np.abs(before - later)) == 0


def test_targets_are_point_volume_at_t_plus_h(frame):
    vol = frame["volume_veh_per_hour"].to_numpy()
    for horizon, minutes in HORIZON_MINUTES.items():
        target = frame[f"target_volume_{horizon}"].to_numpy()
        np.testing.assert_allclose(target[: len(vol) - minutes], vol[minutes:])


@pytest.mark.parametrize("horizon", list(HORIZON_MINUTES))
def test_splits_disjoint_and_targets_stay_inside_split(frame, horizon):
    masks = fe.split_masks(frame, horizon)
    assert not (masks["train"] & masks["validation"]).any()
    assert not (masks["validation"] & masks["test"]).any()
    minutes = HORIZON_MINUTES[horizon]
    start = frame["timestamp_wib"].iloc[0].normalize()
    for name, (lo, hi) in fe.SPLIT_DAYS.items():
        issue = frame.loc[masks[name], "timestamp_wib"]
        target_day = ((issue + pd.Timedelta(minutes=minutes) - start).dt.days + 1)
        assert target_day.between(lo, hi).all(), name
        assert masks[name].sum() > 0


def test_windows_end_at_issue_row_and_never_look_ahead():
    matrix = np.arange(100, dtype=float).reshape(100, 1)
    windows = build_windows(matrix, np.array([20, 99]), 15)
    assert windows[0, -1, 0] == 20 and windows[0, 0, 0] == 6
    assert windows[1, -1, 0] == 99
    with pytest.raises(ValueError):
        build_windows(matrix, np.array([3]), 15)


def test_baselines_only_read_the_past(frame):
    rows = np.flatnonzero(fe.split_masks(frame, "4h")["test"])
    preds = fe.baseline_predictions(frame, rows, "4h")
    vol = frame["volume_veh_per_hour"].to_numpy()
    np.testing.assert_allclose(preds["persistence"], vol[rows])
    np.testing.assert_allclose(preds["seasonal_naive_1d"], vol[rows + 240 - 1440])


def test_metric_definitions_and_zero_target_policy():
    m = fe.regression_metrics(np.array([0.0, 100.0, 200.0]), np.array([10.0, 110.0, 180.0]))
    assert m["mae"] == pytest.approx(40 / 3)
    assert m["wape_pct"] == pytest.approx(40 / 300 * 100)
    assert m["mape_zero_targets_skipped"] == 1
    assert m["mape_pct"] == pytest.approx((10 / 100 + 20 / 200) / 2 * 100)
    assert fe.improvement_pct(100.0, 80.0) == pytest.approx(20.0)
    assert fe.improvement_pct(100.0, 120.0) == pytest.approx(-20.0)


EVAL = fe.ARTIFACT_DIR / "forecast_evaluation.json"


@pytest.mark.skipif(not EVAL.exists(), reason="run backend/scripts/run_d2_evaluation.py first")
def test_headline_metrics_recompute_from_saved_predictions():
    payload = json.loads(EVAL.read_text(encoding="utf-8"))
    root = Path(fe.ROOT)
    for horizon, data in payload["horizons"].items():
        pred = pd.read_csv(root / data["predictions_csv"])
        assert len(pred) == data["n"]["test"]
        for row in data["comparison"]:
            recomputed = fe.regression_metrics(pred["actual"].to_numpy(), pred[row["model"]].to_numpy())
            # CSV stores 2 decimals; allow rounding noise.
            assert recomputed["mae"] == pytest.approx(row["test"]["mae"], abs=0.01), (horizon, row["model"])
