"""Section-level segment analytics routes for the v4 dataset.

Contract: `docs/SCHEMA-v4.md` §3.3.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from core.schemas import SegmentsResponse, SegmentsSummaryResponse
from sim.analytics_loader import analytics_loader

router = APIRouter(prefix="/segments", tags=["Segments"])

TipeFilter = Literal["perempatan", "pertigaan"]
SectionTypeFilter = Literal["approach", "corridor"]


@router.get(
    "",
    response_model=SegmentsResponse,
    summary="List Segments",
    description="Section rows of one replay tick with vehicle composition.",
)
async def list_segments(
    tick: int | None = Query(default=None, ge=0, description="Replay tick (default: last played)"),
    tipe: TipeFilter | None = Query(default=None, description="Filter by intersection type"),
    section_type: SectionTypeFilter | None = Query(default=None, description="Filter by section type"),
) -> SegmentsResponse:
    """Return per-section metrics for a tick."""
    resolved = analytics_loader.resolve_tick(tick)
    items = analytics_loader.segment_items(resolved, tipe=tipe, section_type=section_type)
    return SegmentsResponse(
        tick=resolved,
        count=len(items),
        total_capacity_vehicles=sum(int(item["kapasitas_kendaraan"]) for item in items),
        items=items,
    )


@router.get(
    "/summary",
    response_model=SegmentsSummaryResponse,
    summary="Segments Summary",
    description="Network-level segment aggregates, per intersection and corridor.",
)
async def segments_summary(
    tick: int | None = Query(default=None, ge=0, description="Replay tick (default: last played)"),
) -> SegmentsSummaryResponse:
    """Return network-level segment aggregates for a tick."""
    resolved = analytics_loader.resolve_tick(tick)
    return SegmentsSummaryResponse(**analytics_loader.segments_summary(resolved))
