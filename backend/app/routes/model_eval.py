"""Model evaluation route: serves the bottleneck classifier report.

Contract: `docs/SCHEMA-v4.md` §3.3. The report is a pass-through of the artifact
agent's `metrics.json`; when it is absent the route answers 200 with
`available: false` and the reason instead of failing.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.schemas import ModelEvaluationResponse
from ml.bottleneck.classifier import ARTIFACT_PATH, METRICS_PATH, load_metrics

router = APIRouter(prefix="/model", tags=["Model"])


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
    return ModelEvaluationResponse(**payload)
