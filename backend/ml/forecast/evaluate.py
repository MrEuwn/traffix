"""D2 forecasting experiment: data, split, baselines, LSTM, metrics.

Called by `backend/scripts/run_d2_evaluation.py`. Nothing here prints a number it
did not compute: every metric comes from arrays of saved per-sample predictions.

Protocol (frozen in docs/D2_RESEARCH_PROTOCOL.md), run on two synthetic datasets:
- `v4_replay` (primary, served): the six intersections of the v4 replay the app runs.
- `hybrid_tmg` (secondary): TMG-1012 rebuilt from the raw hybrid simulator output by
  approach aggregation (the rows the Data team notebook trained on).
- Issue time t, horizon h in {15, 120, 240} minutes, target = point volume at t+h.
- Split by calendar day of BOTH issue and target time: days 1-5 train, day 6
  validation, day 7 test. Samples whose target crosses into the next split are
  purged. Look-back windows may reach into earlier days (past data only).
- Scalers are fitted on training rows only. Model choice per horizon uses the
  validation MAE only; the test day is scored once after selection.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from ml.forecast.features import (
    FEATURE_COLUMNS,
    HORIZON_MINUTES,
    TARGET_COLUMNS,
    assert_no_leakage,
    build_windows,
    engineer_features,
)

ROOT = Path(__file__).resolve().parents[3]
HYBRID_RAW = ROOT / "data" / "data_synthetic" / "hybrid_traffic_7d.csv"
LSTM_READY = ROOT / "data" / "data_process" / "traffix_lstm_ready.csv"
V4_REPLAY = ROOT / "data" / "data_synthetic" / "v4" / "live_replay_7d.csv.gz"
LEGACY_ARTIFACTS = ROOT / "LSTM Training" / "artifacts"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_DIR = ARTIFACT_DIR / "models"

SEED = 42
SERIES_ID = "TMG-1012"
SPLIT_DAYS = {"train": (1, 5), "validation": (6, 6), "test": (7, 7)}
BOOTSTRAP_BLOCK = 60  # minutes; keeps autocorrelated errors together
BOOTSTRAP_REPS = 2000

# Small, pre-declared search spaces. Selection is on validation MAE only.
LSTM_GRID = (
    {"seq_len": 15, "learning_rate": 1e-3},
    {"seq_len": 15, "learning_rate": 5e-4},
    {"seq_len": 60, "learning_rate": 1e-3},
    {"seq_len": 60, "learning_rate": 5e-4},
)
# v4 has six series (~6x the samples): a two-point grid and larger batches keep the
# CPU budget under control. Declared up front, not adjusted after seeing results.
LSTM_GRID_V4 = (
    {"seq_len": 15, "learning_rate": 1e-3},
    {"seq_len": 60, "learning_rate": 1e-3},
)
MAX_SEQ_LEN = max(cfg["seq_len"] for cfg in LSTM_GRID + LSTM_GRID_V4)
LSTM_FIXED = {"arch": "lstm_light", "dropout": 0.1, "loss": "mae", "max_epochs": 60, "patience": 8}


@dataclass(frozen=True)
class Experiment:
    """One dataset + its pre-declared LSTM search budget."""

    key: str
    title: str
    lstm_grid: tuple
    batch_size: int
    served: bool


EXPERIMENTS = {
    "v4_replay": Experiment(
        key="v4_replay",
        title="Replay v4 — 6 simpang (data yang dijalankan aplikasi)",
        lstm_grid=LSTM_GRID_V4,
        batch_size=128,
        served=True,
    ),
    "hybrid_tmg": Experiment(
        key="hybrid_tmg",
        title="Hybrid TMG-1012 — data latih notebook asli",
        lstm_grid=LSTM_GRID,
        batch_size=32,
        served=False,
    ),
}
RIDGE_ALPHAS = [0.1, 1.0, 10.0, 100.0]
HGB_GRID = [
    {"learning_rate": 0.05, "max_leaf_nodes": 15},
    {"learning_rate": 0.05, "max_leaf_nodes": 31},
    {"learning_rate": 0.1, "max_leaf_nodes": 15},
    {"learning_rate": 0.1, "max_leaf_nodes": 31},
]

MODEL_LABELS = {
    "lstm": "LSTM (model utama)",
    "persistence": "Persistence (volume saat ini)",
    "moving_average_15": "Rata-rata 15 menit terakhir",
    "seasonal_naive_1d": "Seasonal naive (kemarin, jam sama)",
    "ridge": "Ridge regression",
    "hist_gradient_boosting": "HistGradientBoosting",
}
BASELINES = ["persistence", "moving_average_15", "seasonal_naive_1d"]
COMPARATORS = ["ridge", "hist_gradient_boosting"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mode_or_first(series: pd.Series):
    values = series.dropna()
    mode = values.mode()
    return mode.iloc[0] if len(mode) else values.iloc[0]


def aggregate_approaches(raw: pd.DataFrame) -> pd.DataFrame:
    """Approach rows -> one intersection row per minute (notebook cell 21 rules)."""
    return raw.groupby(["intersectionId", "tick"], as_index=False).agg(
        timestamp_wib=("timestamp_wib", "first"),
        vehicle_count_1min=("vehicle_count_1min", "sum"),
        volume_veh_per_hour=("volume_veh_per_hour", "sum"),
        avg_speed_kmh=("avg_speed_kmh", "mean"),
        queue_length_veh=("queue_length_veh", "sum"),
        wait_time_min=("wait_time_min", "sum"),
        green_seconds=("green_seconds", "mean"),
        density_percent=("density_percent", "mean"),
        weather_condition=("weather_condition", _mode_or_first),
        weather_temp_c=("weather_temp_c", "mean"),
        accident_count=("accident_count", "max"),
        roadwork_flag=("roadwork_flag", "max"),
        event_flag=("event_flag", "max"),
    )


def _index_days(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.reset_index(drop=True)
    start = frame["timestamp_wib"].min().normalize()
    frame["day_index"] = (frame["timestamp_wib"] - start).dt.days + 1
    frame["pos"] = frame.groupby("intersectionId", sort=False).cumcount()
    return frame


def load_series() -> pd.DataFrame:
    """Raw hybrid output -> TMG-1012 per-minute features + targets."""
    raw = pd.read_csv(HYBRID_RAW)
    series = aggregate_approaches(raw)
    series["intersectionId"] = SERIES_ID  # notebook cell 10 renames JKT-TMG-SIM-01
    return _index_days(engineer_features(series, with_targets=True))


def load_v4() -> pd.DataFrame:
    """v4 replay (already one row per intersection per minute) -> features + targets.

    Targets are recomputed from the replay volume; the file's own target_* columns
    are per-section means on another scale and are ignored.
    """
    return _index_days(engineer_features(pd.read_csv(V4_REPLAY), with_targets=True))


def load_experiment(key: str) -> pd.DataFrame:
    return {"v4_replay": load_v4, "hybrid_tmg": load_series}[key]()


def split_masks(frame: pd.DataFrame, horizon: str) -> dict[str, np.ndarray]:
    """Eligible issue rows per split for one horizon (target inside the same split)."""
    minutes = HORIZON_MINUTES[horizon]
    issue_day = frame["day_index"].to_numpy()
    start = frame["timestamp_wib"].iloc[0].normalize()
    target_time = frame["timestamp_wib"] + pd.Timedelta(minutes=minutes)
    target_day = ((target_time - start).dt.days + 1).to_numpy()
    complete = frame[FEATURE_COLUMNS].notna().all(axis=1)
    # Every candidate scores the same rows: the longest LSTM window must fit
    # entirely inside rows with complete features of the SAME intersection.
    first_complete = complete.groupby(frame["intersectionId"], sort=False).transform(
        lambda s: int(np.argmax(s.to_numpy())))
    complete = complete.to_numpy() & (frame["pos"].to_numpy() >= first_complete.to_numpy() + MAX_SEQ_LEN - 1)
    has_target = frame[TARGET_COLUMNS[horizon]].notna().to_numpy()
    masks = {}
    for name, (lo, hi) in SPLIT_DAYS.items():
        masks[name] = (
            (issue_day >= lo) & (issue_day <= hi)
            & (target_day >= lo) & (target_day <= hi)
            & complete & has_target
        )
    return masks


# ---------------------------------------------------------------- metrics

def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int]:
    """MAE, RMSE, WAPE, sMAPE, MAPE (nonzero targets only), R2, bias.

    Zero-target policy: MAPE skips targets equal to 0 and reports how many were
    skipped; WAPE = sum|e| / sum|y| and sMAPE stay defined on every sample.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    abs_err = np.abs(err)
    nonzero = y_true != 0
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    smape = np.where(denom == 0, 0.0, abs_err / np.where(denom == 0, 1, denom))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "n": int(len(y_true)),
        "mae": float(abs_err.mean()),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "wape_pct": float(abs_err.sum() / np.abs(y_true).sum() * 100),
        "smape_pct": float(smape.mean() * 100),
        "mape_pct": float(np.mean(abs_err[nonzero] / np.abs(y_true[nonzero])) * 100),
        "mape_zero_targets_skipped": int((~nonzero).sum()),
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "bias": float(err.mean()),
    }


