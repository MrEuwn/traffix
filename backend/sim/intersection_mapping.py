"""Dataset intersection ID mapping for Traffix live state store."""

from typing import Final

# Data team synthetic IDs mapped to Jakarta-Tangerang dashboard intersections.
DATASET_TO_STORE: Final[dict[str, str]] = {
    "JKT-TMG-SIM-01": "INT-001",
    "1": "INT-001",
    "2": "INT-002",
    "3": "INT-003",
    "4": "INT-004",
}

# When the CSV only contains one physical intersection, fan out to dashboard IDs.
DEMO_INTERSECTION_SCALE: Final[dict[str, float]] = {
    "INT-001": 1.0,
    "INT-002": 0.88,
    "INT-003": 1.12,
    "INT-004": 0.95,
    "INT-005": 1.05,
    "INT-006": 0.92,
}

# v4 intersection names mapped to the legacy CCTV metadata labels, so the
# inference insight bridge keeps resolving camera/LSTM rows.
CAMERA_LABEL_ALIASES: Final[dict[str, str]] = {
    "INT-001": "GT MERUYA 2B",
    "INT-002": "KM 00+600",
    "INT-003": "KM 04+600",
    "INT-004": "KM 07+200",
}


def camera_labels_for(intersection_id: str, intersection_name: str = "") -> tuple[str, ...]:
    """Return candidate CCTV labels for an intersection.

    Args:
        intersection_id: State store intersection identifier such as INT-001.
        intersection_name: Current display name of the intersection.

    Returns:
        Tuple of candidate labels, display name first, legacy alias second.
    """
    alias = CAMERA_LABEL_ALIASES.get(intersection_id.strip().upper())
    names = [intersection_name]
    if alias is not None:
        names.append(alias)
    return tuple(name for name in names if name)

DEMO_INTERSECTION_IDS: Final[tuple[str, ...]] = tuple(DEMO_INTERSECTION_SCALE)


def map_dataset_intersection_id(raw_id: str) -> str:
    """Map a dataset intersection identifier to a state store ID.

    Args:
        raw_id: Intersection identifier from the hybrid traffic CSV.

    Returns:
        Mapped state store intersection identifier.
    """
    normalized = raw_id.strip()
    if normalized in DATASET_TO_STORE:
        return DATASET_TO_STORE[normalized]
    if normalized.isdigit():
        candidate = f"INT-{int(normalized):03d}"
        if candidate in DEMO_INTERSECTION_SCALE:
            return candidate
    return normalized
