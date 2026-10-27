"""Shared feature engineering for the traffic-volume forecaster.

One implementation, used by the D2 evaluation (`backend/scripts/run_d2_evaluation.py`)
and by runtime inference (`ml/predictor.py`), so the served model sees exactly the
features it was evaluated on. It reproduces the Data team notebook
(`data/data_process/Data_Processing_&_Analysis.ipynb`, cells 24-28); the audit checks
the recomputation against `traffix_lstm_ready.csv` to 1e-9.

Every feature at minute t uses observations at minutes <= t only:
lags are positive shifts, rolling windows are taken over `shift(1)`.
Targets are the point volume at t + horizon and are never features.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FEATURE_COLUMNS_PATH = ROOT / "data" / "data_process" / "feature_columns.json"

HORIZON_MINUTES: dict[str, int] = {"15m": 15, "2h": 120, "4h": 240}
TARGET_COLUMNS: dict[str, str] = {h: f"target_volume_{h}" for h in HORIZON_MINUTES}

# Raw per-minute, per-intersection columns both the hybrid dataset and the v4 replay carry.
RAW_COLUMNS = [
    "timestamp_wib",
    "intersectionId",
    "vehicle_count_1min",
    "volume_veh_per_hour",
    "avg_speed_kmh",
    "queue_length_veh",
    "wait_time_min",
    "green_seconds",
    "density_percent",
    "weather_condition",
    "weather_temp_c",
    "accident_count",
    "roadwork_flag",
    "event_flag",
]

WEATHER_LEVELS = ["Clear", "Cloudy", "Hot", "Rain"]

# Indonesian public holidays inside the simulated range. Used only when the
# `holidays` package is not installed; the notebook used `holidays.ID`.
_FALLBACK_HOLIDAYS = {"2026-05-01", "2026-05-14"}

# Longest look-back a feature needs (lag_60, roll_*_60 over shift(1)).
MAX_LOOKBACK = 61


def load_feature_columns(path: Path = FEATURE_COLUMNS_PATH) -> list[str]:
    """Ordered model input columns (the contract shared with the LSTM scalers)."""
    with path.open("r", encoding="utf-8") as handle:
        columns = json.load(handle)
    if not isinstance(columns, list) or not columns:
        raise ValueError(f"feature_columns.json is empty or malformed: {path}")
    return [str(c) for c in columns]


FEATURE_COLUMNS = load_feature_columns()


def forbidden_feature(column: str) -> bool:
    """A column is forbidden as input when it encodes a future value."""
    return column.startswith("target_") or column.startswith("future_")


def assert_no_leakage(columns: list[str]) -> None:
    """Fail hard if any target/future column is used as a model input."""
    leaked = [c for c in columns if forbidden_feature(c)]
    if leaked:
        raise ValueError(f"leakage: forbidden columns among model inputs: {leaked}")


def _holiday_flags(dates: pd.Series) -> pd.Series:
    try:
        import holidays  # type: ignore[import-not-found]

        years = sorted({d.year for d in dates})
        calendar = holidays.country_holidays("ID", years=years)
        return dates.map(lambda d: int(d in calendar))
    except ImportError:
        return dates.map(lambda d: int(d.isoformat() in _FALLBACK_HOLIDAYS))


def engineer_features(raw: pd.DataFrame, *, with_targets: bool = True) -> pd.DataFrame:
    """Build the 41 model features (and optionally the targets) per intersection.

    Args:
        raw: Per-minute rows with `RAW_COLUMNS`. Each intersection must be a
            contiguous 1-minute series; gaps raise instead of silently shifting
            lags across missing minutes.
        with_targets: Also attach `target_volume_{15m,2h,4h}` (future point volume).

    Returns:
        Frame sorted by (intersectionId, timestamp) with identifiers, the
        feature columns and, if requested, target columns. Rows whose look-back
        is incomplete keep NaN features; callers drop them explicitly.
    """
    missing = [c for c in RAW_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"raw frame lacks columns: {missing}")

    df = raw[RAW_COLUMNS].copy()
    df["timestamp_wib"] = pd.to_datetime(df["timestamp_wib"])
    df = df.sort_values(["intersectionId", "timestamp_wib"]).reset_index(drop=True)
    assert_contiguous(df)

    ts = df["timestamp_wib"]
    df["hour"] = ts.dt.hour
    df["minute"] = ts.dt.minute
    df["day"] = ts.dt.day
    df["day_of_week"] = ts.dt.day_of_week
    df["month"] = ts.dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_holiday"] = _holiday_flags(ts.dt.date).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    group = df.groupby("intersectionId", sort=False)
    volume = group["volume_veh_per_hour"]
    for lag in (1, 5, 15, 30, 60):
        df[f"lag_{lag}"] = volume.shift(lag)
    df["lag_speed_15"] = group["avg_speed_kmh"].shift(15)
    df["lag_queue_15"] = group["queue_length_veh"].shift(15)

    past = volume.shift(1)
    past_group = past.groupby(df["intersectionId"], sort=False)
    for window, stats in ((15, ("mean", "std", "min", "max", "median")), (60, ("mean", "std", "min", "max"))):
        rolling = past_group.rolling(window)
        for stat in stats:
            values = getattr(rolling, stat)()
            df[f"roll_{stat}_{window}"] = values.reset_index(level=0, drop=True)
    df["delta_volume"] = volume.diff()

    weather = df["weather_condition"].astype(str)
    for level in WEATHER_LEVELS:
        df[f"weather_condition_{level}"] = (weather == level).astype(int)

    if with_targets:
        for horizon, minutes in HORIZON_MINUTES.items():
            df[TARGET_COLUMNS[horizon]] = volume.shift(-minutes)

    keep = ["timestamp_wib", "intersectionId", *FEATURE_COLUMNS]
    if with_targets:
        keep += list(TARGET_COLUMNS.values())
    return df[keep]


def assert_contiguous(df: pd.DataFrame) -> None:
    """Every intersection series must be strictly 1-minute spaced, no duplicates."""
    for intersection, block in df.groupby("intersectionId", sort=False):
        steps = block["timestamp_wib"].diff().dropna()
        if len(steps) and not (steps == pd.Timedelta(minutes=1)).all():
            bad = int((steps != pd.Timedelta(minutes=1)).sum())
            raise ValueError(f"{intersection}: {bad} non 1-minute steps (gap or duplicate)")


def window_end_indices(n_rows: int, seq_len: int) -> np.ndarray:
    """Row indices that can end a full window of `seq_len` rows."""
    return np.arange(seq_len - 1, n_rows)


def build_windows(matrix: np.ndarray, ends: np.ndarray, seq_len: int) -> np.ndarray:
    """Stack windows `matrix[end - seq_len + 1 : end + 1]` (issue row inclusive).

    Args:
        matrix: (T, F) scaled features of ONE contiguous series.
        ends: Issue-time row indices (each >= seq_len - 1).
        seq_len: Window length in minutes.

    Returns:
        (len(ends), seq_len, F) float32 array.
    """
    if len(ends) and int(ends.min()) < seq_len - 1:
        raise ValueError("window would start before the series")
    offsets = np.arange(-seq_len + 1, 1)
    return matrix[ends[:, None] + offsets[None, :]].astype(np.float32)