def improvement_pct(baseline_error: float, model_error: float) -> float:
    """(baseline - model) / baseline * 100; positive = model has lower error."""
    return float((baseline_error - model_error) / baseline_error * 100)


def block_bootstrap_mae_diff(abs_err_model: np.ndarray, abs_err_base: np.ndarray,
                             block: int = BOOTSTRAP_BLOCK, reps: int = BOOTSTRAP_REPS,
                             seed: int = SEED) -> dict[str, float]:
    """95% moving-block bootstrap CI for MAE(model) - MAE(baseline).

    Consecutive minutes are correlated, so whole blocks are resampled.
    """
    diff = np.asarray(abs_err_model) - np.asarray(abs_err_base)
    n = len(diff)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    starts_max = max(1, n - block + 1)
    stats = np.empty(reps)
    for r in range(reps):
        starts = rng.integers(0, starts_max, size=n_blocks)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
        stats[r] = diff[idx].mean()
    return {
        "mae_diff": float(diff.mean()),
        "ci95_low": float(np.percentile(stats, 2.5)),
        "ci95_high": float(np.percentile(stats, 97.5)),
        "block_minutes": block,
        "reps": reps,
    }


# ---------------------------------------------------------------- baselines

def baseline_predictions(frame: pd.DataFrame, rows: np.ndarray, horizon: str) -> dict[str, np.ndarray]:
    """Naive forecasts using only data available at issue time t."""
    volume = frame["volume_veh_per_hour"].to_numpy()
    minutes = HORIZON_MINUTES[horizon]
    moving = (frame.groupby("intersectionId", sort=False)["volume_veh_per_hour"]
              .transform(lambda s: s.rolling(15).mean()).to_numpy())  # t-14..t inclusive
    # Same clock time as the target, one day earlier, same intersection (series are contiguous).
    seasonal_idx = rows + minutes - 1440
    if (frame["pos"].to_numpy()[rows] + minutes - 1440 < 0).any() or (seasonal_idx > rows).any():
        raise ValueError("seasonal naive would read unavailable or future data")
    return {
        "persistence": volume[rows],
        "moving_average_15": moving[rows],
        "seasonal_naive_1d": volume[seasonal_idx],
    }


