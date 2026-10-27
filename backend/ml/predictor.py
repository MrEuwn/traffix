"""Traffix prediction service: LSTM on real replay windows, labelled heuristic fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import numpy as np
import pandas as pd

from app.state_store import LiveIntersectionState, state_store
from core.constants import HORIZONS
from core.logger import get_logger
from ml.forecast.features import HORIZON_MINUTES
from ml.forecast.runtime import ForecastInput, feature_store, load_expected_errors, seq_len_for
from ml.model_loader import (
    get_model,
    get_scalers,
    ml_fallback_active,
    models_loaded,
)
from ml.registry import registry
from sim.dataset_models import DatasetRow

ml_logger = get_logger("ml")

CongestionLevel = Literal["Low", "Medium", "High", "Critical"]


@dataclass(frozen=True)
class PredictionResult:
    """Structured prediction output for API and state store updates."""

    intersection_id: str
    horizon: str
    predicted_vehicle_count: int
    predicted_congestion_level: CongestionLevel
    confidence_score: float | None
    prediction_timestamp: str
    source: Literal["lstm", "heuristic"]
    unit: str = "kend/jam"
    current_volume: float | None = None
    issue_time_wib: str | None = None
    target_time_wib: str | None = None
    expected_mae: float | None = None
    replay_split: str | None = None


class PredictionService:
    """Generate multi-horizon predictions and sync them to live state."""

    def __init__(self) -> None:
        """Initialize prediction caches."""
        self._latest_rows: dict[str, DatasetRow] = {}
        self._expected_errors = load_expected_errors()

    def note_dataset_batch(self, rows: list[DatasetRow]) -> None:
        """Cache the latest dataset row per intersection from a replay batch.

        Args:
            rows: Dataset rows processed in the current tick.
        """
        for row in rows:
            self._latest_rows[row.intersection_id] = row

    def predict(
        self,
        intersection_id: str,
        horizon: str,
    ) -> PredictionResult:
        """Generate a prediction for one intersection and horizon.

        Args:
            intersection_id: Target intersection identifier.
            horizon: Prediction horizon.

        Returns:
            Structured prediction result.
        """
        if horizon not in HORIZONS:
            raise ValueError(f"Unsupported horizon: {horizon}")

        live_state = state_store.get_state(intersection_id)
        if live_state is None:
            raise KeyError(f"Intersection {intersection_id} not found")

        dataset_row = self._latest_rows.get(intersection_id)
        if models_loaded() and not ml_fallback_active():
            return self._predict_with_lstm(
                intersection_id,
                horizon,
                live_state,
                dataset_row,
            )

        return self._predict_with_fallback(
            intersection_id,
            horizon,
            live_state,
            dataset_row,
        )

    def refresh_all_predictions(self) -> None:
        """Refresh AI prediction fields for all registered intersections."""
        for intersection_id in state_store.get_intersection_ids():
            predictions: dict[str, float | None] = {}
            for horizon in HORIZONS:
                result = self.predict(intersection_id, horizon)
                predictions[horizon] = float(result.predicted_vehicle_count)

            state_store.update_state(
                intersection_id,
                {"ai_predictions": predictions},
            )

    def _predict_with_lstm(
        self,
        intersection_id: str,
        horizon: str,
        live_state: LiveIntersectionState,
        dataset_row: DatasetRow | None,
    ) -> PredictionResult:
        """Run the LSTM on the real feature window ending at the replayed minute.

        Falls back to the labelled heuristic when the window is not available
        (unknown minute, not enough history); never pads or repeats rows.
        """
        if dataset_row is None:
            return self._predict_with_fallback(intersection_id, horizon, live_state, dataset_row)
        scalers = get_scalers()
        seq_len = seq_len_for(registry.get_config(), horizon)
        payload = feature_store.get_input(
            intersection_id, dataset_row.timestamp, seq_len, scalers["feat"],
        )
        if payload is None or payload.window is None:
            return self._predict_with_fallback(intersection_id, horizon, live_state, dataset_row)

        target_scaler = self._target_scaler_for_horizon(scalers["target"], horizon)
        model = get_model(horizon)
        raw_prediction = np.asarray(model(payload.window, training=False))
        inverse = target_scaler.inverse_transform(raw_prediction.reshape(-1, 1))
        return self._result(
            intersection_id, horizon, live_state,
            value=float(inverse.ravel()[0]), source="lstm", payload=payload,
        )

    def _predict_with_fallback(
        self,
        intersection_id: str,
        horizon: str,
        live_state: LiveIntersectionState,
        dataset_row: DatasetRow | None,
    ) -> PredictionResult:
        """Heuristic forecast: mean volume of the last 15 replayed minutes.

        This is the `moving_average_15` baseline of the D2 evaluation, labelled
        `heuristic`. It never reads the dataset's future target columns.
        """
        payload = None
        if dataset_row is not None:
            payload = feature_store.get_input(intersection_id, dataset_row.timestamp, 1, None)
        if payload is not None:
            value = payload.moving_average_15
        else:
            value = float(live_state["vehicle_count"]) * 60.0
        return self._result(
            intersection_id, horizon, live_state,
            value=value, source="heuristic", payload=payload,
        )

    def _result(
        self,
        intersection_id: str,
        horizon: str,
        live_state: LiveIntersectionState,
        *,
        value: float,
        source: Literal["lstm", "heuristic"],
        payload: ForecastInput | None,
    ) -> PredictionResult:
        issue = payload.issue_time if payload is not None else None
        target = issue + pd.Timedelta(minutes=HORIZON_MINUTES[horizon]) if issue is not None else None
        return PredictionResult(
            intersection_id=intersection_id,
            horizon=horizon,
            predicted_vehicle_count=int(max(0, round(value))),
            predicted_congestion_level=self._congestion_level(live_state),
            confidence_score=None,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            unit="kend/jam",
            current_volume=None if payload is None else round(payload.current_volume, 1),
            issue_time_wib=None if issue is None else issue.strftime("%Y-%m-%d %H:%M"),
            target_time_wib=None if target is None else target.strftime("%Y-%m-%d %H:%M"),
            expected_mae=self._expected_errors.get(horizon) if source == "lstm" else None,
            replay_split=None if payload is None else payload.split,
        )

    def _congestion_level(
        self,
        live_state: LiveIntersectionState,
    ) -> CongestionLevel:
        """Map occupancy to a congestion label.

        Args:
            live_state: Current live intersection state.

        Returns:
            Congestion level label.
        """
        occupancy = float(live_state["occupancy_rate"])
        if occupancy >= 0.9:
            return "Critical"
        if occupancy >= 0.75:
            return "High"
        if occupancy >= 0.55:
            return "Medium"
        return "Low"

    def _target_scaler_for_horizon(
        self,
        target_scalers: object,
        horizon: str,
    ) -> object:
        """Return the target scaler matching a prediction horizon.

        Args:
            target_scalers: Loaded target scaler artifact.
            horizon: Prediction horizon.

        Returns:
            Scaler object with ``inverse_transform``.

        Raises:
            KeyError: If a scaler dictionary does not contain the horizon.
        """
        if isinstance(target_scalers, dict):
            scaler = target_scalers.get(horizon)
            if scaler is None:
                raise KeyError(f"Target scaler for horizon {horizon} not found")
            return scaler
        return target_scalers


prediction_service = PredictionService()
