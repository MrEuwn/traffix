"""Bottleneck-cause analytics routes for the v4 dataset.

Contract: `docs/SCHEMA-v4.md` §3.3. Confidence comes from
`ml.bottleneck.classifier.bottleneck_classifier`; when the trained artifact is
absent the rule-based fallback is used, `model_available` is false and confidence
is reported as 0 per the schema.
"""

from __future__ import annotations

import re
from typing import Final

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from core.schemas import (
    BottleneckCauseItem,
    BottleneckDetailResponse,
    BottleneckHistoryPoint,
    BottleneckPerIntersection,
    BottleneckSectionRow,
    BottlenecksResponse,
    BottleneckTopCause,
)
from ml.bottleneck.classifier import bottleneck_classifier, load_metrics
from ml.bottleneck.features import CLASSES
from sim.analytics_loader import MODEL_LAG_WARMUP_TICKS, analytics_loader

router = APIRouter(prefix="/bottlenecks", tags=["Bottlenecks"])

DISCLOSURE: Final[str] = "data sintetis · seed 42"
TOP_CAUSES: Final[int] = 3
HISTORY_TICKS: Final[int] = 60
DEFAULT_DRIVERS: Final[tuple[str, ...]] = (
    "volume_veh_per_hour",
    "queue_length_veh",
    "avg_speed_kmh",
)

# Indonesian labels for the allowed features shown as drivers: (label, unit, decimals).
_DRIVER_SPEC: Final[dict[str, tuple[str, str, int]]] = {
    "vehicle_count_1min": ("arus kendaraan", "kendaraan/menit", 0),
    "volume_veh_per_hour": ("volume", "kendaraan/jam", 0),
    "avg_speed_kmh": ("kecepatan rata-rata", "km/jam", 1),
    "queue_length_veh": ("antrean", "kendaraan", 0),
    "wait_time_min": ("waktu tunggu", "menit", 1),
    "density_percent": ("kepadatan", "%", 1),
    "jumlah_lajur": ("jumlah lajur", "lajur", 0),
    "panjang_m": ("panjang ruas", "m", 0),
    "kapasitas_smp_per_jam": ("kapasitas", "smp/jam", 0),
    "proporsi_roda_6plus": ("pangsa kendaraan berat", "%", 1),
    "weather_temp_c": ("suhu udara", "°C", 1),
}
_LAG_PREFIX: Final[re.Pattern[str]] = re.compile(r"^(?:lag\d+|roll\d+_(?:mean|std))_")


def _num(value: object, digits: int = 4) -> float | None:
    """Round a possibly-null numeric value for JSON output."""
    if value is None or value != value:  # NaN check without pandas
        return None
    return round(float(value), digits)  # type: ignore[arg-type]


def _fmt(value: float, digits: int) -> str:
    """Format a number with Indonesian decimal comma and thousands space."""
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def _driver_features() -> list[str]:
    """Return the top contributing allowed features (model importance first)."""
    payload = load_metrics()
    ordered: list[str] = []
    for item in payload.get("feature_importance") or []:
        base = _LAG_PREFIX.sub("", str(item.get("feature", "")))
        if (base in _DRIVER_SPEC or base in {"green_seconds", "cycle_length_s"}) and base not in ordered:
            ordered.append(base)
    return (ordered or list(DEFAULT_DRIVERS))[:TOP_CAUSES]


def _driver_text(feature: str, value: float, cycle_length_s: float) -> str:
    """Render one driver as a human-readable Indonesian reason."""
    if feature == "green_seconds":
        return f"green {_fmt(value, 0)} s dari siklus {_fmt(cycle_length_s, 0)} s"
    if feature == "cycle_length_s":
        return f"siklus {_fmt(value, 0)} s"
    label, unit, digits = _DRIVER_SPEC[feature]
    if feature == "proporsi_roda_6plus":
        value *= 100.0
    return f"{label} {_fmt(value, digits)} {unit}"


def _drivers(intersection_id: str, tick: int) -> list[str]:
    """Build Indonesian driver reasons for one intersection and tick."""
    metrics = analytics_loader.intersection_metrics(tick)
    if intersection_id not in metrics.index:
        return []
    row = metrics.loc[intersection_id]
    cycle = float(row.get("cycle_length_s") or 0.0)
    drivers: list[str] = []
    for feature in _driver_features():
        value = row.get(feature)
        if value is None or value != value:
            continue
        drivers.append(_driver_text(feature, float(value), cycle))
    return drivers


def _class_probabilities(frame, tick: int) -> np.ndarray:
    """Mean class probabilities over the rows of one tick, in `CLASSES` order."""
    window = frame.sort_values(["section_id", "tick"]).reset_index(drop=True)
    proba = np.asarray(bottleneck_classifier.predict_proba(window), dtype=float)
    mean = proba[(window["tick"] == tick).to_numpy()]
    out = np.zeros(len(CLASSES))
    if len(mean):
        averaged = mean.mean(axis=0)
        for position, label in enumerate(bottleneck_classifier.classes):
            if label in CLASSES and position < len(averaged):
                out[CLASSES.index(label)] = float(averaged[position])
    total = out.sum()
    return out / total if total > 0 else out