# ---------------------------------------------------------------- LSTM

def _set_seeds() -> None:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf

    tf.keras.utils.set_random_seed(SEED)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:  # noqa: BLE001 - older TF builds lack the switch
        pass


def build_lstm_light(n_features: int, seq_len: int, learning_rate: float, dropout: float):
    """Same architecture as the notebook's `lstm_light` (cell 20)."""
    from tensorflow import keras
    from tensorflow.keras import layers

    inp = keras.Input(shape=(seq_len, n_features), name="input")
    x = layers.LSTM(64, return_sequences=True, name="lstm1")(inp)
    x = layers.Dropout(dropout, name="drop1")(x)
    x = layers.LSTM(32, name="lstm2")(x)
    x = layers.Dense(64, activation="relu", name="dense1")(x)
    x = layers.Dropout(dropout / 2, name="drop2")(x)
    out = layers.Dense(1, name="output")(x)
    model = keras.Model(inp, out, name="lstm_light")
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=learning_rate), loss="mae")
    return model


@dataclass
class HorizonResult:
    horizon: str
    n: dict[str, int]
    test_rows: np.ndarray
    y_test: np.ndarray
    predictions: dict[str, np.ndarray]
    val_metrics: dict[str, dict]
    test_metrics: dict[str, dict]
    selection: dict[str, dict]
    lstm_history: list[dict] = field(default_factory=list)


