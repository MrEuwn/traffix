"""Vehicle detection used by the evaluation, the frame catalogue and live inference.

Two modes:
- `full`: one pass over the whole frame.
- `sliced`: SAHI-style — the whole frame plus a 3x3 grid of overlapping tiles (25%), each
  tile upscaled to `imgsz`, merged with class-agnostic NMS. Small, distant vehicles become
  several times larger in a tile, which is where single-pass detectors miss them.

COCO checkpoints are restricted to vehicle classes; other checkpoints keep all classes.
"""

from __future__ import annotations

import numpy as np

VEHICLE_NAMES = ("car", "motorcycle", "bus", "truck")
SLICE_GRID = 3
SLICE_OVERLAP = 0.25
NMS_IOU = 0.5


def vehicle_class_ids(names: dict[int, str]) -> list[int] | None:
    ids = [i for i, n in names.items() if n in VEHICLE_NAMES]
    return ids if len(names) > 1 and ids else None


def _tiles(w: int, h: int) -> list[tuple[int, int, int, int]]:
    n, ov = SLICE_GRID, SLICE_OVERLAP
    sw, sh = int(w / (n - (n - 1) * ov)), int(h / (n - (n - 1) * ov))
    xs = np.linspace(0, w - sw, n).astype(int)
    ys = np.linspace(0, h - sh, n).astype(int)
    return [(int(x), int(y), int(x) + sw, int(y) + sh) for x in xs for y in ys]


def detect(model, img: np.ndarray, *, mode: str = "full", imgsz: int = 640, conf: float = 0.25) -> list[dict]:
    """Run the detector on a BGR image; returns [{xyxy, confidence, class}] in image pixels."""
    import torch
    from torchvision.ops import nms

    h, w = img.shape[:2]
    classes = vehicle_class_ids(model.names)
    regions = [(0, 0, w, h)] + (_tiles(w, h) if mode == "sliced" else [])
    boxes, scores, labels = [], [], []
    for x0, y0, x1, y1 in regions:
        r = model.predict(img[y0:y1, x0:x1], imgsz=imgsz, conf=conf, classes=classes,
                          verbose=False, device="cpu")[0]
        b = r.boxes.xyxy.clone()
        b[:, [0, 2]] += x0
        b[:, [1, 3]] += y0
        boxes.append(b)
        scores.append(r.boxes.conf)
        labels.append(r.boxes.cls)
    b, s, c = torch.cat(boxes), torch.cat(scores), torch.cat(labels)
    if len(regions) > 1 and len(b):
        keep = nms(b, s, NMS_IOU)  # a vehicle seen in two tiles is one vehicle
        b, s, c = b[keep], s[keep], c[keep]
    return [
        {"xyxy": [round(float(v), 1) for v in box], "confidence": round(float(sc), 4), "class": model.names[int(k)]}
        for box, sc, k in zip(b.tolist(), s.tolist(), c.tolist())
    ]
