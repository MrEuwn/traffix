"""Runtime bottleneck-cause classifier (artifact loader + rule fallback).

Frozen interface — see `docs/SCHEMA-v4.md` §4.1. Training lives in
`train_bottleneck.py` (owned by the model task); this module only loads the
resulting artifact and serves probabilities.

Artifact layout (`artifacts/bottleneck_classifier.joblib`)::

    {"model": <fitted estimator with predict_proba>, "classes": [...],
     "feature_columns": [...], "model_name": str, "trained_at": str,
     "with_lags": bool}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.bottleneck.features import (
    CLASSES,
    FEATURE_COLUMNS,
    assert_no_leakage,
    build_feature_frame,
    rule_based_cause,
)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "bottleneck_classifier.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"


class BottleneckClassifier:
    """Loads the trained cause classifier once and serves class probabilities."""

    def __init__(self, artifact_path: Path | None = None) -> None:
        self._artifact_path = artifact_path or ARTIFACT_PATH
        self._model: Any | None = None
        self._classes: list[str] = list(CLASSES)
        self._feature_columns: list[str] = list(FEATURE_COLUMNS)
        self._model_name = "rule_based_fallback"
        self._trained_at: str | None = None
        self._load()

    def _load(self) -> None:
        """Load the joblib artifact when present; otherwise stay on fallback."""
        if not self._artifact_path.exists():
            return
        try:
            import joblib

            payload = joblib.load(self._artifact_path)
            model = payload["model"] if isinstance(payload, dict) else payload
            features = list(
                (payload.get("feature_columns") if isinstance(payload, dict) else None)
                or FEATURE_COLUMNS
            )
            assert_no_leakage(features)
            self._model = model
            self._feature_columns = features
            self._classes = list(
                (payload.get("classes") if isinstance(payload, dict) else None)
                or getattr(model, "classes_", CLASSES)
            )
            self._model_name = str(
                (payload.get("model_name") if isinstance(payload, dict) else None)
                or type(model).__name__
            )
            self._trained_at = (
                payload.get("trained_at") if isinstance(payload, dict) else None
            )
        except Exception:  # pragma: no cover - defensive: never break the API
            self._model = None

    @property
    def available(self) -> bool:
        """True when a trained artifact is loaded."""
        return self._model is not None

    @property
    def model_name(self) -> str:
        """Name of the loaded model (or the fallback name)."""
        return self._model_name

    @property
    def trained_at(self) -> str | None:
        """ISO timestamp of training when known."""
        return self._trained_at

    @property
    def classes(self) -> list[str]:
        """Class labels in model column order."""
        return list(self._classes)

    @property
    def feature_columns(self) -> list[str]:
        """Feature columns expected by the loaded model."""
        return list(self._feature_columns)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        """Return class probabilities for the given raw tick rows.

        Args:
            frame: Section-level tick rows containing the raw feature inputs.

        Returns:
            Array of shape (n_rows, n_classes) aligned with `self.classes`.
        """
        features = build_feature_frame(frame)
        if self._model is None:
            labels = rule_based_cause(pd.concat([frame.reset_index(drop=True), features], axis=1))
            proba = np.zeros((len(frame), len(self._classes)))
            for i, label in enumerate(labels):
                idx = self._classes.index(label) if label in self._classes else 0
                proba[i, idx] = 1.0
            return proba
        columns = [c for c in self._feature_columns if c in features.columns]
        proba = np.asarray(self._model.predict_proba(features[columns]), dtype=float)
        return proba

    def predict(self, frame: pd.DataFrame) -> list[str]:
        """Return the most likely cause label per row."""
        proba = self.predict_proba(frame)
        return [self._classes[int(np.argmax(row))] for row in proba]


def load_metrics() -> dict:
    """Return the persisted training metrics, or an unavailable marker."""
    if not METRICS_PATH.exists():
        return {"available": False}
    try:
        payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"available": False}
    payload.setdefault("available", True)
    return payload


bottleneck_classifier = BottleneckClassifier()