def run_horizon(frame: pd.DataFrame, horizon: str, feat_scaler: StandardScaler,
                experiment: Experiment, log=print) -> tuple[HorizonResult, object, StandardScaler]:
    """Fit/select every candidate on one horizon; score the test day once."""
    from tensorflow import keras

    masks = split_masks(frame, horizon)
    target = frame[TARGET_COLUMNS[horizon]].to_numpy()
    X_all = frame[FEATURE_COLUMNS].to_numpy(dtype=float)
    X_scaled = np.nan_to_num(feat_scaler.transform(X_all))
    rows = {k: np.flatnonzero(m) for k, m in masks.items()}
    n = {k: int(len(v)) for k, v in rows.items()}
    y = {k: target[v] for k, v in rows.items()}
    log(f"  [{experiment.key} {horizon}] sampel train={n['train']} val={n['validation']} test={n['test']}")

    preds_val: dict[str, np.ndarray] = {}
    preds_test: dict[str, np.ndarray] = {}
    selection: dict[str, dict] = {}

    for split, store in (("validation", preds_val), ("test", preds_test)):
        store.update(baseline_predictions(frame, rows[split], horizon))

    # Ridge — alpha by validation MAE.
    best = None
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha).fit(X_scaled[rows["train"]], y["train"])
        mae = float(np.mean(np.abs(model.predict(X_scaled[rows["validation"]]) - y["validation"])))
        if best is None or mae < best[0]:
            best = (mae, alpha, model)
    selection["ridge"] = {"alpha": best[1], "val_mae": best[0], "searched": RIDGE_ALPHAS}
    preds_val["ridge"] = best[2].predict(X_scaled[rows["validation"]])
    preds_test["ridge"] = best[2].predict(X_scaled[rows["test"]])

    # HistGradientBoosting — tiny grid by validation MAE.
    best = None
    for cfg in HGB_GRID:
        model = HistGradientBoostingRegressor(max_iter=300, random_state=SEED, **cfg)
        model.fit(X_all[rows["train"]], y["train"])
        mae = float(np.mean(np.abs(model.predict(X_all[rows["validation"]]) - y["validation"])))
        if best is None or mae < best[0]:
            best = (mae, cfg, model)
    selection["hist_gradient_boosting"] = {**best[1], "val_mae": best[0], "searched": HGB_GRID}
    preds_val["hist_gradient_boosting"] = best[2].predict(X_all[rows["validation"]])
    preds_test["hist_gradient_boosting"] = best[2].predict(X_all[rows["test"]])

    # LSTM — grid over seq_len x learning rate, chosen by validation MAE.
    target_scaler = StandardScaler().fit(y["train"].reshape(-1, 1))
    y_train_sc = target_scaler.transform(y["train"].reshape(-1, 1)).ravel()
    y_val_sc = target_scaler.transform(y["validation"].reshape(-1, 1)).ravel()
    best = None
    grid_log = []
    for cfg in experiment.lstm_grid:
        _set_seeds()
        seq_len = cfg["seq_len"]
        Xtr = build_windows(X_scaled, rows["train"], seq_len)
        Xvl = build_windows(X_scaled, rows["validation"], seq_len)
        model = build_lstm_light(len(FEATURE_COLUMNS), seq_len, cfg["learning_rate"], LSTM_FIXED["dropout"])
        t0 = time.time()
        history = model.fit(
            Xtr, y_train_sc, validation_data=(Xvl, y_val_sc),
            epochs=LSTM_FIXED["max_epochs"], batch_size=experiment.batch_size, verbose=0,
            shuffle=True,
            callbacks=[keras.callbacks.EarlyStopping(monitor="val_loss", patience=LSTM_FIXED["patience"],
                                                     restore_best_weights=True)],
        )
        pred_val = target_scaler.inverse_transform(model.predict(Xvl, verbose=0)).ravel()
        mae = float(np.mean(np.abs(pred_val - y["validation"])))
        epochs = len(history.history["loss"])
        grid_log.append({**cfg, "val_mae": mae, "epochs": epochs, "seconds": round(time.time() - t0, 1)})
        log(f"  [{experiment.key} {horizon}] LSTM seq={seq_len} lr={cfg['learning_rate']}: val MAE {mae:.1f} ({epochs} epoch)")
        if best is None or mae < best[0]:
            best = (mae, cfg, model, pred_val, history.history)
    _, cfg, lstm_model, pred_val, hist = best
    selection["lstm"] = {**cfg, **LSTM_FIXED, "batch_size": experiment.batch_size,
                         "val_mae": best[0], "grid": grid_log}
    preds_val["lstm"] = pred_val
    Xte = build_windows(X_scaled, rows["test"], cfg["seq_len"])
    preds_test["lstm"] = target_scaler.inverse_transform(lstm_model.predict(Xte, verbose=0)).ravel()
    history_rows = [
        {"epoch": i + 1, "loss": float(l), "val_loss": float(v)}
        for i, (l, v) in enumerate(zip(hist["loss"], hist["val_loss"]))
    ]

    result = HorizonResult(
        horizon=horizon,
        n=n,
        test_rows=rows["test"],
        y_test=y["test"],
        predictions=preds_test,
        val_metrics={k: regression_metrics(y["validation"], v) for k, v in preds_val.items()},
        test_metrics={k: regression_metrics(y["test"], v) for k, v in preds_test.items()},
        selection=selection,
        lstm_history=history_rows,
    )
    return result, lstm_model, target_scaler


