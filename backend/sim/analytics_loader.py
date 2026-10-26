"""Tick-aware analytics loader for the v4 synthetic traffic dataset.

Single cached pandas entry point for `data/data_synthetic/v4`: the section-level
tick series plus the two master CSVs (intersections, sections).

Paths are resolved like `core/paths.resolve_asset_path` and can be overridden with
`TRAFFIX_V4_TICKS_PATH`, `TRAFFIX_V4_SECTIONS_PATH`, `TRAFFIX_V4_INTERSECTIONS_PATH`
(or explicit constructor arguments, used by tests).

All accessors return cached frames or derived copies: treat the result as read-only.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Final

import numpy as np
import pandas as pd

from core.paths import resolve_asset_path
from ml.bottleneck.features import assert_no_leakage

DEFAULT_TICKS_PATH: Final[str] = "../data/data_synthetic/v4/ticks_v4.csv.gz"
DEFAULT_SECTIONS_PATH: Final[str] = "../data/data_synthetic/v4/sections.csv"
DEFAULT_INTERSECTIONS_PATH: Final[str] = "../data/data_synthetic/v4/intersections.csv"

TICKS_PATH_ENV: Final[str] = "TRAFFIX_V4_TICKS_PATH"
SECTIONS_PATH_ENV: Final[str] = "TRAFFIX_V4_SECTIONS_PATH"
INTERSECTIONS_PATH_ENV: Final[str] = "TRAFFIX_V4_INTERSECTIONS_PATH"

# Exactly the raw inputs the bottleneck classifier is allowed to see. Every
# label-defining column (`bottleneck_cause`, `vc_ratio`, `curah_hujan_mm_jam`, ...)
# is physically absent here, so it can never reach `predict_proba`.
MODEL_INPUT_COLUMNS: Final[tuple[str, ...]] = (
    "section_id",
    "tick",
    "timestamp_wib",
    "section_type",
    "tipe_persimpangan",
    "vehicle_count_1min",
    "volume_veh_per_hour",
    "avg_speed_kmh",
    "queue_length_veh",
    "wait_time_min",
    "green_seconds",
    "cycle_length_s",
    "density_percent",
    "jumlah_lajur",
    "panjang_m",
    "kapasitas_smp_per_jam",
    "proporsi_roda_6plus",
    "weather_temp_c",
)

# 60-minute warm-up so lag/rolling features of the requested tick are real values.
MODEL_LAG_WARMUP_TICKS: Final[int] = 61

# Per-intersection means exposed to the bottleneck endpoints.
INTERSECTION_METRICS: Final[tuple[str, ...]] = (
    "vehicle_count_1min",
    "volume_veh_per_hour",
    "avg_speed_kmh",
    "queue_length_veh",
    "wait_time_min",
    "green_seconds",
    "red_seconds",
    "cycle_length_s",
    "density_percent",
    "vc_ratio",
    "proporsi_roda_6plus",
)

LOS_GRADES: Final[tuple[str, ...]] = ("A", "B", "C", "D", "E", "F")
VEHICLE_CLASSES: Final[tuple[str, ...]] = ("roda_2", "roda_3", "roda_4", "roda_6plus")

assert_no_leakage(list(MODEL_INPUT_COLUMNS))


def _num(value: object, digits: int = 3) -> float | None:
    """Round a possibly-null numeric value for JSON output."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


