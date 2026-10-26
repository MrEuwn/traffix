"""Schema, leakage-guard, and endpoint tests for the v4 analytics layer.

Contract under test: `docs/SCHEMA-v4.md` §3.3.
"""

from __future__ import annotations

import pytest

from ml.bottleneck.classifier import bottleneck_classifier
from ml.bottleneck.features import CLASSES, FORBIDDEN_COLUMNS
from sim.analytics_loader import MODEL_INPUT_COLUMNS, analytics_loader

EXPECTED_CAUSES = set(CLASSES)
INTERSECTION_IDS = {f"INT-00{index}" for index in range(1, 7)}
TICK = 1000


# --- loader ---------------------------------------------------------------


def test_loader_section_counts_and_master_tables():
    rows = analytics_loader.section_rows(TICK)
    assert len(rows) == 30
    assert (rows["section_type"] == "approach").sum() == 21
    assert (rows["section_type"] == "corridor").sum() == 9

    sections = analytics_loader.load_sections()
    intersections = analytics_loader.load_intersections()
    assert len(sections) == 30
    assert list(intersections.index) == sorted(INTERSECTION_IDS)
    assert set(intersections["tipe_persimpangan"]) == {"perempatan", "pertigaan"}


def test_loader_tick_timestamp_tracking():
    analytics_loader.set_current_tick(TICK)
    assert analytics_loader.resolve_tick() == TICK

    explicit = analytics_loader.resolve_tick(2500)
    assert explicit == 2500
    assert analytics_loader.current_tick == 2500

    clamped = analytics_loader.set_current_tick(10_000_000)
    assert clamped == analytics_loader.latest_tick() == 10079
    assert analytics_loader.timestamp_for_tick(clamped) == "2026-05-07T23:59:00+07:00"


def test_loader_never_feeds_forbidden_columns_to_the_classifier():
    assert set(MODEL_INPUT_COLUMNS).isdisjoint(FORBIDDEN_COLUMNS)
    for intersection_id in sorted(INTERSECTION_IDS):
        frame = analytics_loader.model_input_frame(TICK, intersection_id=intersection_id)
        assert tuple(frame.columns) == MODEL_INPUT_COLUMNS
        assert set(frame.columns).isdisjoint(FORBIDDEN_COLUMNS)
        assert not frame.empty
    window = analytics_loader.model_input_frame(TICK)
    assert len(window) > len(analytics_loader.section_rows(TICK))  # lag warm-up included


def test_classifier_only_receives_allowed_columns(monkeypatch):
    """The frames handed to `predict_proba` must stay leakage-free."""
    captured = []
    original = bottleneck_classifier.predict_proba

    def spy(frame):
        captured.append(frame)
        return original(frame)

    monkeypatch.setattr(bottleneck_classifier, "predict_proba", spy)

    probabilities = bottleneck_classifier_probabilities_for_int001()
    assert pytest.approx(sum(probabilities.values()), abs=1e-3) == 1.0
    assert captured, "classifier was never called"
    for frame in captured:
        assert set(frame.columns).isdisjoint(FORBIDDEN_COLUMNS)


def bottleneck_classifier_probabilities_for_int001() -> dict[str, float]:
    """Run the route-level probability helper for one intersection."""
    from app.routes.bottlenecks import _class_probabilities

    frame = analytics_loader.model_input_frame(TICK, intersection_id="INT-001")
    return dict(zip(CLASSES, _class_probabilities(frame, TICK)))


# --- endpoints ------------------------------------------------------------


def test_bottlenecks_endpoint_shape(api_client):
    response = api_client.get(f"/api/v1/bottlenecks?tick={TICK}")
    assert response.status_code == 200
    payload = response.json()

    assert set(payload) == {
        "tick",
        "timestamp_wib",
        "section_count",
        "affected_section_count",
        "dominant_cause",
        "causes",
        "per_intersection",
        "model_available",
        "synthetic_data",
        "disclosure",
    }
    assert payload["tick"] == TICK
    assert payload["section_count"] == 30
    assert payload["synthetic_data"] is True
    assert "sintetis" in payload["disclosure"]
    assert 0 <= payload["affected_section_count"] <= 30
    assert payload["dominant_cause"] in EXPECTED_CAUSES
    assert payload["causes"] and "normal" not in {item["cause"] for item in payload["causes"]}

    intersections = payload["per_intersection"]
    assert {item["intersection_id"] for item in intersections} == INTERSECTION_IDS
    for item in intersections:
        assert set(item["probabilities"]) == EXPECTED_CAUSES
        assert abs(sum(item["probabilities"].values()) - 1.0) < 1e-3
        assert len(item["top3"]) == 3
        assert item["top3"][0]["cause"] == item["dominant_cause"]
        assert item["drivers"]
        assert item["tipe_persimpangan"] in {"perempatan", "pertigaan"}
        if payload["model_available"]:
            assert 0.0 <= item["confidence"] <= 1.0
        else:
            assert item["confidence"] == 0.0


