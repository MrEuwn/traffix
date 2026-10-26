"""Contract tests for the v4 bottleneck classifier artifacts (SCHEMA-v4 §4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.bottleneck.classifier import ARTIFACT_DIR, bottleneck_classifier
from ml.bottleneck.features import CLASSES, FEATURE_COLUMNS, FORBIDDEN_COLUMNS

METRICS_PATH = ARTIFACT_DIR / "metrics.json"
CARD_PATH = Path(__file__).resolve().parents[1] / "ml" / "bottleneck" / "model_card.md"
HEADLINE = ("macro_f1", "balanced_accuracy", "accuracy")


@pytest.fixture(scope="module")
def metrics() -> dict:
    assert METRICS_PATH.exists(), f"metrics.json belum ada: {METRICS_PATH}"
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def test_artifact_exists_and_loads() -> None:
    assert (ARTIFACT_DIR / "bottleneck_classifier.joblib").exists()
    assert bottleneck_classifier.available is True
    assert bottleneck_classifier.model_name and bottleneck_classifier.model_name != "rule_based_fallback"
    assert bottleneck_classifier.classes == list(CLASSES)


def test_no_forbidden_feature_reaches_model() -> None:
    columns = bottleneck_classifier.feature_columns
    assert columns, "feature_columns kosong"
    assert not set(columns) & set(FORBIDDEN_COLUMNS), "kolom terlarang masuk model"
    assert set(columns) == set(FEATURE_COLUMNS)


def test_metrics_json_matches_schema(metrics: dict) -> None:
    required = {
        "model_name", "trained_at", "n_train", "n_validation", "n_test", "classes",
        "feature_columns", "forbidden_columns", "metrics", "baselines", "per_class",
        "confusion_matrix", "feature_importance", "leakage_guard", "limitations",
    }
    assert required <= set(metrics), f"key hilang: {sorted(required - set(metrics))}"

    assert metrics["classes"] == list(CLASSES)
    assert len(metrics["feature_columns"]) == len(FEATURE_COLUMNS)
    assert set(metrics["forbidden_columns"]) == set(FORBIDDEN_COLUMNS)
    assert all(isinstance(metrics[k], int) and metrics[k] > 0 for k in ("n_train", "n_validation", "n_test"))

    for value in metrics["metrics"].values():
        assert isinstance(value, float) and 0.0 <= value <= 1.0
    for name in ("majority_class", "rule_based"):
        scores = metrics["baselines"][name]
        assert all(k in scores and 0.0 <= scores[k] <= 1.0 for k in HEADLINE)

    assert len(metrics["per_class"]) == len(CLASSES)
    for row in metrics["per_class"]:
        assert set(row) == {"cause", "precision", "recall", "f1", "support"}
        assert row["cause"] in CLASSES and row["support"] >= 0

    cm = metrics["confusion_matrix"]
    assert cm["labels"] == list(CLASSES)
    assert len(cm["matrix"]) == len(CLASSES) and all(len(r) == len(CLASSES) for r in cm["matrix"])
    assert sum(sum(r) for r in cm["matrix"]) == metrics["n_test"]

    top = metrics["feature_importance"]
    assert 0 < len(top) <= 20
    assert all(set(r) == {"feature", "importance"} and r["feature"] in FEATURE_COLUMNS for r in top)

    assert metrics["leakage_guard"] and metrics["limitations"]
    assert len(metrics["limitations"]) >= 6
    assert all(isinstance(x, str) and x.strip() for x in metrics["leakage_guard"] + metrics["limitations"])


def test_model_beats_rule_based_baseline(metrics: dict) -> None:
    assert metrics["metrics"]["macro_f1"] > metrics["baselines"]["rule_based"]["macro_f1"]
    assert metrics["metrics"]["macro_f1"] > metrics["baselines"]["majority_class"]["macro_f1"]


def test_model_card_written() -> None:
    assert CARD_PATH.exists()
    text = CARD_PATH.read_text(encoding="utf-8")
    assert "seed 42" in text and "macro-F1" in text