def fit_feature_scaler(frame: pd.DataFrame) -> StandardScaler:
    """Feature scaler fitted on rows whose issue day is a training day only."""
    assert_no_leakage(FEATURE_COLUMNS)
    train_rows = (frame["day_index"] <= SPLIT_DAYS["train"][1]) & frame[FEATURE_COLUMNS].notna().all(axis=1)
    return StandardScaler().fit(frame.loc[train_rows, FEATURE_COLUMNS].to_numpy(dtype=float))


# ---------------------------------------------------------------- reproduction of the shipped notebook models

def reproduce_legacy(log=print) -> dict:
    """Re-score the shipped `LSTM Training/artifacts` models with the notebook protocol.

    Mirrors notebook cells 16, 22, 28 and 30 exactly (70/15/15 row split over the
    file order, window rows [i-seq_len, i) -> target of row i). Reports the
    recomputed numbers next to the stored metrics.json and documents the
    protocol issues that made us re-run the experiment under the D2 protocol.
    """
    import joblib
    from tensorflow import keras

    df = pd.read_csv(LSTM_READY)
    stored = json.loads((LEGACY_ARTIFACTS / "metrics.json").read_text())
    config = json.loads((LEGACY_ARTIFACTS / "best_config.json").read_text())
    feat_scaler = joblib.load(LEGACY_ARTIFACTS / "feat_scaler.joblib")
    target_scalers = joblib.load(LEGACY_ARTIFACTS / "target_scalers.joblib")
    seq_len = int(config["seq_len"])

    n = len(df)
    n_train, n_val = int(n * 0.70), int(n * 0.15)
    test = df.iloc[n_train + n_val:].reset_index(drop=True)
    X_test = feat_scaler.transform(test[FEATURE_COLUMNS].to_numpy(dtype=float))
    ends = np.arange(seq_len, len(test))
    windows = build_windows(X_test, ends - 1, seq_len)  # rows [i-seq_len, i)

    out = {"protocol": "notebook: 70/15/15 split by row order, window ends at i-1, target row i",
           "seq_len": seq_len, "n_test": int(len(ends)), "horizons": {}}
    stored_key = {"15m": "15m_optimized", "2h": "2h_optimized", "4h": "4h_optimized"}
    for horizon in HORIZON_MINUTES:
        model = keras.models.load_model(LEGACY_ARTIFACTS / f"best_lstm_{horizon}.keras", compile=False)
        pred = target_scalers[horizon].inverse_transform(model.predict(windows, verbose=0)).ravel()
        y_true = test[TARGET_COLUMNS[horizon]].to_numpy()[ends]
        recomputed = regression_metrics(y_true, pred)
        last_obs = test["volume_veh_per_hour"].to_numpy()[ends - 1]
        out["horizons"][horizon] = {
            "recomputed": recomputed,
            "stored_mape_pct": stored[stored_key[horizon]]["MAPE"],
            "stored_mae": stored[stored_key[horizon]]["MAE"],
            "mape_matches_stored": bool(abs(recomputed["mape_pct"] - stored[stored_key[horizon]]["MAPE"]) < 0.05),
            "persistence_last_observation": regression_metrics(y_true, last_obs),
        }
        log(f"  legacy {horizon}: MAPE {recomputed['mape_pct']:.3f}% (tersimpan {stored[stored_key[horizon]]['MAPE']})")

    test_ts = pd.to_datetime(test["timestamp_wib"])
    out["test_period"] = [str(test_ts.min()), str(test_ts.max())]
    out["issues_found"] = [
        "Split 70/15/15 mengikuti urutan baris file, bukan kalender: blok JKT-TMG-SIM-01 (8 Mei, data "
        "low-traffic acak yang ditambahkan di notebook) berada di set latih padahal tanggalnya sesudah set uji.",
        "Jendela urutan menutup di baris i-1 untuk memprediksi target baris i, sehingga horizon efektif "
        "16/121/241 menit, bukan 15/120/240.",
        "Baseline 'Persistence' di notebook memakai target_volume_15m baris t-1 (= volume pada t+14), "
        "yaitu nilai masa depan; itu bukan baseline yang adil.",
        "Baseline hanya dihitung untuk horizon 15 menit; 2 jam dan 4 jam tidak punya pembanding.",
        "Target validasi di tepi split boleh jatuh di periode uji (tidak ada purging).",
    ]
    return out


