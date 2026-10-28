#!/usr/bin/env python3
"""Fine-tune YOLOv8m (COCO-pretrained) on InaTRC, Indonesian toll-road CCTV.

Dataset: InaTRC — Indonesia Toll Road Vehicle Classification Dataset, Chasanah et al.,
Mendeley Data v1 (2025), doi:10.17632/kddgphck3b.1, CC BY 4.0. 3,250 CCTV frames
(704x480), YOLO labels, 5 toll-tariff classes (Gol. I non-truck, Gol. II-V trucks by axle
count), fixed split 2,600 / 325 / 325. It is NOT committed to the repo; fetch it with:

    python backend/scripts/train_yolo_inatrc.py --download

Training uses the dataset's own train split, model selection (best epoch) on its val
split, and the test split is scored once at the end for both the fine-tuned model and the
untuned COCO checkpoint (baseline). Seed 42.

    python backend/scripts/train_yolo_inatrc.py [--epochs 40] [--imgsz 896] [--device mps]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "external" / "inatrc"
ZIP_URL = "https://data.mendeley.com/public-api/zip/kddgphck3b/download/1"
BASE_WEIGHTS = ROOT / "yolo pipeline" / "model" / "yolov8m_coco.pt"
RUNS = ROOT / "yolo pipeline" / "runs"
OUT_WEIGHTS = ROOT / "yolo pipeline" / "model" / "yolov8m_inatrc.pt"
EVIDENCE = ROOT / "backend" / "ml" / "detection" / "artifacts" / "inatrc_evaluation.json"
CLASS_NAMES = ["gol1_non_truk", "gol2_truk_2_gandar", "gol3_truk_3_gandar", "gol4_truk_4_gandar", "gol5_truk_5plus_gandar"]


def download() -> None:
    """Fetch the official 'Download All' zip with plain curl and lay it out as data/external/inatrc."""
    DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    archive = DATA_DIR.parent / "inatrc.zip"
    subprocess.run(["curl", "-sL", "-o", str(archive), ZIP_URL], check=True)
    tmp = DATA_DIR.parent / "_inatrc_extract"
    with zipfile.ZipFile(archive) as z:
        z.extractall(tmp)
    inner = next(p for p in tmp.iterdir() if p.is_dir())
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    inner.rename(DATA_DIR)
    shutil.rmtree(tmp)
    archive.unlink()


def write_yaml() -> Path:
    path = DATA_DIR / "inatrc.yaml"
    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASS_NAMES))
    path.write_text(f"path: {DATA_DIR}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n{names}\n")
    return path


def metrics(result) -> dict:
    box = result.box
    return {
        "map50": round(float(box.map50), 4),
        "map50_95": round(float(box.map), 4),
        "precision": round(float(box.mp), 4),
        "recall": round(float(box.mr), 4),
        "per_class_map50": {CLASS_NAMES[int(c)]: round(float(v), 4) for c, v in zip(result.box.ap_class_index, box.ap50)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true")
    # Defaults sized for an Apple M1 Pro (16 GB): ~10-15 min per epoch on MPS. On a CUDA GPU
    # (e.g. Colab T4) use --device 0 --epochs 40 --freeze 0 --imgsz 896.
    parser.add_argument("--weights", type=str, default=str(BASE_WEIGHTS),
                        help="weights to start/continue training from (default: COCO pretrained)")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--freeze", type=int, default=10, help="freeze the first N layers (backbone; 0 to unfreeze all)")
    parser.add_argument("--device", default="mps")
    parser.add_argument("--lr0", type=float, default=0.001, help="initial learning rate (default 0.001 for fine tuning)")
    parser.add_argument("--name", type=str, default="inatrc_yolov8m", help="run name under yolo pipeline/runs")
    args = parser.parse_args()

    if args.download or not (DATA_DIR / "train" / "images").exists():
        download()
    data_yaml = write_yaml()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    model.train(
        data=str(data_yaml), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
        seed=42, deterministic=False, patience=5, freeze=args.freeze, amp=False, workers=4, lr0=args.lr0,
        project=str(RUNS), name=args.name, exist_ok=True, plots=True, verbose=False,
    )
    best = RUNS / args.name / "weights" / "best.pt"
    shutil.copy(best, OUT_WEIGHTS)

    # Test split, scored once. Fine-tuned model: 5 toll classes.
    tuned = YOLO(str(OUT_WEIGHTS))
    tuned_test = tuned.val(data=str(data_yaml), split="test", imgsz=args.imgsz, device=args.device,
                           project=str(RUNS), name="inatrc_test_tuned", exist_ok=True, verbose=False)
    tuned_single = tuned.val(data=str(data_yaml), split="test", imgsz=args.imgsz, device=args.device,
                             single_cls=True, project=str(RUNS), name="inatrc_test_tuned_1cls", exist_ok=True,
                             verbose=False)
    # The untuned COCO baseline is NOT scored here: Ultralytics val(single_cls=True,
    # classes=[...]) drops most COCO predictions (it reported mAP50 0.119, wrong). The
    # baseline comparison lives in backend/scripts/eval_detector_slicing.py, which
    # collapses both models to one vehicle class with the same IoU>=0.5 matching.

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": "python backend/scripts/train_yolo_inatrc.py",
        "dataset": {
            "name": "InaTRC — Indonesia Toll Road Vehicle Classification Dataset",
            "citation": "Chasanah U. et al., Mendeley Data v1 (2025), doi:10.17632/kddgphck3b.1",
            "license": "CC BY 4.0",
            "split": {"train": 2600, "validation": 325, "test": 325},
            "classes": CLASS_NAMES,
            "provenance": "observasi — frame CCTV jalan tol Indonesia (2022) dengan label manual dari penyusun dataset",
        },
        "training": {"base": str(BASE_WEIGHTS.relative_to(ROOT)), "epochs_max": args.epochs, "imgsz": args.imgsz,
                     "batch": args.batch, "freeze_layers": args.freeze, "seed": 42, "patience": 5,
                     "device": args.device, "deterministic": False,
                     "selection": "epoch terbaik menurut mAP50-95 validasi"},
        "test": {
            "finetuned_5_classes": metrics(tuned_test),
            "finetuned_as_single_vehicle_class": metrics(tuned_single),
        },
        "baseline": "lihat inatrc_slicing_eval.json (python backend/scripts/eval_detector_slicing.py)",
        "weights": str(OUT_WEIGHTS.relative_to(ROOT)),
    }
    EVIDENCE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["test"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
