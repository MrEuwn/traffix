"""Feature contract for the bottleneck-cause classifier.

Single source of truth for columns used by training (`train_bottleneck.py`) and by
runtime inference (`classifier.py`). Frozen by `docs/SCHEMA-v4.md` §4.

Leakage policy: every feature is either a physical sensor reading or a lag/rolling
statistic of the past. Event context columns (raw rain, flood depth, lane closure,
signal state, accident count) and the derived `vc_ratio`/`los`/`smp_ekivalen` are
NEVER inputs — they define the label.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BASE_FEATURES: tuple[str, ...] = (
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
    "hour",
    "minute",
    "day_of_week",
    "is_weekend",
    "section_type_is_corridor",
    "tipe_is_perempatan",
)

LAG_TARGETS: tuple[str, ...] = ("volume_veh_per_hour", "queue_length_veh", "avg_speed_kmh")
LAGS: tuple[int, ...] = (1, 5, 15, 30, 60)
ROLLS: tuple[int, ...] = (15, 60)

FEATURE_COLUMNS: tuple[str, ...] = BASE_FEATURES + tuple(
    [f"lag{n}_{col}" for col in LAG_TARGETS for n in LAGS]
    + [f"roll{n}_{stat}_{col}" for col in LAG_TARGETS for n in ROLLS for stat in ("mean", "std")]
)

CLASSES: tuple[str, ...] = (
    "banjir",
    "hujan",
    "kecelakaan",
    "kendaraan_berat",
    "keramaian_event",
    "lampu_mati",
    "normal",
    "perbaikan_jalan",
    "volume_puncak",
)

FORBIDDEN_COLUMNS: tuple[str, ...] = (
    "bottleneck_cause",
    "bottleneck_rule",
    "bottleneck_secondary",
    "weather_condition",
    "curah_hujan_mm_jam",
    "tinggi_genangan_cm",
    "durasi_hujan_menit",
    "lane_closure",
    "pct_lajur_tertutup",
    "durasi_kerja_jalan_menit",
    "event_flag",
    "lampu_operasional",
    "accident_count",
    "roadwork_flag",
    "vc_ratio",
    "los",
    "smp_ekivalen",
)


class LeakageError(ValueError):
    """Raised when a forbidden column is offered as a model feature."""


def assert_no_leakage(feature_names: list[str]) -> None:
    """Raise `LeakageError` when any forbidden column is used as a feature."""
    bad = sorted(set(feature_names) & set(FORBIDDEN_COLUMNS))
    if bad:
        raise LeakageError(f"kolom terlarang dipakai sebagai fitur: {', '.join(bad)}")


def build_feature_frame(df: pd.DataFrame, *, with_lags: bool = True) -> pd.DataFrame:
    """Build the model feature frame from section-level tick rows.

    Args:
        df: Section-level frame containing at least `section_id`, `tick`,
            `timestamp_wib` and the base feature columns.
        with_lags: When False, only `BASE_FEATURES` are returned (useful for tests).

    Returns:
        Frame with exactly `FEATURE_COLUMNS` columns, sorted by section and tick.
    """
    missing = {
        "section_id", "tick", "timestamp_wib",
        "vehicle_count_1min", "volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh",
        "wait_time_min", "green_seconds", "cycle_length_s", "density_percent", "jumlah_lajur",
        "panjang_m", "kapasitas_smp_per_jam", "proporsi_roda_6plus", "weather_temp_c",
        "section_type", "tipe_persimpangan",
    } - set(df.columns)
    if missing:
        raise ValueError(f"kolom wajib fitur tidak ada: {sorted(missing)}")

    frame = df.sort_values(["section_id", "tick"]).reset_index(drop=True)
    ts = pd.to_datetime(frame["timestamp_wib"])
    out = pd.DataFrame(index=frame.index)
    for col in (
        "vehicle_count_1min", "volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh",
        "wait_time_min", "green_seconds", "cycle_length_s", "density_percent", "jumlah_lajur",
        "panjang_m", "kapasitas_smp_per_jam", "proporsi_roda_6plus", "weather_temp_c",
    ):
        out[col] = frame[col].astype(float)
    out["hour"] = ts.dt.hour
    out["minute"] = ts.dt.minute
    out["day_of_week"] = ts.dt.dayofweek
    out["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)
    out["section_type_is_corridor"] = (frame["section_type"] == "corridor").astype(int)
    out["tipe_is_perempatan"] = (frame["tipe_persimpangan"] == "perempatan").astype(int)

    if not with_lags:
        return out[list(BASE_FEATURES)]

    grouped = frame.groupby("section_id", sort=False)
    for col in LAG_TARGETS:
        series = frame[col].astype(float)
        for n in LAGS:
            out[f"lag{n}_{col}"] = series.groupby(frame["section_id"]).shift(n)
        for n in ROLLS:
            shifted = series.groupby(frame["section_id"]).shift(1)
            out[f"roll{n}_mean_{col}"] = shifted.groupby(frame["section_id"]).transform(
                lambda s, w=n: s.rolling(w, min_periods=1).mean()
            )
            out[f"roll{n}_std_{col}"] = shifted.groupby(frame["section_id"]).transform(
                lambda s, w=n: s.rolling(w, min_periods=1).std()
            )
    del grouped

    out = out[list(FEATURE_COLUMNS)].astype(float)
    return out.fillna(0.0)


def _numeric_column(frame: pd.DataFrame, name: str, default: float) -> np.ndarray:
    """Return a 1-D float array for a column, tolerating duplicate column names."""
    if name not in frame.columns:
        return np.full(len(frame), default, dtype=float)
    series = frame[name]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return series.to_numpy(dtype=float)


def rule_based_cause(frame: pd.DataFrame) -> np.ndarray:
    """Baseline 2: rule-of-thumb labels from allowed features only.

    Cannot see the raw event context, so it has to infer the cause from the
    observable traffic state — exactly the job given to the learned model.

    Args:
        frame: Frame containing allowed feature columns.

    Returns:
        Array of cause labels aligned with `frame`.
    """
    speed = _numeric_column(frame, "avg_speed_kmh", 60.0)
    density = _numeric_column(frame, "density_percent", 0.0)
    volume = _numeric_column(frame, "volume_veh_per_hour", 0.0)
    heavy = _numeric_column(frame, "proporsi_roda_6plus", 0.0)
    wait = _numeric_column(frame, "wait_time_min", 0.0)
    hour = _numeric_column(frame, "hour", 12.0)

    peak_hour = ((hour >= 6) & (hour <= 9)) | ((hour >= 16) & (hour <= 19))
    out = np.full(len(frame), "normal", dtype=object)
    out[(speed < 18) & (density > 90)] = "banjir"
    out[(speed < 30) & (density > 70) & (density <= 90) & (wait > 12)] = "kecelakaan"
    out[(speed < 40) & (density > 55) & (density <= 70)] = "hujan"
    out[(heavy >= 0.14) & (density <= 55)] = "kendaraan_berat"
    out[(volume > 6000) & peak_hour & (density > 40)] = "volume_puncak"
    out[(wait > 20) & (speed < 25)] = "perbaikan_jalan"
    return out


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute macro-F1, balanced accuracy, accuracy and per-class scores."""
    labels = list(CLASSES)
    n = len(y_true)
    per_class = []
    recalls = []
    f1s = []
    for label in labels:
        tp = int(np.sum((y_true == label) & (y_pred == label)))
        fp = int(np.sum((y_true != label) & (y_pred == label)))
        fn = int(np.sum((y_true == label) & (y_pred != label)))
        support = int(np.sum(y_true == label))
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        recalls.append(recall)
        f1s.append(f1)
        per_class.append({
            "cause": label,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        })
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    index = {label: i for i, label in enumerate(labels)}
    for truth, pred in zip(y_true, y_pred):
        if truth in index and pred in index:
            matrix[index[truth], index[pred]] += 1
    return {
        "macro_f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
        "balanced_accuracy": round(float(np.mean(recalls)), 4) if recalls else 0.0,
        "accuracy": round(float(np.mean(y_true == y_pred)), 4) if n else 0.0,
        "n": n,
        "per_class": per_class,
        "confusion_matrix": {"labels": labels, "matrix": matrix.tolist()},
    }
