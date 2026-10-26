"""Signal-timing analytics routes for the v4 dataset.

Contract: `docs/SCHEMA-v4.md` §3.3. Corridor sections have no signal
(`cycle_length_s`/`green_seconds`/`red_seconds` are 0) and are excluded.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from core.schemas import SignalsSummaryResponse
from sim.analytics_loader import analytics_loader

router = APIRouter(prefix="/signals", tags=["Signals"])

ScopeFilter = Literal["all", "perempatan", "pertigaan"]


@router.get(
    "/summary",
    response_model=SignalsSummaryResponse,
    summary="Signals Summary",
    description="Signal timing aggregates per intersection type and overall.",
)
async def signals_summary(
    scope: ScopeFilter = Query(default="all", description="Aggregation scope"),
    tick: int | None = Query(default=None, ge=0, description="Replay tick (default: last played)"),
) -> SignalsSummaryResponse:
    """Return signal timing aggregates for a tick."""
    resolved = analytics_loader.resolve_tick(tick)
    return SignalsSummaryResponse(**analytics_loader.signals_summary(resolved, scope))
