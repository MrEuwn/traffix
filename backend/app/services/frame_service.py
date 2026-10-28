"""Recorded CCTV frames and their YOLOv8 detections.

Two modes, always labelled:
- `precomputed`: boxes from `backend/scripts/run_yolo_frames.py` (real YOLO output,
  computed earlier, stored in detections.json).
- `live`: the same weights, imgsz and classes as the stored run, executed now on
  request, when ultralytics is installed.
Either way the input is a REPLAY of recorded public CCTV footage, never a live feed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

from core.logger import get_logger
from core.paths import repo_root

logger = get_logger("system")

DETECTION_DIR = Path(__file__).resolve().parents[2] / "ml" / "detection" / "artifacts"
DETECTIONS_PATH = DETECTION_DIR / "detections.json"
EVIDENCE_PATH = DETECTION_DIR / "yolo_evidence.json"
DEFAULT_WEIGHTS = repo_root() / "yolo pipeline" / "model" / "yolov8m_inatrc.pt"


class FrameService:
    """Serve the frame catalogue, annotated images and on-demand inference."""

    def __init__(self) -> None:
        self._catalogue: dict | None = None
        self._model = None
        self._lock = Lock()

    def catalogue(self) -> dict | None:
        if self._catalogue is None and DETECTIONS_PATH.exists():
            self._catalogue = json.loads(DETECTIONS_PATH.read_text(encoding="utf-8"))
        return self._catalogue

    def frame(self, frame_id: str) -> dict | None:
        catalogue = self.catalogue()
        if not catalogue:
            return None
        return next((f for f in catalogue["frames"] if f["frame_id"] == frame_id), None)

    def image_path(self, frame_id: str, annotated: bool) -> Path | None:
        """Resolve only paths listed in the catalogue (no user-controlled paths)."""
        record = self.frame(frame_id)
        if record is None:
            return None
        path = repo_root() / (record["annotated_frame"] if annotated else record["source_frame"])
        if not annotated and not path.exists():
            # The backend image ships only annotated frames; fall back to them.
            path = repo_root() / record["annotated_frame"]
        return path if path.exists() else None

    def _model_settings(self) -> tuple[Path, int, str]:
        """Weights, imgsz and mode of the stored detections, so live == precomputed."""
        model = (self.catalogue() or {}).get("model", {})
        weights = repo_root() / model["weights"] if model.get("weights") else DEFAULT_WEIGHTS
        return weights, int(model.get("imgsz", 1280)), str(model.get("mode", "full"))

    def live_available(self) -> tuple[bool, str | None]:
        weights, _, _ = self._model_settings()
        if not weights.exists():
            return False, f"bobot YOLO tidak ada: {weights.name}"
        try:
            import ultralytics  # noqa: F401
        except ImportError:
            return False, "ultralytics tidak terpasang di image ini; hanya hasil inferensi tersimpan yang tersedia"
        return True, None

    def infer(self, frame_id: str, conf: float = 0.25) -> dict:
        """Run YOLO now on the recorded frame. Raises LookupError/RuntimeError."""
        record = self.frame(frame_id)
        if record is None:
            raise LookupError(frame_id)
        ok, reason = self.live_available()
        if not ok:
            raise RuntimeError(reason)
        source = repo_root() / record["source_frame"]
        if not source.exists():
            raise RuntimeError("frame mentah tidak dibundel di image ini")
        import cv2

        from app.services.detector import detect

        weights, imgsz, mode = self._model_settings()
        with self._lock:
            if self._model is None:
                from ultralytics import YOLO

                self._model = YOLO(str(weights))
            t0 = time.perf_counter()
            boxes = detect(self._model, cv2.imread(str(source)), mode=mode, imgsz=imgsz, conf=conf)
            elapsed = (time.perf_counter() - t0) * 1000
        return {
            "frame_id": frame_id,
            "mode": "live",
            "inference_mode": mode,
            "conf_threshold": conf,
            "vehicle_count": len(boxes),
            "inference_ms": round(elapsed, 1),
            "boxes": boxes,
            "width": record["width"],
            "height": record["height"],
        }

    def evidence(self) -> dict | None:
        if not EVIDENCE_PATH.exists():
            return None
        return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


frame_service = FrameService()
