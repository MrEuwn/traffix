"""Evidence endpoints: real artefacts, missing artefacts, and unambiguous model mode."""

from app.routes import model_eval
from app.services import frame_service as frame_module
from ml.forecast import runtime as forecast_runtime
from ml.registry import registry


def _data(response):
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]


def test_forecast_evaluation_serves_the_artefact(api_client):
    data = _data(api_client.get("/api/v1/model/evaluation/forecast"))
    assert data["available"] is True
    assert set(data["horizons"]) == {"15m", "2h", "4h"}
    assert data["dataset"]["provenance"] == "sintetis"
    for horizon in data["horizons"].values():
        roles = {row["role"] for row in horizon["comparison"]}
        assert roles == {"model", "baseline", "pembanding"}
        assert "lstm_training_history" not in horizon


def test_forecast_evaluation_missing_artefact_is_explicit(api_client, monkeypatch, tmp_path):
    monkeypatch.setattr(model_eval, "EVALUATION_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(forecast_runtime, "EVALUATION_PATH", tmp_path / "absent.json")
    data = _data(api_client.get("/api/v1/model/evaluation/forecast"))
    assert data["available"] is False
    assert "run_d2_evaluation.py" in data["command"]
    series = api_client.get("/api/v1/model/evaluation/forecast/15m/series")
    assert series.status_code == 404


def test_series_rejects_unknown_horizon_and_intersection(api_client):
    assert api_client.get("/api/v1/model/evaluation/forecast/1d/series").status_code == 404
    bad = api_client.get("/api/v1/model/evaluation/forecast/15m/series?intersection=INT-999")
    assert bad.status_code == 404
    ok = _data(api_client.get("/api/v1/model/evaluation/forecast/15m/series?intersection=INT-002"))
    assert ok["intersection"] == "INT-002" and ok["points"]


def test_model_status_reports_fallback_not_lstm_when_models_absent(api_client):
    registry.clear()
    registry.set_fallback_mode(True)
    data = _data(api_client.get("/api/v1/model/status"))
    assert data["mode"] in {"heuristic_fallback", "disabled"}
    assert data["matches_evaluation"] is False
    registry.clear()


def test_frames_catalogue_and_missing_detections(api_client, monkeypatch, tmp_path):
    data = _data(api_client.get("/api/v1/cameras/frames"))
    assert data["available"] is True and data["source"]["kind"] == "replay_rekaman_cctv_publik"
    frame_id = data["frames"][0]["frame_id"]
    image = api_client.get(f"/api/v1/cameras/frames/{frame_id}/image")
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    assert api_client.get("/api/v1/cameras/frames/not-a-frame/image").status_code == 404

    empty = frame_module.FrameService()
    monkeypatch.setattr(frame_module, "DETECTIONS_PATH", tmp_path / "absent.json")
    monkeypatch.setattr("app.routes.cameras.frame_service", empty)
    missing = _data(api_client.get("/api/v1/cameras/frames"))
    assert missing["available"] is False and "run_yolo_frames.py" in missing["reason"]
