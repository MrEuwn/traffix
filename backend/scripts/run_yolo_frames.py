#!/usr/bin/env python3
"""Run YOLOv8 on the recorded CCTV frames for the camera demo.

Real inference, not a mock. The frames under
`inference_data/data_video/frames/{pagi,siang,malam}/` were cut from public Bina
Marga toll-road CCTV recordings (Jakarta-Tangerang); they are a REPLAY of past
footage, not a live feed, and they do not show the six simulated intersections.

Detector (default): `yolo pipeline/model/yolov8m_coco.pt`, the Ultralytics YOLOv8m
checkpoint pretrained on COCO, restricted to the vehicle classes car / motorcycle /
bus / truck, at imgsz 1280. It replaced the team model for the demo because the team
model (`best.pt`, 1 class, trained on 399 close-up Kaggle images) misses most of the
small, distant vehicles on these toll cameras. The team model still runs on every
frame and its count is stored next to the demo detector's as a comparison.

There are no reference labels for these frames: counts are model output, not accuracy.

Writes (idempotent, overwrites only its own outputs):
    backend/ml/detection/artifacts/detections.json
    backend/ml/detection/artifacts/frames/<period>/<frame>.jpg   (boxes drawn)

Usage:
    python backend/scripts/run_yolo_frames.py [--weights PATH] [--conf 0.25] [--imgsz 1280]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "yolo pipeline" / "model"
DEMO_WEIGHTS = MODEL_DIR / "yolov8m_coco.pt"
TEAM_WEIGHTS = MODEL_DIR / "best.pt"
TEAM_IMGSZ = 640  # the size the team model was trained and validated at
FRAMES = ROOT / "inference_data" / "data_video" / "frames"
METADATA = ROOT / "inference_data" / "data_video" / "metadata" / "video_weather_data.csv"
OUT_DIR = ROOT / "backend" / "ml" / "detection" / "artifacts"
PERIODS = ("pagi", "siang", "malam")
VEHICLE_NAMES = ("car", "motorcycle", "bus", "truck")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vehicle_class_ids(names: dict[int, str]) -> list[int] | None:
    """COCO-style models: keep only vehicle classes. Single-class models: keep all."""
    ids = [i for i, n in names.items() if n in VEHICLE_NAMES]
    return ids if len(names) > 1 and ids else None


def load_metadata() -> dict[str, dict]:
    """Video file -> location/weather metadata (best-effort; frames without it still run)."""
    if not METADATA.exists():
        return {}
    meta = pd.read_csv(METADATA, encoding="utf-8-sig")
    out = {}
    for row in meta.to_dict("records"):
        video = str(row.get("video_file", "")).removesuffix(".mp4")
        out[video] = {
            "ruas": row.get("ruas"),
            "location": row.get("location_text"),
            "camera_id": row.get("camera_id"),
            "recorded_at_wib": row.get("timestamp_wib"),
            "temperature_c": row.get("temperature_2m"),
            "precipitation_mm": row.get("precipitation"),
        }
    return out


def clean(value):
    """NaN -> None so the JSON stays valid."""
    if isinstance(value, float) and value != value:
        return None
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", type=Path, default=DEMO_WEIGHTS)
    parser.add_argument("--conf", type=float, default=0.25, help="confidence threshold (Ultralytics default 0.25)")
    parser.add_argument("--imgsz", type=int, default=1280, help="inference size; 1280 upsamples the 640x480 frames")
    args = parser.parse_args()

    for weights in (args.weights, TEAM_WEIGHTS):
        if not weights.exists():
            print(f"[FAIL] bobot YOLO tidak ada: {weights}", file=sys.stderr)
            return 2
    try:
        import cv2
        import ultralytics
        from ultralytics import YOLO
    except ImportError as exc:
        print(f"[FAIL] ultralytics/opencv belum terpasang: {exc}", file=sys.stderr)
        return 2

    frames = sorted(p for period in PERIODS for p in (FRAMES / period).glob("*.jpg"))
    if not frames:
        print(f"[FAIL] tidak ada frame di {FRAMES}", file=sys.stderr)
        return 2

    model = YOLO(str(args.weights))
    classes = vehicle_class_ids(model.names)
    team = YOLO(str(TEAM_WEIGHTS))
    metadata = load_metadata()
    records = []
    for frame in frames:
        period = frame.parent.name
        t0 = time.perf_counter()
        result = model.predict(str(frame), conf=args.conf, imgsz=args.imgsz, classes=classes,
                               verbose=False, device="cpu")[0]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        team_result = team.predict(str(frame), conf=args.conf, imgsz=TEAM_IMGSZ, verbose=False, device="cpu")[0]
        boxes = [
            {
                "xyxy": [round(float(v), 1) for v in box.xyxy[0].tolist()],
                "confidence": round(float(box.conf[0]), 4),
                "class": result.names[int(box.cls[0])],
            }
            for box in result.boxes
        ]
        out_path = OUT_DIR / "frames" / period / frame.name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), result.plot(line_width=1, font_size=8), [cv2.IMWRITE_JPEG_QUALITY, 85])
        video = frame.stem.rsplit("_frame_", 1)[0]
        height, width = result.orig_shape
        by_class = {name: sum(b["class"] == name for b in boxes) for name in VEHICLE_NAMES}
        records.append({
            "frame_id": frame.stem,
            "period": period,
            "video": video,
            "second": frame.stem.rsplit("_frame_", 1)[-1],
            "source_frame": str(frame.relative_to(ROOT)),
            "annotated_frame": str(out_path.relative_to(ROOT)),
            "width": int(width),
            "height": int(height),
            "vehicle_count": len(boxes),
            "by_class": {k: v for k, v in by_class.items() if v},
            "team_model_vehicle_count": len(team_result.boxes),
            "mean_confidence": round(sum(b["confidence"] for b in boxes) / len(boxes), 4) if boxes else None,
            "inference_ms": round(elapsed_ms, 1),
            "boxes": boxes,
            **{k: clean(v) for k, v in metadata.get(video, {}).items()},
        })
        print(f"  {period}/{frame.name}: {len(boxes)} kendaraan (model tim: {len(team_result.boxes)}) ({elapsed_ms:.0f} ms)")

    def mean(values):
        values = list(values)
        return round(sum(values) / max(1, len(values)), 2)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": "python backend/scripts/run_yolo_frames.py",
        "model": {
            "weights": str(args.weights.relative_to(ROOT)),
            "sha256": sha256(args.weights),
            "description": "YOLOv8m pretrained COCO (Ultralytics), tidak dilatih ulang oleh tim; "
                           "lisensi AGPL-3.0",
            "classes": [model.names[i] for i in classes] if classes else list(model.names.values()),
            "ultralytics_version": ultralytics.__version__,
            "conf_threshold": args.conf,
            "imgsz": args.imgsz,
            "device": "cpu",
        },
        "team_model": {
            "weights": str(TEAM_WEIGHTS.relative_to(ROOT)),
            "sha256": sha256(TEAM_WEIGHTS),
            "classes": list(team.names.values()),
            "imgsz": TEAM_IMGSZ,
            "role": "pembanding per frame; metrik validasinya ada di yolo_evidence.json",
        },
        "source": {
            "kind": "replay_rekaman_cctv_publik",
            "description": "Frame dari rekaman CCTV publik Bina Marga, ruas tol Jakarta-Tangerang "
                           "(pagi/siang/malam, Mei-Juni 2026). Bukan siaran langsung dan bukan simpang simulasi.",
            "frames_dir": str(FRAMES.relative_to(ROOT)),
            "metadata": str(METADATA.relative_to(ROOT)),
        },
        "caveats": [
            "Detektor demo adalah YOLOv8m pretrained COCO, bukan model yang dilatih tim; model tim (best.pt, 1 kelas) "
            "melewatkan sebagian besar kendaraan kecil di CCTV tol sehingga hanya dipakai sebagai pembanding.",
            "Tidak ada label acuan untuk frame CCTV ini: jumlah kotak adalah keluaran model, bukan ukuran akurasi.",
            "Kendaraan yang sangat jauh atau saling menutupi di antrean masih bisa terlewat; sepeda motor kecil paling sulit.",
            "Frame malam: silau lampu menurunkan deteksi dan papan petunjuk terang kadang terbaca sebagai bus.",
        ],
        "summary": {
            "frames": len(records),
            "by_period": {
                p: {
                    "frames": sum(r["period"] == p for r in records),
                    "mean_vehicle_count": mean(r["vehicle_count"] for r in records if r["period"] == p),
                    "mean_team_model_count": mean(r["team_model_vehicle_count"] for r in records if r["period"] == p),
                }
                for p in PERIODS
            },
            "mean_vehicle_count": mean(r["vehicle_count"] for r in records),
            "mean_team_model_count": mean(r["team_model_vehicle_count"] for r in records),
            "by_class_total": {n: sum(r["by_class"].get(n, 0) for r in records) for n in VEHICLE_NAMES},
            "mean_inference_ms": mean(r["inference_ms"] for r in records),
        },
        "frames": records,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "detections.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {len(records)} frame -> {OUT_DIR / 'detections.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