# ---------------------------------------------------------------- transfer check on the v4 replay

def transfer_v4(lstm_models: dict, target_scalers: dict, feat_scaler: StandardScaler,
                seq_lens: dict[str, int], log=print) -> dict:
    """Score the selected LSTMs on the v4 replay (a different simulator, 6 intersections).

    This is the data the running app feeds the model. Targets are recomputed from
    the replay volume (point volume at t+h); the replay's own target columns are a
    per-section mean and are not on the same scale, so they are not used.
    """
    replay = pd.read_csv(V4_REPLAY)
    frame = engineer_features(replay, with_targets=True)
    start = frame["timestamp_wib"].min().normalize()
    frame["day_index"] = (frame["timestamp_wib"] - start).dt.days + 1
    out = {"dataset": str(V4_REPLAY.relative_to(ROOT)), "split": "hari 7 (uji)", "horizons": {}}
    for horizon, minutes in HORIZON_MINUTES.items():
        y_all, p_all, b_all = [], [], []
        for _, block in frame.groupby("intersectionId", sort=False):
            block = block.reset_index(drop=True)
            target_time = block["timestamp_wib"] + pd.Timedelta(minutes=minutes)
            target_day = ((target_time - start).dt.days + 1).to_numpy()
            ok = ((block["day_index"].to_numpy() == 7) & (target_day == 7)
                  & block[FEATURE_COLUMNS].notna().all(axis=1).to_numpy())
            rows = np.flatnonzero(ok)
            X = np.nan_to_num(feat_scaler.transform(block[FEATURE_COLUMNS].to_numpy(dtype=float)))
            windows = build_windows(X, rows, seq_lens[horizon])
            pred = target_scalers[horizon].inverse_transform(lstm_models[horizon].predict(windows, verbose=0)).ravel()
            y_all.append(block[TARGET_COLUMNS[horizon]].to_numpy()[rows])
            p_all.append(pred)
            b_all.append(block["volume_veh_per_hour"].to_numpy()[rows])
        y, p, b = (np.concatenate(a) for a in (y_all, p_all, b_all))
        lstm_m, pers_m = regression_metrics(y, p), regression_metrics(y, b)
        out["horizons"][horizon] = {
            "lstm": lstm_m,
            "persistence": pers_m,
            "mae_improvement_pct_vs_persistence": improvement_pct(pers_m["mae"], lstm_m["mae"]),
        }
        log(f"  transfer v4 {horizon}: LSTM MAE {lstm_m['mae']:.1f} vs persistence {pers_m['mae']:.1f}")
    return out