def _per_intersection(tick: int) -> list[BottleneckPerIntersection]:
    """Diagnose every intersection of one tick."""
    metrics = analytics_loader.intersection_metrics(tick)
    master = analytics_loader.load_intersections()
    available = bottleneck_classifier.available
    result: list[BottleneckPerIntersection] = []

    for intersection_id in sorted(metrics.index):
        probabilities = _class_probabilities(
            analytics_loader.model_input_frame(tick, intersection_id=str(intersection_id)),
            tick,
        )
        ranked = sorted(
            zip(CLASSES, probabilities),
            key=lambda item: item[1],
            reverse=True,
        )[:TOP_CAUSES]
        result.append(
            BottleneckPerIntersection(
                intersection_id=str(intersection_id),
                intersection_name=(
                    str(master.loc[intersection_id, "intersection_name"])
                    if intersection_id in master.index
                    else ""
                ),
                tipe_persimpangan=(
                    str(master.loc[intersection_id, "tipe_persimpangan"])
                    if intersection_id in master.index
                    else ""
                ),
                dominant_cause=str(ranked[0][0]),
                confidence=round(float(ranked[0][1]), 4) if available else 0.0,
                probabilities={
                    label: round(float(value), 4) for label, value in zip(CLASSES, probabilities)
                },
                top3=[
                    BottleneckTopCause(cause=str(label), probability=round(float(value), 4))
                    for label, value in ranked
                ],
                drivers=_drivers(str(intersection_id), tick),
            ),
        )
    return result


def _history(intersection_id: str, tick: int, count: int = HISTORY_TICKS) -> list[BottleneckHistoryPoint]:
    """Return the last `count` replayed ticks for one intersection."""
    first = max(0, tick - count + 1)
    frame = analytics_loader.model_input_frame(
        tick,
        intersection_id=intersection_id,
        warmup=count + MODEL_LAG_WARMUP_TICKS,
    ).sort_values(["section_id", "tick"]).reset_index(drop=True)
    proba = np.asarray(bottleneck_classifier.predict_proba(frame), dtype=float)

    labels = np.zeros((len(frame), len(CLASSES)))
    for position, label in enumerate(bottleneck_classifier.classes):
        if label in CLASSES and position < proba.shape[1]:
            labels[:, CLASSES.index(label)] = proba[:, position]
    ticks = frame["tick"].to_numpy()

    raw = analytics_loader.tick_window(first, tick)
    raw = raw[raw["intersection_id"] == intersection_id]
    means = raw.groupby("tick")[["vc_ratio", "queue_length_veh", "avg_speed_kmh"]].mean()
    available = bottleneck_classifier.available

    history: list[BottleneckHistoryPoint] = []
    for value in sorted({int(item) for item in ticks.tolist()}):
        if value < first:
            continue
        rows = labels[ticks == value]
        if not len(rows):
            continue
        mean = rows.mean(axis=0)
        hottest = int(np.argmax(mean))
        point = means.loc[value] if value in means.index else None
        history.append(
            BottleneckHistoryPoint(
                tick=value,
                timestamp_wib=analytics_loader.timestamp_for_tick(value),
                dominant_cause=CLASSES[hottest],
                confidence=round(float(mean[hottest]), 4) if available else 0.0,
                vc_ratio=None if point is None else _num(point["vc_ratio"], 3),
                queue_length_veh=None if point is None else _num(point["queue_length_veh"], 1),
                avg_speed_kmh=None if point is None else _num(point["avg_speed_kmh"], 2),
            ),
        )
    return history


@router.get(
    "",
    response_model=BottlenecksResponse,
    summary="Bottleneck Causes",
    description="Bottleneck causes per section and per intersection for one replay tick.",
)
async def list_bottlenecks(
    tick: int | None = Query(default=None, ge=0, description="Replay tick (default: last played)"),
) -> BottlenecksResponse:
    """Return network and per-intersection bottleneck causes for a tick."""
    resolved = analytics_loader.resolve_tick(tick)
    rows = analytics_loader.section_rows(resolved)
    causes = analytics_loader.cause_table(resolved)
    return BottlenecksResponse(
        tick=resolved,
        timestamp_wib=analytics_loader.timestamp_for_tick(resolved),
        section_count=int(len(rows)),
        affected_section_count=int((rows["bottleneck_cause"] != "normal").sum()),
        dominant_cause=str(causes[0]["cause"]) if causes else "normal",
        causes=[BottleneckCauseItem(**item) for item in causes],
        per_intersection=_per_intersection(resolved),
        model_available=bottleneck_classifier.available,
        synthetic_data=True,
        disclosure=DISCLOSURE,
    )


@router.get(
    "/{intersection_id}",
    response_model=BottleneckDetailResponse,
    summary="Get Intersection Bottleneck",
    description="Bottleneck diagnosis of one intersection with history and sections.",
)
async def get_bottleneck(
    intersection_id: str,
    tick: int | None = Query(default=None, ge=0, description="Replay tick (default: last played)"),
) -> BottleneckDetailResponse:
    """Return one intersection diagnosis, its 60-tick history, and sections.

    Raises:
        HTTPException: 404 when the intersection is not in the v4 master table.
    """
    normalized = intersection_id.upper()
    master = analytics_loader.load_intersections()
    if normalized not in master.index:
        raise HTTPException(status_code=404, detail=f"Intersection {intersection_id} not found")

    tick = analytics_loader.resolve_tick(tick)
    detail = next(
        item for item in _per_intersection(tick) if item.intersection_id == normalized
    )
    section_keys = (
        "section_id",
        "nama_ruas",
        "section_type",
        "approach",
        "vc_ratio",
        "los",
        "avg_speed_kmh",
        "queue_length_veh",
        "wait_time_min",
        "bottleneck_cause",
    )
    return BottleneckDetailResponse(
        **detail.model_dump(),
        history=_history(normalized, tick),
        sections=[
            BottleneckSectionRow(**{key: item[key] for key in section_keys})
            for item in analytics_loader.segment_items(tick)
            if item["intersection_id"] == normalized
        ],
    )
