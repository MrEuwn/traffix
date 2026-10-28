#!/usr/bin/env python3
"""Pitch figures built only from saved artefacts and real model runs.

Writes to docs/evidence/d2/figures/:
- cctv_detector_comparison.png : same CCTV frames, team best.pt vs COCO YOLOv8m vs fine-tuned InaTRC
- detector_test_metrics.png    : InaTRC test P/R/F1/AP50 (inatrc_slicing_eval.json)
- forecast_mae_table.png       : LSTM vs baselines per horizon (forecast_evaluation.json)
- yolo_training_curves.png     : val mAP per epoch, both fine-tune stages (results.csv)

    python backend/scripts/make_pitch_figures.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.detector import detect  # noqa: E402

FIG = ROOT / "docs" / "evidence" / "d2" / "figures"
MODELS = ROOT / "yolo pipeline" / "model"
RUNS = ROOT / "yolo pipeline" / "runs"
DET = ROOT / "backend" / "ml" / "detection" / "artifacts"
FRAMES = ["siang/siang_cctv_007_20260518_160452_frame_3s.jpg", "pagi/pagi_cctv_002_20260518_070954_frame_3s.jpg"]
INK, MUTED, ACCENT, ACCENT2, BG = "#1d2433", "#5b6475", "#2a6fdb", "#e07a1f", "#fbfaf7"

plt.rcParams.update({"font.size": 13, "axes.edgecolor": "#c9ccd3", "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": BG, "axes.facecolor": BG})


def boxed(img, boxes, color):
    out = img.copy()
    for b in boxes:
        x0, y0, x1, y1 = (int(v) for v in b["xyxy"])
        cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def cctv_comparison():
    from ultralytics import YOLO

    specs = [("Model tim awal (best.pt, Kaggle)", MODELS / "best.pt", 640, (40, 40, 220)),
             ("YOLOv8m COCO (tanpa fine-tune)", MODELS / "yolov8m_coco.pt", 1280, (31, 122, 224)),
             ("YOLOv8m fine-tune InaTRC (dipakai)", MODELS / "yolov8m_inatrc.pt", 640, (219, 111, 42))]
    models = [(t, YOLO(str(w)), s, c) for t, w, s, c in specs]
    fig, axes = plt.subplots(len(FRAMES), 3, figsize=(18, 5.4 * len(FRAMES)))
    for r, f in enumerate(FRAMES):
        img = cv2.imread(str(ROOT / "inference_data/data_video/frames" / f))
        for c, (title, m, imgsz, color) in enumerate(models):
            boxes = detect(m, img, mode="full", imgsz=imgsz, conf=0.25)
            ax = axes[r, c]
            ax.imshow(boxed(img, boxes, color))
            ax.set_axis_off()
            ax.set_title(f"{title}\n{len(boxes)} kendaraan terdeteksi", fontsize=14, color=INK)
    fig.tight_layout(h_pad=2.5)
    fig.savefig(FIG / "cctv_detector_comparison.png", dpi=110)
    plt.close(fig)


def detector_metrics():
    data = json.loads((DET / "inatrc_slicing_eval.json").read_text())["results"]
    keep = [r for r in data if r["mode"] == "full"]
    labels = ["YOLOv8m COCO\n(tanpa fine-tune)", "YOLOv8m\nfine-tune InaTRC"]
    metrics = [("precision", "Presisi"), ("recall", "Recall"), ("f1", "F1"), ("ap50", "AP50")]
    x = np.arange(len(metrics))
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for i, (r, lab, col) in enumerate(zip(keep, labels, ["#9aa3b2", ACCENT2])):
        vals = [r[k] for k, _ in metrics]
        bars = ax.bar(x + (i - 0.5) * 0.36, vals, 0.34, label=lab.replace("\n", " "), color=col)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.3f}", ha="center", fontsize=12)
    ax.set_xticks(x, [m for _, m in metrics])
    ax.set_ylim(0, 1.08)
    ax.set_title(f"Set uji InaTRC — {keep[0]['n_ground_truth']:,} kendaraan berlabel, 325 frame, IoU ≥ 0,5".replace(",", "."))
    ax.legend(frameon=False, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "detector_test_metrics.png", dpi=130)
    plt.close(fig)


def yolo_curves():
    fig, ax = plt.subplots(figsize=(11, 5))
    offset = 0
    for run, label, col in [("inatrc_yolov8m", "Tahap 1 — backbone dibekukan", "#9aa3b2"),
                            ("inatrc_yolov8m_ft", "Tahap 2 — semua lapisan dilatih", ACCENT2)]:
        rows = list(csv.DictReader(open(RUNS / run / "results.csv")))
        ep = [offset + int(r["epoch"]) for r in rows]
        ax.plot(ep, [float(r["metrics/mAP50(B)"]) for r in rows], "-o", color=col, label=f"{label}: mAP50")
        ax.plot(ep, [float(r["metrics/mAP50-95(B)"]) for r in rows], "--", color=col, alpha=0.8, label=f"{label}: mAP50-95")
        offset = ep[-1]
    ax.set_xlabel("epoch (kumulatif)")
    ax.set_ylabel("mAP validasi InaTRC (5 golongan)")
    ax.set_ylim(0.3, 0.9)
    ax.legend(frameon=False, fontsize=11, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "yolo_training_curves.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    detector_metrics()
    yolo_curves()
    cctv_comparison()
    print("ok:", sorted(p.name for p in FIG.glob("*.png")))
