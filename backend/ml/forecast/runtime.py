"""Runtime feature windows for LSTM inference on the replayed dataset.

The replay file is the app's only traffic source, so the forecaster builds the
model features from it with `ml.forecast.features.engineer_features`, the same
function the D2 evaluation uses. Features at minute t depend only on minutes
<= t (enforced by the evaluation's future-perturbation check), so computing
them once for the whole file is equivalent to computing them as the replay
streams. Inference at replay minute t reads the window ending at t; nothing
after t is ever read.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd

from core.config import settings
from core.logger import get_logger
from core.paths import resolve_asset_path
from ml.forecast.features import FEATURE_COLUMNS, RAW_COLUMNS, build_windows, engineer_features

ml_logger = get_logger("ml")

EVALUATION_PATH = Path(__file__).resolve().parent / "artifacts" / "forecast_evaluation.json"


@dataclass(frozen=True)
class ForecastInput:
    """Window and context for one (intersection, replay minute)."""

    window: np.ndarray | None
    current_volume: float
    moving_average_15: float
    issue_time: pd.Timestamp
    replay_day: int

    @property
    def split(self) -> str:
        """Role of this replay day in the D2 evaluation (days 1-5 / 6 / 7)."""
        return "latih" if self.replay_day <= 5 else "validasi" if self.replay_day == 6 else "uji"


class ReplayFeatureStore:
    """Per-intersection feature matrices of the replay dataset, built once."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._frames: dict[str, pd.DataFrame] = {}
        self._positions: dict[str, dict[pd.Timestamp, int]] = {}
        self._ready = False
        self._error: str | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> str | None:
        return self._error

    def ensure_loaded(self) -> bool:
        with self._lock:
            if self._ready or self._error:
                return self._ready
            path = resolve_asset_path(settings.hybrid_traffic_dataset_path)
            try:
                raw = pd.read_csv(path)
                missing = [c for c in RAW_COLUMNS if c not in raw.columns]
                if missing:
                    raise ValueError(f"replay lacks forecast columns {missing}")
                frame = engineer_features(raw, with_targets=False)
                frame["timestamp_utc"] = frame["timestamp_wib"].dt.tz_convert("UTC")
                for intersection, block in frame.groupby("intersectionId", sort=False):
                    block = block.reset_index(drop=True)
                    block["moving_average_15"] = block["volume_veh_per_hour"].rolling(15).mean() \
                        if "volume_veh_per_hour" in block else np.nan
                    self._frames[str(intersection)] = block
                    self._positions[str(intersection)] = {
                        ts: i for i, ts in enumerate(block["timestamp_utc"])
                    }
                self._ready = True
                ml_logger.info("Forecast features ready for %s intersections from %s", len(self._frames), path)
            except Exception as exc:  # noqa: BLE001 - surfaced through status, never silently
                self._error = f"{type(exc).__name__}: {exc}"
                ml_logger.error("Forecast feature store failed: %s", self._error)
            return self._ready

    def get_input(self, intersection_id: str, timestamp: datetime, seq_len: int,
                  feat_scaler: object | None) -> ForecastInput | None:
        """Window ending at the replayed minute; None if the minute is unknown."""
        if not self.ensure_loaded():
            return None
        block = self._frames.get(intersection_id)
        if block is None:
            return None
        pos = self._positions[intersection_id].get(pd.Timestamp(timestamp).tz_convert("UTC"))
        if pos is None:
            return None
        current = float(block["volume_veh_per_hour"].iloc[pos]) if "volume_veh_per_hour" in block else float("nan")
        moving = block["moving_average_15"].iloc[pos]
        window = None
        if feat_scaler is not None and pos >= seq_len - 1:
            rows = block[FEATURE_COLUMNS].iloc[pos - seq_len + 1: pos + 1].to_numpy(dtype=float)
            if not np.isnan(rows).any():
                scaled = feat_scaler.transform(rows)
                window = build_windows(scaled, np.array([seq_len - 1]), seq_len)
        issue_time = block["timestamp_wib"].iloc[pos]
        return ForecastInput(
            window=window,
            current_volume=current,
            moving_average_15=float(moving) if pd.notna(moving) else current,
            issue_time=issue_time,
            replay_day=int((issue_time.normalize() - block["timestamp_wib"].iloc[0].normalize()).days) + 1,
        )


def seq_len_for(config: dict, horizon: str) -> int:
    """seq_len is a per-horizon dict in D2 artifacts and an int in the legacy config."""
    value = config.get("seq_len", 15)
    if isinstance(value, dict):
        return int(value[horizon])
    return int(value)


def load_expected_errors() -> dict[str, float]:
    """Test-day MAE per horizon of the served LSTM (trained and tested on the v4 replay).

    Empty when the evaluation artefact is absent; the API then reports no error band.
    """
    if not EVALUATION_PATH.exists():
        return {}
    payload = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    out = {}
    for horizon, data in payload.get("horizons", {}).items():
        lstm = next((r for r in data.get("comparison", []) if r["model"] == "lstm"), None)
        if lstm:
            out[horizon] = float(lstm["test"]["mae"])
    return out


feature_store = ReplayFeatureStore()
