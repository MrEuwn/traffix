"""Model evaluation routes.

- `/model/evaluation`            bottleneck classifier report (SCHEMA-v4 §3.3), pass-through
                                 of metrics.json plus its reproduction check.
- `/model/evaluation/forecast`   D2 primary task: LSTM vs baselines (forecast_evaluation.json).
- `/model/evaluation/forecast/{horizon}/series`  saved per-sample test predictions for charts.
- `/model/evaluation/detection`  YOLOv8 recorded validation metrics + frame inference summary.
- `/model/status`                which forecaster is serving and whether it is the evaluated one.

Every number comes from an artefact written by `backend/scripts/run_d2_evaluation.py`;
a missing artefact answers `available: false` with the command to produce it.
"""

from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from app.services.frame_service import frame_service
from core.responses import success_response
from core.schemas import ModelEvaluationResponse, StandardSuccessResponse
from ml.bottleneck.classifier import ARTIFACT_PATH, METRICS_PATH, load_metrics
from ml.forecast.features import HORIZON_MINUTES
from ml.forecast.runtime import EVALUATION_PATH
from ml.forecast.status import forecaster_status

router = APIRouter(prefix="/model", tags=["Model"])

REPRODUCE = "python backend/scripts/run_d2_evaluation.py"
REPRODUCTION_PATH = METRICS_PATH.parent / "reproduction.json"


def _read_json(path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@router.get(
    "/evaluation",
    response_model=ModelEvaluationResponse,
    summary="Model Evaluation",
    description="Bottleneck classifier metrics, baselines, and limitations.",
)
async def model_evaluation() -> ModelEvaluationResponse:
    """Return the persisted classifier evaluation report."""
    payload = load_metrics()
    if not payload.get("available"):
        return ModelEvaluationResponse(
            available=False,
            reason=(
                f"artefak model belum tersedia: {ARTIFACT_PATH} "
                f"(metrics: {METRICS_PATH})"
            ),
        )
    # Split protocol and artifact paths come from the frozen schema (§4), the rest
    # is a pass-through of the artifact agent's metrics.json.
    payload.setdefault(
        "split",
        {
            "train": "hari 1-5",
            "validation": "hari 6",
            "test": "hari 7",
            "protocol": "temporal, tanpa pengacakan",
        },
    )
    payload.setdefault(
        "artifacts",
        {"model": str(ARTIFACT_PATH), "metrics": str(METRICS_PATH)},
    )
    reproduction = _read_json(REPRODUCTION_PATH)
    if reproduction:
        payload["reproduction"] = {
            "matches_stored_metrics": reproduction["matches_stored_metrics"],
            "generated_at": reproduction.get("generated_at"),
            "validation": {k: reproduction["splits"]["validation"][k]
                           for k in ("macro_f1", "balanced_accuracy", "accuracy", "n")},
            "command": REPRODUCE,
        }
    payload["label_provenance"] = "sintetis — label dari aturan simulator v4 (seed 42), bukan kejadian lapangan"
    return ModelEvaluationResponse(**payload)


@router.get(
    "/evaluation/forecast",
    response_model=StandardSuccessResponse,
    summary="Forecast Evaluation (D2 primary task)",
    description="LSTM vs baselines per horizon on the held-out test day, with provenance and runtime status.",
)
async def forecast_evaluation(request: Request) -> StandardSuccessResponse:
    payload = _read_json(EVALUATION_PATH)
    if payload is None:
        data = {"available": False,
                "reason": f"artefak evaluasi belum ada: {EVALUATION_PATH.name}",
                "command": REPRODUCE}
    else:
        # Per-sample series and training history are served separately / trimmed.
        for horizon in payload.get("horizons", {}).values():
            horizon.pop("lstm_training_history", None)
        payload.pop("preflight", None)
        data = payload
    data["runtime"] = forecaster_status()
    return success_response(
        message="Forecast evaluation retrieved",
        data=data,
        request_id=request.state.request_id,
    )


@router.get(
    "/evaluation/forecast/{horizon}/series",
    response_model=StandardSuccessResponse,
    summary="Forecast test-day predictions",
    description="Saved per-sample actual vs predicted values (LSTM and one baseline) for one horizon.",
)
async def forecast_series(
    request: Request,
    horizon: str,
    baseline: str | None = Query(default=None, description="baseline column; default = strongest baseline"),
    intersection: str | None = Query(default=None, description="intersection id; default = first in the file"),
    step: int = Query(default=5, ge=1, le=60, description="keep every n-th minute"),
) -> StandardSuccessResponse:
    if horizon not in HORIZON_MINUTES:
        raise HTTPException(status_code=404, detail=f"horizon tidak dikenal: {horizon}")
    payload = _read_json(EVALUATION_PATH)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"artefak evaluasi belum ada — jalankan {REPRODUCE}")
    meta = payload["horizons"][horizon]
    chosen = baseline or meta["strongest_baseline"]["model"]
    path = EVALUATION_PATH.parent / f"predictions_test_{horizon}.csv"
    frame = pd.read_csv(path)
    if chosen not in frame.columns or chosen in {"actual", "issue_time_wib", "target_time_wib", "intersection_id"}:
        raise HTTPException(status_code=400, detail=f"kolom baseline tidak dikenal: {chosen}")
    intersections = list(dict.fromkeys(frame["intersection_id"])) if "intersection_id" in frame else []
    shown = intersection or (intersections[0] if intersections else None)
    if shown is not None:
        if shown not in intersections:
            raise HTTPException(status_code=404, detail=f"simpang tidak ada di set uji: {shown}")
        frame = frame[frame["intersection_id"] == shown]
    frame = frame.iloc[::step]
    return success_response(
        message="Forecast series retrieved",
        data={
            "horizon": horizon,
            "baseline": chosen,
            "unit": "kend/jam",
            "step_minutes": step,
            "intersection": shown,
            "intersections": intersections,
            "n_total": int(meta["n"]["test"]),
            "source_csv": meta["predictions_csv"],
            "points": [
                {"t": r.target_time_wib, "actual": r.actual, "lstm": r.lstm, "baseline": getattr(r, chosen)}
                for r in frame.itertuples(index=False)
            ],
        },
        request_id=request.state.request_id,
    )


@router.get(
    "/evaluation/detection",
    response_model=StandardSuccessResponse,
    summary="YOLO detection evidence",
    description="Notebook-recorded validation metrics and the frame-inference summary.",
)
async def detection_evaluation(request: Request) -> StandardSuccessResponse:
    evidence = frame_service.evidence()
    live_ok, live_reason = frame_service.live_available()
    data = evidence or {"available": False, "command": REPRODUCE}
    data["live_inference_available"] = live_ok
    data["live_inference_reason"] = live_reason
    return success_response(
        message="Detection evidence retrieved",
        data=data,
        request_id=request.state.request_id,
    )


@router.get(
    "/status",
    response_model=StandardSuccessResponse,
    summary="Forecaster runtime status",
    description="Serving mode (lstm / heuristic_fallback / disabled) and model-file hashes vs the evaluated ones.",
)
async def model_status(request: Request) -> StandardSuccessResponse:
    return success_response(
        message="Model status retrieved",
        data=forecaster_status(),
        request_id=request.state.request_id,
    )