def test_bottlenecks_endpoint_uses_tracked_tick_by_default(api_client):
    analytics_loader.set_current_tick(TICK)
    response = api_client.get("/api/v1/bottlenecks")
    assert response.status_code == 200
    assert response.json()["tick"] == TICK
    assert analytics_loader.current_tick == TICK


def test_bottleneck_detail_endpoint(api_client):
    response = api_client.get(f"/api/v1/bottlenecks/INT-001?tick={TICK}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["intersection_id"] == "INT-001"
    assert payload["intersection_name"] == "Simpang Meruya Utara"
    assert len(payload["history"]) == 60
    assert payload["history"][-1]["tick"] == TICK
    for point in payload["history"]:
        assert set(point) == {
            "tick",
            "timestamp_wib",
            "dominant_cause",
            "confidence",
            "vc_ratio",
            "queue_length_veh",
            "avg_speed_kmh",
        }
        assert point["dominant_cause"] in EXPECTED_CAUSES
    assert len(payload["sections"]) == 4
    assert all(item["section_type"] == "approach" for item in payload["sections"])


def test_bottleneck_detail_unknown_intersection_returns_404(api_client):
    response = api_client.get("/api/v1/bottlenecks/INT-999")
    assert response.status_code == 404


def test_segments_endpoint(api_client):
    response = api_client.get(f"/api/v1/segments?tick={TICK}")
    assert response.status_code == 200
    payload = response.json()

    assert set(payload) == {"tick", "count", "total_capacity_vehicles", "items"}
    assert payload["count"] == len(payload["items"]) == 30
    assert payload["total_capacity_vehicles"] > 0

    section = payload["items"][0]
    assert set(section) == {
        "section_id",
        "nama_ruas",
        "section_type",
        "intersection_id",
        "tipe_persimpangan",
        "approach",
        "panjang_m",
        "jumlah_lajur",
        "kapasitas_smp_per_jam",
        "kapasitas_kendaraan",
        "volume_veh_per_hour",
        "vc_ratio",
        "los",
        "avg_speed_kmh",
        "queue_length_veh",
        "wait_time_min",
        "kendaraan",
        "bottleneck_cause",
        "penyebab_dominan",
    }
    assert section["bottleneck_cause"] in EXPECTED_CAUSES
    assert section["penyebab_dominan"] in EXPECTED_CAUSES
    assert section["los"] in {"A", "B", "C", "D", "E", "F"}

    kendaraan = section["kendaraan"]
    assert kendaraan["total"] == (
        kendaraan["roda_2"] + kendaraan["roda_3"] + kendaraan["roda_4"] + kendaraan["roda_6plus"]
    )
    assert abs(sum(kendaraan["persen"].values()) - 1.0) < 0.01
    expected_smp = (
        0.25 * kendaraan["roda_2"]
        + 0.50 * kendaraan["roda_3"]
        + kendaraan["roda_4"]
        + 1.30 * kendaraan["roda_6plus"]
    )
    assert kendaraan["smp_ekivalen"] == pytest.approx(expected_smp, rel=1e-3)


def test_segments_endpoint_filters(api_client):
    approach = api_client.get(f"/api/v1/segments?tick={TICK}&section_type=approach").json()
    corridor = api_client.get(f"/api/v1/segments?tick={TICK}&section_type=corridor").json()
    perempatan = api_client.get(f"/api/v1/segments?tick={TICK}&tipe=perempatan").json()
    pertigaan = api_client.get(f"/api/v1/segments?tick={TICK}&tipe=pertigaan").json()

    assert approach["count"] == 21
    assert corridor["count"] == 9
    assert perempatan["count"] == 12
    assert pertigaan["count"] == 9
    assert all(item["section_type"] == "approach" for item in approach["items"])
    assert all(item["approach"] == "" for item in corridor["items"])


def test_segments_summary_endpoint(api_client):
    response = api_client.get(f"/api/v1/segments/summary?tick={TICK}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["section_count"] == 30
    assert payload["approach_count"] == 21
    assert payload["corridor_count"] == 9
    assert payload["total_capacity_vehicles"] > 0
    assert payload["total_capacity_smp_per_jam"] > 0
    assert set(payload["los_distribution"]) == {"A", "B", "C", "D", "E", "F"}
    assert sum(payload["los_distribution"].values()) == 30
    assert payload["total_kendaraan"]["total"] > 0
    intersections = {item["intersection_id"] for item in payload["per_intersection"]}
    assert intersections == INTERSECTION_IDS | {f"COR-00{index}" for index in range(1, 10)}


def test_signals_summary_excludes_corridors(api_client):
    response = api_client.get(f"/api/v1/signals/summary?scope=all&tick={TICK}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["scope"] == "all"
    assert payload["intersection_count"] == 6
    assert payload["section_count"] == 21  # corridors excluded
    assert payload["cycle_length_s"] > 0
    assert payload["avg_green_s"] > 0
    assert payload["avg_red_s"] > 0
    assert payload["avg_delay_s"] > 0

    assert {item["scope"] for item in payload["items"]} == {"perempatan", "pertigaan"}
    per_tipe = {item["scope"]: item for item in payload["items"]}
    assert per_tipe["perempatan"]["section_count"] == 12
    assert per_tipe["pertigaan"]["section_count"] == 9
    assert per_tipe["perempatan"]["cycle_length_s"] == 120.0
    assert per_tipe["pertigaan"]["cycle_length_s"] == 80.0
    assert per_tipe["perempatan"]["avg_green_s"] > per_tipe["pertigaan"]["avg_green_s"] or (
        per_tipe["perempatan"]["avg_green_s"] != per_tipe["pertigaan"]["avg_green_s"]
    )

    per_intersection = payload["per_intersection"]
    assert {item["intersection_id"] for item in per_intersection} == INTERSECTION_IDS
    assert all(not item["intersection_id"].startswith("COR-") for item in per_intersection)
    assert {item["tipe_persimpangan"] for item in per_intersection} == {"perempatan", "pertigaan"}


def test_signals_summary_scope_split(api_client):
    perempatan = api_client.get(f"/api/v1/signals/summary?scope=perempatan&tick={TICK}").json()
    pertigaan = api_client.get(f"/api/v1/signals/summary?scope=pertigaan&tick={TICK}").json()

    assert perempatan["section_count"] == 12
    assert perempatan["intersection_count"] == 3
    assert perempatan["cycle_length_s"] == 120.0
    assert [item["scope"] for item in perempatan["items"]] == ["perempatan"]
    assert all(item["tipe_persimpangan"] == "perempatan" for item in perempatan["per_intersection"])

    assert pertigaan["section_count"] == 9
    assert pertigaan["intersection_count"] == 3
    assert pertigaan["cycle_length_s"] == 80.0
    assert [item["scope"] for item in pertigaan["items"]] == ["pertigaan"]
    assert all(item["tipe_persimpangan"] == "pertigaan" for item in pertigaan["per_intersection"])

    assert api_client.get("/api/v1/signals/summary?scope=banjir").status_code == 422


def test_model_evaluation_endpoint_never_500(api_client):
    response = api_client.get("/api/v1/model/evaluation")
    assert response.status_code == 200
    payload = response.json()
    assert "available" in payload
    if payload["available"]:
        assert set(payload["classes"]) == EXPECTED_CAUSES
        assert set(payload["metrics"]) >= {"macro_f1", "balanced_accuracy", "accuracy"}
        assert set(payload["baselines"]) == {"majority_class", "rule_based"}
        assert {item["cause"] for item in payload["per_class"]} == EXPECTED_CAUSES
        assert payload["confusion_matrix"]["labels"] == payload["classes"]
        assert payload["feature_importance"]
        assert payload["leakage_guard"] and payload["limitations"]
        assert payload["split"]["protocol"]
        assert payload["artifacts"]["model"]
    else:
        assert payload["reason"]
