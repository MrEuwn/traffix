"""Which forecaster is actually serving, and is it the one that was evaluated?

The API reports one unambiguous mode:
- `lstm`               Keras models loaded; predictions come from real replay windows.
- `heuristic_fallback` models missing or failed to load; predictions are the
                       labelled 15-minute moving average (the D2 baseline).
- `disabled`           ML loading switched off by configuration.
`matches_evaluation` compares the sha256 of the loaded model files with the
files the D2 evaluation scored, so a judge can see the served model is the
evaluated one.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from core.config import settings
from core.paths import resolve_asset_path
from ml.forecast.runtime import EVALUATION_PATH, feature_store
from ml.model_loader import ml_fallback_active, models_loaded


@lru_cache(maxsize=16)
def _sha256(path: str, mtime: float) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_sha256(path: Path) -> str | None:
    return _sha256(str(path), path.stat().st_mtime) if path.exists() else None


def forecaster_status() -> dict[str, object]:
    lstm_paths = {h: resolve_asset_path(p) for h, p in settings.get_lstm_paths().items()}
    loaded = {h: file_sha256(p) for h, p in lstm_paths.items()}
    evaluated: dict[str, str] = {}
    generated_at = None
    if EVALUATION_PATH.exists():
        payload = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
        evaluated = {h: v["sha256"] for h, v in payload.get("model", {}).get("artifacts", {}).items()}
        generated_at = payload.get("generated_at")

    if not settings.ml_auto_load and not models_loaded():
        mode = "disabled"
    elif models_loaded() and not ml_fallback_active():
        mode = "lstm"
    else:
        mode = "heuristic_fallback"

    return {
        "mode": mode,
        "label": {
            "lstm": "LSTM dimuat — inferensi nyata pada jendela replay",
            "heuristic_fallback": "Fallback heuristik — rata-rata 15 menit terakhir, bukan model",
            "disabled": "ML dimatikan oleh konfigurasi",
        }[mode],
        "model_files": {h: str(p.name) for h, p in lstm_paths.items()},
        "loaded_sha256": loaded,
        "evaluated_sha256": evaluated,
        "matches_evaluation": bool(evaluated) and mode == "lstm"
        and all(loaded.get(h) == evaluated.get(h) for h in evaluated),
        "evaluation_generated_at": generated_at,
        "input_data": {
            "kind": "replay_sintetis",
            "path": settings.hybrid_traffic_dataset_path,
            "features_ready": feature_store.ready,
            "features_error": feature_store.error,
        },
    }
