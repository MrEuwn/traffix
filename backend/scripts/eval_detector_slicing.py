#!/usr/bin/env python3
"""Score full-frame vs SAHI-style sliced inference on the InaTRC test split (one 'vehicle' class).

Same eval for every detector: predictions and labels are collapsed to a single vehicle
class, matched greedily by IoU >= 0.5 (highest confidence first). Reports precision,
recall, F1 at the operating confidence, and AP50 from the precision-recall curve.
The test split is used for this comparison only after the model was selected on val.

    python backend/scripts/eval_detector_slicing.py WEIGHTS [WEIGHTS ...] [--imgsz 640]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TEST = ROOT / "data" / "external" / "inatrc" / "test"
OUT = ROOT / "backend" / "ml" / "detection" / "artifacts" / "inatrc_slicing_eval.json"
sys.path.insert(0, str(ROOT / "backend"))

from app.services.detector import detect  # noqa: E402  (shared with run_yolo_frames + API)


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    x0 = np.maximum(a[:, None, 0], b[None, :, 0])
    y0 = np.maximum(a[:, None, 1], b[None, :, 1])
    x1 = np.minimum(a[:, None, 2], b[None, :, 2])
    y1 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    area = lambda r: (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])  # noqa: E731
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def load_labels(path: Path, w: int, h: int) -> np.ndarray:
    rows = [l.split() for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    out = [[(float(x) - float(bw) / 2) * w, (float(y) - float(bh) / 2) * h,
            (float(x) + float(bw) / 2) * w, (float(y) + float(bh) / 2) * h] for _, x, y, bw, bh, *_ in rows]
    return np.array(out, dtype=float).reshape(-1, 4)


def evaluate(model, mode: str, imgsz: int, conf: float) -> dict:
    import cv2

    scores, hits, n_gt = [], [], 0
    for img_path in sorted((TEST / "images").glob("*")):
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        gt = load_labels(TEST / "labels" / (img_path.stem + ".txt"), w, h)
        n_gt += len(gt)
        boxes = detect(model, img, mode=mode, imgsz=imgsz, conf=0.05)
        if not boxes:
            continue
        pred = np.array([b["xyxy"] for b in boxes])
        sc = np.array([b["confidence"] for b in boxes])
        order = np.argsort(-sc)
        matched = np.zeros(len(gt), dtype=bool)
        ious = iou(pred[order], gt) if len(gt) else np.zeros((len(pred), 0))
        for k, i in enumerate(order):
            j = int(np.argmax(ious[k])) if ious.shape[1] else -1
            ok = j >= 0 and ious[k, j] >= 0.5 and not matched[j]
            if ok:
                matched[j] = True
            scores.append(sc[i])
            hits.append(ok)
    scores, hits = np.array(scores), np.array(hits, dtype=bool)
    order = np.argsort(-scores)
    tp = np.cumsum(hits[order])
    fp = np.cumsum(~hits[order])
    recall = tp / max(n_gt, 1)
    precision = tp / np.maximum(tp + fp, 1)
    # AP50: area under the monotone precision envelope (all-point interpolation)
    env = np.maximum.accumulate(precision[::-1])[::-1]
    ap50 = float(np.sum(np.diff(np.concatenate([[0], recall])) * env)) if len(recall) else 0.0
    at = scores[order] >= conf
    tp_c, fp_c = int(hits[order][at].sum()), int((~hits[order][at]).sum())
    p, r = tp_c / max(tp_c + fp_c, 1), tp_c / max(n_gt, 1)
    return {"mode": mode, "imgsz": imgsz, "ap50": round(ap50, 4), "operating_conf": conf,
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / max(p + r, 1e-9), 4),
            "tp": tp_c, "fp": fp_c, "fn": n_gt - tp_c, "n_ground_truth": n_gt}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("weights", nargs="+", type=Path)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()
    from ultralytics import YOLO

    results = []
    for w in args.weights:
        model = YOLO(str(w))
        for mode in ("full", "sliced"):
            r = evaluate(model, mode, args.imgsz, args.conf)
            r["weights"] = str(w.relative_to(ROOT) if w.is_relative_to(ROOT) else w)
            print(json.dumps(r), flush=True)
            results.append(r)
    OUT.write_text(json.dumps({"split": "InaTRC test (325 frame)", "match": "IoU>=0.5, satu kelas kendaraan",
                               "results": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