class AnalyticsLoader:
    """Cached, vectorized reader for the v4 tick series and master tables."""

    def __init__(
        self,
        ticks_path: str | Path | None = None,
        sections_path: str | Path | None = None,
        intersections_path: str | Path | None = None,
    ) -> None:
        """Initialize the loader (no I/O until first access).

        Args:
            ticks_path: Optional tick-series override.
            sections_path: Optional section-master override.
            intersections_path: Optional intersection-master override.
        """
        self._ticks_source = Path(
            ticks_path or os.environ.get(TICKS_PATH_ENV) or DEFAULT_TICKS_PATH
        )
        self._sections_source = Path(
            sections_path or os.environ.get(SECTIONS_PATH_ENV) or DEFAULT_SECTIONS_PATH
        )
        self._intersections_source = Path(
            intersections_path
            or os.environ.get(INTERSECTIONS_PATH_ENV)
            or DEFAULT_INTERSECTIONS_PATH
        )
        self._lock = Lock()
        self._ticks: pd.DataFrame | None = None
        self._sections: pd.DataFrame | None = None
        self._intersections: pd.DataFrame | None = None
        self._tick_values: np.ndarray | None = None
        self._tick_timestamps: pd.Series | None = None
        self._current_tick: int | None = None

    def _resolve(self, source: Path) -> Path:
        """Resolve a configured path against backend and repo roots."""
        return source if source.is_absolute() else resolve_asset_path(str(source))

    @property
    def ticks_path(self) -> Path:
        """Return the resolved tick-series path."""
        return self._resolve(self._ticks_source)

    @property
    def sections_path(self) -> Path:
        """Return the resolved section-master path."""
        return self._resolve(self._sections_source)

    @property
    def intersections_path(self) -> Path:
        """Return the resolved intersection-master path."""
        return self._resolve(self._intersections_source)

    @property
    def available(self) -> bool:
        """Return whether the tick series exists on disk."""
        return self.ticks_path.exists()

    def load_ticks(self) -> pd.DataFrame:
        """Load (once) and return the section-level tick series, sorted by tick."""
        with self._lock:
            if self._ticks is None:
                frame = pd.read_csv(self.ticks_path).sort_values(
                    ["tick", "section_id"],
                ).reset_index(drop=True)
                self._ticks = frame
                self._tick_values = frame["tick"].to_numpy()
                self._tick_timestamps = frame.drop_duplicates("tick").set_index(
                    "tick",
                )["timestamp_wib"]
            return self._ticks

    def load_sections(self) -> pd.DataFrame:
        """Load (once) and return the section master table."""
        with self._lock:
            if self._sections is None:
                self._sections = pd.read_csv(self.sections_path)
            return self._sections

    def load_intersections(self) -> pd.DataFrame:
        """Load (once) and return the intersection master table."""
        with self._lock:
            if self._intersections is None:
                self._intersections = pd.read_csv(self.intersections_path).set_index(
                    "intersection_id",
                )
            return self._intersections

    def intersection_master_row(self, intersection_id: str) -> dict[str, object] | None:
        """Return one intersection master row as a dict, or None when unknown."""
        master = self.load_intersections()
        if intersection_id not in master.index:
            return None
        return master.loc[intersection_id].to_dict()

    # --- tick tracking -------------------------------------------------------

    @property
    def current_tick(self) -> int | None:
        """Return the tick currently tracked by the replay cursor, if any."""
        return self._current_tick

    def latest_tick(self) -> int:
        """Return the last tick present in the dataset."""
        return int(self.load_ticks()["tick"].max())

    def set_current_tick(self, tick: int) -> int:
        """Track a tick (clamped to the dataset range) and return it."""
        clamped = max(0, min(int(tick), self.latest_tick()))
        self._current_tick = clamped
        return clamped

    def resolve_tick(self, tick: int | None = None) -> int:
        """Resolve an optional tick parameter to a concrete dataset tick.

        Explicit ticks update the tracked cursor; otherwise the tracked cursor,
        then the last dataset tick, is used.
        """
        if tick is None:
            return self._current_tick if self._current_tick is not None else self.latest_tick()
        return self.set_current_tick(tick)

    def timestamp_for_tick(self, tick: int) -> str | None:
        """Return the ISO-8601 WIB timestamp of a tick."""
        self.load_ticks()
        assert self._tick_timestamps is not None
        value = self._tick_timestamps.get(tick)
        return None if value is None or pd.isna(value) else str(value)

    def tick_for_elapsed_minutes(self, elapsed_minutes: int) -> int:
        """Map replay elapsed minutes to a dataset tick.

        The v4 dataset is a gap-free 1-minute series, so the replay cursor's
        elapsed minutes from the dataset start equal the tick index. Used by the
        tick engine to keep the analytics endpoints on the same instant as the
        live dashboard.

        Args:
            elapsed_minutes: Minutes elapsed since the first dataset timestamp.

        Returns:
            Dataset tick, clamped to the available range.
        """
        return self.set_current_tick(int(elapsed_minutes))

    # --- per-tick slices -----------------------------------------------------

    def tick_bounds(self, tick: int) -> tuple[int, int]:
        """Return the positional slice bounds of one tick in the loaded frame."""
        self.load_ticks()
        assert self._tick_values is not None
        left = int(np.searchsorted(self._tick_values, tick, side="left"))
        right = int(np.searchsorted(self._tick_values, tick, side="right"))
        return left, right

    def section_rows(self, tick: int) -> pd.DataFrame:
        """Return all section rows of one tick (30 rows)."""
        frame = self.load_ticks()
        left, right = self.tick_bounds(tick)
        return frame.iloc[left:right]

    def tick_window(self, tick_from: int, tick_to: int) -> pd.DataFrame:
        """Return every section row between two ticks inclusive."""
        frame = self.load_ticks()
        left, _ = self.tick_bounds(tick_from)
        _, right = self.tick_bounds(tick_to)
        return frame.iloc[left:right]

    def model_input_frame(
        self,
        tick: int,
        *,
        intersection_id: str | None = None,
        warmup: int = MODEL_LAG_WARMUP_TICKS,
    ) -> pd.DataFrame:
        """Return leakage-safe model inputs for a tick (plus lag warm-up).

        Args:
            tick: Target tick; its rows are the prediction target.
            intersection_id: Optional intersection filter.
            warmup: Ticks of history included so lag/rolling features are real.

        Returns:
            Frame with exactly `MODEL_INPUT_COLUMNS` columns.
        """
        window = self.tick_window(max(0, tick - warmup + 1), tick)
        if intersection_id is not None:
            window = window[window["intersection_id"] == intersection_id]
        frame = window.loc[:, list(MODEL_INPUT_COLUMNS)].copy()
        assert_no_leakage(list(frame.columns))
        return frame

    def intersection_metrics(self, tick: int) -> pd.DataFrame:
        """Return per-intersection means of signal/traffic metrics for a tick."""
        rows = self.section_rows(tick)
        approach = rows[rows["section_type"] == "approach"]
        columns = [c for c in INTERSECTION_METRICS if c in approach.columns]
        if approach.empty:
            return pd.DataFrame(columns=columns)
        return approach.groupby("intersection_id")[columns].mean()

    # --- aggregations --------------------------------------------------------

    def cause_table(self, tick: int) -> list[dict[str, object]]:
        """Return per-cause aggregates for a tick, most affected first.

        Only non-`normal` causes are listed, so `causes[0]` is the dominant
        disruption of the tick.
        """
        rows = self.section_rows(tick)
        total = len(rows)
        affected = rows[rows["bottleneck_cause"] != "normal"]
        if affected.empty:
            return []
        grouped = affected.groupby("bottleneck_cause").agg(
            sections=("section_id", "size"),
            avg_vc_ratio=("vc_ratio", "mean"),
            avg_queue_veh=("queue_length_veh", "mean"),
            avg_wait_time_min=("wait_time_min", "mean"),
        )
        grouped = grouped.sort_values(
            ["sections", "bottleneck_cause"],
            ascending=[False, True],
        )
        return [
            {
                "cause": str(cause),
                "sections": int(row["sections"]),
                "share": round(int(row["sections"]) / total, 3) if total else 0.0,
                "avg_vc_ratio": _num(row["avg_vc_ratio"]),
                "avg_queue_veh": _num(row["avg_queue_veh"], 1),
                "avg_wait_time_min": _num(row["avg_wait_time_min"], 2),
            }
            for cause, row in grouped.iterrows()
        ]

    def cause_by_intersection(self, tick: int) -> dict[str, str]:
        """Return the dominant data label per intersection for a tick."""
        rows = self.section_rows(tick)
        approach = rows[rows["section_type"] == "approach"]
        if approach.empty:
            return {}
        counts = approach.groupby(["intersection_id", "bottleneck_cause"]).size()
        result: dict[str, str] = {}
        for intersection_id, group in counts.groupby(level=0):
            ordered = group.droplevel(0).sort_values(ascending=False)
            result[str(intersection_id)] = str(ordered.index[0])
        return result

    def segment_items(
        self,
        tick: int,
        *,
        tipe: str | None = None,
        section_type: str | None = None,
    ) -> list[dict[str, object]]:
        """Return per-section rows for a tick with vehicle composition."""
        rows = self.section_rows(tick)
        if tipe is not None:
            rows = rows[rows["tipe_persimpangan"] == tipe]
        if section_type is not None:
            rows = rows[rows["section_type"] == section_type]
        dominant = self.cause_by_intersection(tick)

        counts = rows["vehicle_count_1min"].to_numpy(dtype=float)
        volume = rows["volume_veh_per_hour"].to_numpy(dtype=float)
        # Hourly scale factor keeps composition consistent with volume_veh_per_hour.
        scale = np.divide(volume, counts, out=np.full_like(volume, 60.0), where=counts > 0)
        mix = {name: rows[name].to_numpy(dtype=float) for name in VEHICLE_CLASSES}
        hourly = {name: np.round(values * scale) for name, values in mix.items()}
        totals = np.sum(list(hourly.values()), axis=0)
        smp = (
            0.25 * hourly["roda_2"]
            + 0.50 * hourly["roda_3"]
            + hourly["roda_4"]
            + 1.30 * hourly["roda_6plus"]
        )

        items: list[dict[str, object]] = []
        for position, (_, row) in enumerate(rows.iterrows()):
            total = float(totals[position])
            approach = row["approach"]
            items.append(
                {
                    "section_id": str(row["section_id"]),
                    "nama_ruas": str(row["nama_ruas"]),
                    "section_type": str(row["section_type"]),
                    "intersection_id": str(row["intersection_id"]),
                    "tipe_persimpangan": str(row["tipe_persimpangan"]),
                    "approach": "" if pd.isna(approach) else str(approach),
                    "panjang_m": int(row["panjang_m"]),
                    "jumlah_lajur": int(row["jumlah_lajur"]),
                    "kapasitas_smp_per_jam": int(row["kapasitas_smp_per_jam"]),
                    "kapasitas_kendaraan": int(row["kapasitas_kendaraan"]),
                    "volume_veh_per_hour": _num(row["volume_veh_per_hour"], 1),
                    "vc_ratio": _num(row["vc_ratio"]),
                    "los": str(row["los"]),
                    "avg_speed_kmh": _num(row["avg_speed_kmh"], 2),
                    "queue_length_veh": int(row["queue_length_veh"]),
                    "wait_time_min": _num(row["wait_time_min"], 2),
                    "kendaraan": {
                        **{name: int(hourly[name][position]) for name in VEHICLE_CLASSES},
                        "total": int(total),
                        "smp_ekivalen": round(float(smp[position]), 1),
                        "persen": {
                            name: (round(float(hourly[name][position]) / total, 3) if total else 0.0)
                            for name in VEHICLE_CLASSES
                        },
                    },
                    "bottleneck_cause": str(row["bottleneck_cause"]),
                    # Corridor rows have no intersection, so their own label is the
                    # dominant cause of that ruas.
                    "penyebab_dominan": dominant.get(
                        str(row["intersection_id"]),
                        str(row["bottleneck_cause"]),
                    ),
                },
            )
        return items

    @staticmethod
    def _vehicle_totals(rows: pd.DataFrame) -> dict[str, object]:
        """Aggregate vehicle composition over a set of section rows."""
        counts = rows["vehicle_count_1min"].to_numpy(dtype=float)
        volume = rows["volume_veh_per_hour"].to_numpy(dtype=float)
        scale = np.divide(volume, counts, out=np.full_like(volume, 60.0), where=counts > 0)
        hourly = {
            name: float(np.round(rows[name].to_numpy(dtype=float) * scale).sum())
            for name in VEHICLE_CLASSES
        }
        total = float(sum(hourly.values()))
        smp = (
            0.25 * hourly["roda_2"]
            + 0.50 * hourly["roda_3"]
            + hourly["roda_4"]
            + 1.30 * hourly["roda_6plus"]
        )
        return {
            **{name: int(value) for name, value in hourly.items()},
            "total": int(total),
            "persen": {
                name: (round(hourly[name] / total, 3) if total else 0.0) for name in VEHICLE_CLASSES
            },
            "smp_ekivalen": round(float(smp), 1),
        }

    def segments_summary(self, tick: int) -> dict[str, object]:
        """Return network-level segment aggregates for a tick."""
        rows = self.section_rows(tick)
        approach = rows[rows["section_type"] == "approach"]
        corridor = rows[rows["section_type"] == "corridor"]
        per_intersection = [
            {
                "intersection_id": str(intersection_id),
                "section_count": int(len(group)),
                "approach_count": int((group["section_type"] == "approach").sum()),
                "corridor_count": int((group["section_type"] == "corridor").sum()),
                "total_capacity_vehicles": int(group["kapasitas_kendaraan"].sum()),
                "total_capacity_smp_per_jam": int(group["kapasitas_smp_per_jam"].sum()),
                "kendaraan": self._vehicle_totals(group),
                "avg_vc_ratio": _num(group["vc_ratio"].mean()),
                "avg_speed_kmh": _num(group["avg_speed_kmh"].mean(), 2),
            }
            for intersection_id, group in rows.groupby("intersection_id")
        ]
        los_counts = rows["los"].value_counts()
        return {
            "tick": int(tick),
            "section_count": int(len(rows)),
            "approach_count": int(len(approach)),
            "corridor_count": int(len(corridor)),
            "total_capacity_vehicles": int(rows["kapasitas_kendaraan"].sum()),
            "total_capacity_smp_per_jam": int(rows["kapasitas_smp_per_jam"].sum()),
            "total_kendaraan": self._vehicle_totals(rows),
            "avg_vc_ratio": _num(rows["vc_ratio"].mean()),
            "avg_speed_kmh": _num(rows["avg_speed_kmh"].mean(), 2),
            "los_distribution": {grade: int(los_counts.get(grade, 0)) for grade in LOS_GRADES},
            "per_intersection": per_intersection,
        }

    @staticmethod
    def _signal_aggregate(rows: pd.DataFrame) -> dict[str, object]:
        """Aggregate signal timing over approach rows (corridors have no signal)."""
        if rows.empty:
            return {
                "intersection_count": 0,
                "section_count": 0,
                "cycle_length_s": 0.0,
                "avg_green_s": 0.0,
                "avg_red_s": 0.0,
                "avg_wait_time_min": 0.0,
                "avg_queue_veh": 0.0,
                "avg_delay_s": 0.0,
            }
        return {
            "intersection_count": int(rows["intersection_id"].nunique()),
            "section_count": int(len(rows)),
            "cycle_length_s": _num(rows["cycle_length_s"].mean(), 1),
            "avg_green_s": _num(rows["green_seconds"].mean(), 1),
            "avg_red_s": _num(rows["red_seconds"].mean(), 1),
            "avg_wait_time_min": _num(rows["wait_time_min"].mean(), 2),
            # Tundaan kendali rata-rata: porsi waktu merah yang terpakai antre.
            "avg_delay_s": _num(
                (rows["red_seconds"] * rows["vc_ratio"]).mean(),
                1,
            ),
            "avg_queue_veh": _num(rows["queue_length_veh"].mean(), 1),
        }

    def signals_summary(self, tick: int, scope: str = "all") -> dict[str, object]:
        """Return signal-timing aggregates for a tick, corridors excluded.

        Args:
            tick: Tick to aggregate.
            scope: One of `all`, `perempatan`, `pertigaan`.

        Returns:
            Signal summary payload with per-tipe items and per-intersection rows.
        """
        rows = self.section_rows(tick)
        approach = rows[rows["section_type"] == "approach"]
        scoped = approach if scope == "all" else approach[approach["tipe_persimpangan"] == scope]
        master = self.load_intersections()

        items = [
            {"scope": tipe, **self._signal_aggregate(approach[approach["tipe_persimpangan"] == tipe])}
            for tipe in ("perempatan", "pertigaan")
        ]
        per_intersection = []
        for group in scoped.groupby("intersection_id"):
            intersection_id, group_rows = group
            scoped_metrics = self._signal_aggregate(group_rows)
            scoped_metrics.pop("intersection_count")
            scoped_metrics.pop("section_count")
            meta = master.loc[intersection_id] if intersection_id in master.index else None
            per_intersection.append(
                {
                    "intersection_id": str(intersection_id),
                    "intersection_name": str(meta["intersection_name"]) if meta is not None else "",
                    "tipe_persimpangan": str(group_rows["tipe_persimpangan"].iloc[0]),
                    "jumlah_lengan": int(group_rows["jumlah_lengan"].iloc[0]),
                    "section_count": int(len(group_rows)),
                    "cycle_length_s": (
                        int(meta["cycle_length_s"]) if meta is not None else int(
                            group_rows["cycle_length_s"].iloc[0],
                        )
                    ),
                    **scoped_metrics,
                },
            )

        return {
            "scope": scope,
            "timestamp_wib": self.timestamp_for_tick(tick),
            **self._signal_aggregate(scoped),
            "items": [item for item in items if scope == "all" or item["scope"] == scope],
            "per_intersection": per_intersection,
        }


analytics_loader = AnalyticsLoader()
