#!/usr/bin/env python3
"""Traffix D2 evidence pipeline — one command, real computations only.

    python backend/scripts/run_d2_evaluation.py [--regenerate-v4] [--skip-yolo]

Steps (non-zero exit on any failed check):
  1. preflight: required files and libraries
  2. data audit + cleaning report for every dataset the product uses
  3. feature lineage + leakage invariants (raw hybrid -> features == traffix_lstm_ready.csv)
  4. reproduction of the shipped notebook LSTM metrics
  5. D2 protocol experiment: day split, baselines, Ridge/HGB, LSTM, test scored once
  6. transfer check of the selected LSTM on the v4 replay the app actually runs
  7. bottleneck classifier reproduction from its shipped artefact
  8. YOLO: notebook-recorded validation metrics + frame inference (run_yolo_frames.py)
  9. plots, JSON/CSV artefacts for the API, Markdown reports and the metrics brief

The v4 synthetic data is regenerated only with --regenerate-v4 (deterministic, seed 42).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EVIDENCE = ROOT / "docs" / "evidence" / "d2"
FIGURES = EVIDENCE / "figures"
FORECAST_ARTIFACTS = BACKEND / "ml" / "forecast" / "artifacts"
BOTTLENECK_ARTIFACTS = BACKEND / "ml" / "bottleneck" / "artifacts"
DETECTION_ARTIFACTS = BACKEND / "ml" / "detection" / "artifacts"
YOLO_NOTEBOOK = ROOT / "yolo pipeline" / "code" / "traffix_yolo_pipeline_revised.ipynb"
COMMAND = "python backend/scripts/run_d2_evaluation.py"


class PipelineError(RuntimeError):
    """A check failed; the pipeline stops with a non-zero exit."""


def log(msg: str) -> None:
    print(msg, flush=True)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_dirty() -> bool | None:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                                      stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return rel(value)
    raise TypeError(f"not serialisable: {type(value)}")


# ------------------------------------------------------------------ 1. preflight

def preflight(skip_yolo: bool) -> dict:
    from ml.forecast import evaluate as fe

    required = {
        "hybrid_raw": fe.HYBRID_RAW,
        "lstm_ready": fe.LSTM_READY,
        "feature_columns": ROOT / "data" / "data_process" / "feature_columns.json",
        "v4_ticks": ROOT / "data" / "data_synthetic" / "v4" / "ticks_v4.csv.gz",
        "v4_replay": fe.V4_REPLAY,
        "legacy_lstm_metrics": fe.LEGACY_ARTIFACTS / "metrics.json",
        "legacy_lstm_15m": fe.LEGACY_ARTIFACTS / "best_lstm_15m.keras",
        "legacy_lstm_2h": fe.LEGACY_ARTIFACTS / "best_lstm_2h.keras",
        "legacy_lstm_4h": fe.LEGACY_ARTIFACTS / "best_lstm_4h.keras",
        "legacy_feat_scaler": fe.LEGACY_ARTIFACTS / "feat_scaler.joblib",
        "legacy_target_scalers": fe.LEGACY_ARTIFACTS / "target_scalers.joblib",
        "bottleneck_model": BOTTLENECK_ARTIFACTS / "bottleneck_classifier.joblib",
        "bottleneck_metrics": BOTTLENECK_ARTIFACTS / "metrics.json",
        "yolo_notebook": YOLO_NOTEBOOK,
        "yolo_weights": ROOT / "yolo pipeline" / "model" / "best.pt",
    }
    missing = [f"{k}: {rel(p) if p.is_relative_to(ROOT) else p}" for k, p in required.items() if not p.exists()]
    libs = {}
    for name in ("tensorflow", "sklearn", "matplotlib", "joblib") + (() if skip_yolo else ("ultralytics", "cv2")):
        try:
            module = __import__(name)
            libs[name] = getattr(module, "__version__", "ok")
        except ImportError:
            libs[name] = None
    missing_libs = [k for k, v in libs.items() if v is None]
    if missing or missing_libs:
        raise PipelineError(f"preflight gagal — berkas hilang: {missing}; pustaka hilang: {missing_libs}")
    log(f"[1/9] preflight OK — {len(required)} berkas, pustaka {libs}")
    return {"files": {k: rel(p) for k, p in required.items()}, "libraries": libs}


# ------------------------------------------------------------------ 2. data audit

def audit_frame(name: str, path: Path, frame: pd.DataFrame, *, provenance: str, key: list[str],
                time_col: str | None, entity_col: str | None, target_lineage: str,
                supports_claim: str, ranges: dict[str, tuple[float | None, float | None]]) -> dict:
    from ml.forecast.evaluate import sha256

    report = {
        "dataset": name,
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "provenance": provenance,
        "dtypes": {c: str(t) for c, t in frame.dtypes.items()},
        "missing_values": {c: int(v) for c, v in frame.isna().sum().items() if v},
        "duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_keys": int(frame.duplicated(subset=key).sum()) if key else None,
        "key": key,
        "target_lineage": target_lineage,
        "supports_claim": supports_claim,
    }
    numeric = frame.select_dtypes(include=[np.number])
    report["non_finite_values"] = int((~np.isfinite(numeric.to_numpy(dtype=float))).sum() - numeric.isna().sum().sum())
    violations = {}
    for col, (lo, hi) in ranges.items():
        if col not in frame:
            continue
        bad = 0
        if lo is not None:
            bad += int((frame[col] < lo).sum())
        if hi is not None:
            bad += int((frame[col] > hi).sum())
        violations[col] = {"min": float(frame[col].min()), "max": float(frame[col].max()),
                           "rule": [lo, hi], "violations": bad}
    report["range_checks"] = violations
    if time_col:
        ts = pd.to_datetime(frame[time_col])
        report["time_range"] = [str(ts.min()), str(ts.max())]
        report["timezone"] = str(ts.dt.tz) if ts.dt.tz is not None else "naive"
        if entity_col:
            monotonic = all(g.is_monotonic_increasing for _, g in ts.groupby(frame[entity_col]))
        else:
            monotonic = bool(ts.is_monotonic_increasing)
        report["chronological_within_entity"] = bool(monotonic)
    if entity_col:
        report["entities"] = {"column": entity_col, "unique": int(frame[entity_col].nunique()),
                              "counts": {str(k): int(v) for k, v in frame[entity_col].value_counts().items()}}
    return report


def data_audit() -> dict:
    from ml.forecast import evaluate as fe

    log("[2/9] audit data")
    reports = []
    ranges_traffic = {"volume_veh_per_hour": (0, None), "vehicle_count_1min": (0, None),
                      "avg_speed_kmh": (0, 130), "density_percent": (0, 100), "queue_length_veh": (0, None),
                      "green_seconds": (0, 180)}

    hybrid = pd.read_csv(fe.HYBRID_RAW)
    reports.append(audit_frame(
        "hybrid_traffic_7d (mentah, per approach)", fe.HYBRID_RAW, hybrid,
        provenance="sintetis — simulator hybrid v3 (generate_data_hybrid.py, seed 42) yang dikalibrasi "
                   "dengan distribusi hitungan YOLO; bukan pengukuran lapangan",
        key=["intersectionId", "tick", "approach"], time_col="timestamp_wib", entity_col="approach",
        target_lineage="target_volume_* di file mentah dihitung generator per approach; pipeline D2 menghitung "
                       "ulang target dari volume agregat (shift -15/-120/-240 menit)",
        supports_claim="Mendukung klaim kinerja peramalan PADA SIMULATOR ini saja.",
        ranges=ranges_traffic))

    ready = pd.read_csv(fe.LSTM_READY)
    reports.append(audit_frame(
        "traffix_lstm_ready (fitur siap model, notebook Data team)", fe.LSTM_READY, ready,
        provenance="turunan dari hybrid_traffic_7d + 1.500 menit 'low traffic' acak (np.random seed 42) "
                   "yang ditambahkan di notebook sebagai seri JKT-TMG-SIM-01",
        key=["intersectionId", "tick"], time_col="timestamp_wib", entity_col="intersectionId",
        target_lineage="target_volume_{15m,2h,4h} = volume_veh_per_hour digeser -15/-120/-240 baris per "
                       "intersection (diverifikasi selisih 0)",
        supports_claim="Dipakai untuk mereproduksi angka notebook; tidak dipakai di protokol D2 karena split "
                       "barisnya tidak kronologis.",
        ranges=ranges_traffic))

    replay = pd.read_csv(fe.V4_REPLAY)
    reports.append(audit_frame(
        "live_replay_7d v4 (input replay aplikasi)", fe.V4_REPLAY, replay,
        provenance="sintetis — simulator v4 (generate_data_v4.py, seed 42), 6 simpang, agregat semua lengan",
        key=["intersectionId", "tick"], time_col="timestamp_wib", entity_col="intersectionId",
        target_lineage="target_volume_* di file ini = RATA-RATA volume per ruas, sedangkan volume_veh_per_hour = "
                       "JUMLAH; skala berbeda, sehingga kolom target ini tidak dipakai sebagai label",
        supports_claim="Input demo dan uji transfer antarsimulator; bukan bukti kinerja dunia nyata.",
        ranges=ranges_traffic))

    ticks_path = ROOT / "data" / "data_synthetic" / "v4" / "ticks_v4.csv.gz"
    ticks = pd.read_csv(ticks_path)
    reports.append(audit_frame(
        "ticks_v4 (per ruas per menit, label penyebab)", ticks_path, ticks,
        provenance="sintetis — simulator v4 seed 42; label bottleneck_cause dari aturan prioritas simulator",
        key=["section_id", "tick"], time_col="timestamp_wib" if "timestamp_wib" in ticks else None,
        entity_col="section_id",
        target_lineage="bottleneck_cause ditetapkan aturan simulator (docs/SCHEMA-v4.md §1), bukan anotasi manusia",
        supports_claim="Mendukung klaim 'model memulihkan mekanisme simulator', bukan diagnosis penyebab nyata.",
        ranges={"kecepatan_kmh": (0, 130)} if "kecepatan_kmh" in ticks else {}))
    reports[-1]["label_distribution"] = {k: int(v) for k, v in ticks["bottleneck_cause"].value_counts().items()}

    yolo_counts = ROOT / "inference" / "inference_yolo" / "vehicle_count.csv"
    counts = pd.read_csv(yolo_counts)
    reports.append(audit_frame(
        "vehicle_count (keluaran inferensi YOLO notebook)", yolo_counts, counts,
        provenance="turunan — keluaran YOLO notebook atas video CCTV publik Bina Marga; kecepatan, densitas, "
                   "antrean adalah estimasi berbasis aturan",
        key=["source_video"], time_col=None, entity_col="camera_id",
        target_lineage="tidak ada label acuan; angka adalah keluaran model",
        supports_claim="Bukti alur inferensi, bukan bukti akurasi hitung.",
        ranges={"vehicle_count": (0, None), "avg_speed_kmh": (0, 130), "density_percent": (0, 100)}))

    meta_path = ROOT / "inference_data" / "data_video" / "metadata" / "video_weather_data.csv"
    meta = pd.read_csv(meta_path, encoding="utf-8-sig")
    reports.append(audit_frame(
        "video_weather_data (metadata CCTV)", meta_path, meta,
        provenance="observasi publik — overlay CCTV Bina Marga dibaca manual; koordinat manual (Google Maps); "
                   "cuaca Open-Meteo per jam",
        key=["video_file"], time_col=None, entity_col="period",
        target_lineage="tidak ada target",
        supports_claim="Konteks lokasi/cuaca untuk frame demo.",
        ranges={}))

    cleaning = {
        "rules": [
            "Agregasi approach -> simpang per menit: volume/jumlah kendaraan/antrean/waktu tunggu dijumlah, "
            "kecepatan/hijau/kepadatan/suhu dirata-rata, cuaca = modus, flag kejadian = maksimum "
            "(data/data_process/aggregation_rules.md).",
            "Seri harus kontinu 1 menit per simpang; celah atau duplikat menggagalkan pipeline (assert_contiguous).",
            "Baris dengan riwayat < 60 menit (lag_60/roll_60 kosong) dan baris yang targetnya melewati akhir "
            "seri dibuang, bukan diimputasi.",
            "Tidak ada outlier yang dibuang; nilai di luar rentang fisik dicatat di range_checks.",
            "Seri augmentasi JKT-TMG-SIM-01 (8 Mei) tidak dipakai di protokol D2 karena dibuat acak di notebook "
            "dan tanggalnya sesudah periode uji.",
        ],
    }
    for r in reports:
        if r.get("duplicate_keys"):
            log(f"  [WARN] {r['dataset']}: {r['duplicate_keys']} kunci duplikat")
        bad = {k: v["violations"] for k, v in r.get("range_checks", {}).items() if v["violations"]}
        if bad:
            log(f"  [WARN] {r['dataset']}: pelanggaran rentang {bad}")
        log(f"  {r['dataset']}: {r['rows']:,} baris, provenans: {r['provenance'][:60]}…")
    return {"datasets": reports, "cleaning": cleaning}


# ------------------------------------------------------------------ 3. lineage + leakage

def split_summary(frame: pd.DataFrame) -> dict:
    """Per-horizon split sizes and boundaries; raises if any split leaks into the next."""
    from ml.forecast import evaluate as fe

    splits: dict = {}
    for horizon, minutes in fe.HORIZON_MINUTES.items():
        masks = fe.split_masks(frame, horizon)
        if (masks["train"] & masks["validation"]).any() or (masks["validation"] & masks["test"]).any():
            raise PipelineError("split tumpang tindih")
        for name, m in masks.items():
            issue = frame.loc[m, "timestamp_wib"]
            target_t = issue + pd.Timedelta(minutes=minutes)
            splits.setdefault(horizon, {})[name] = {
                "n": int(m.sum()),
                "issue_from": str(issue.min()), "issue_to": str(issue.max()),
                "target_from": str(target_t.min()), "target_to": str(target_t.max()),
            }
        if splits[horizon]["train"]["target_to"] >= splits[horizon]["validation"]["issue_from"]:
            raise PipelineError(f"{horizon}: target latih masuk periode validasi")
        if splits[horizon]["validation"]["target_to"] >= splits[horizon]["test"]["issue_from"]:
            raise PipelineError(f"{horizon}: target validasi masuk periode uji")
    return splits


def lineage_and_leakage(frames: dict[str, pd.DataFrame]) -> dict:
    from ml.forecast import evaluate as fe
    from ml.forecast.features import FEATURE_COLUMNS, TARGET_COLUMNS, assert_no_leakage

    log("[3/9] lineage fitur + invarian kebocoran")
    frame = frames["hybrid_tmg"]
    assert_no_leakage(FEATURE_COLUMNS)
    ready = pd.read_csv(fe.LSTM_READY)
    ready = ready[ready["intersectionId"] == fe.SERIES_ID].copy()
    ready["timestamp_wib"] = pd.to_datetime(ready["timestamp_wib"])
    ours = frame.set_index("timestamp_wib").loc[ready["timestamp_wib"]]
    cols = FEATURE_COLUMNS + list(TARGET_COLUMNS.values())
    max_abs = float((ours[cols].to_numpy(dtype=float) - ready[cols].to_numpy(dtype=float)).__abs__().max())
    if max_abs > 1e-6:
        raise PipelineError(f"fitur hasil hitung ulang tidak cocok dengan traffix_lstm_ready.csv (maks {max_abs})")

    # Past-only invariant: perturbing the future must not change any feature at t.
    from ml.forecast.features import engineer_features

    cut = len(frame) // 2
    raw_cols = ["volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh"]
    raw = pd.read_csv(fe.HYBRID_RAW)
    series = fe.aggregate_approaches(raw)
    series["intersectionId"] = fe.SERIES_ID
    base = engineer_features(series, with_targets=False)
    poisoned = series.copy()
    poisoned.loc[poisoned.index[cut + 1:], raw_cols] *= 7.0
    after = engineer_features(poisoned, with_targets=False)
    past_changed = float(np.nanmax(np.abs(base[FEATURE_COLUMNS].iloc[: cut + 1].to_numpy(dtype=float)
                                          - after[FEATURE_COLUMNS].iloc[: cut + 1].to_numpy(dtype=float))))
    if past_changed > 0:
        raise PipelineError("fitur pada waktu t berubah ketika data sesudah t diubah — kebocoran masa depan")

    splits = {key: split_summary(f) for key, f in frames.items()}
    log(f"  fitur == notebook (maks selisih {max_abs:.2e}); uji gangguan-masa-depan: 0 perubahan; split tanpa irisan")
    return {
        "feature_recompute_max_abs_diff": max_abs,
        "rows_compared": int(len(ready)),
        "future_perturbation_max_change": past_changed,
        "forbidden_input_columns": "target_* dan future_* (features.assert_no_leakage)",
        "splits": splits,
        "checks": [
            "41 fitur dihitung ulang dari data mentah hybrid identik dengan traffix_lstm_ready.csv (TMG-1012); "
            "fungsi yang sama dipakai untuk replay v4 dan untuk inferensi runtime.",
            "Mengubah data sesudah menit t tidak mengubah satu pun fitur pada menit <= t.",
            "Target tiap sampel berada di hari split yang sama dengan waktu terbit (purging di batas hari).",
            "Scaler fitur dan target di-fit hanya pada baris latih.",
            "Pemilihan model/konfigurasi hanya memakai MAE validasi; hari uji dinilai sekali.",
        ],
    }


# ------------------------------------------------------------------ 5/6. forecasting

TRAINED_ON = {
    "v4_replay": "replay v4, 6 simpang, hari 1-5 (live_replay_7d.csv.gz)",
    "hybrid_tmg": "TMG-1012 hari 1-5 (hybrid_traffic_7d.csv)",
}


def forecasting(frame: pd.DataFrame, key: str) -> dict:
    """Train/select/score one experiment and save its models.

    The served experiment writes to backend/ml/forecast/artifacts/models (what the
    API loads); the other one to models_<key>/ for the record.
    """
    import joblib

    from ml.forecast import evaluate as fe
    from ml.forecast.features import FEATURE_COLUMNS, HORIZON_MINUTES

    experiment = fe.EXPERIMENTS[key]
    model_dir = fe.MODEL_DIR if experiment.served else fe.ARTIFACT_DIR / f"models_{key}"
    model_dir.mkdir(parents=True, exist_ok=True)
    feat_scaler = fe.fit_feature_scaler(frame)
    results, models, tscalers, seq_lens = {}, {}, {}, {}
    for horizon in HORIZON_MINUTES:
        result, model, tscaler = fe.run_horizon(frame, horizon, feat_scaler, experiment, log=log)
        results[horizon], models[horizon], tscalers[horizon] = result, model, tscaler
        seq_lens[horizon] = int(result.selection["lstm"]["seq_len"])
        model.save(model_dir / f"lstm_{horizon}.keras")
    # Two files, the layout ml/model_loader.py reads (feature scaler + per-horizon target scalers).
    joblib.dump(feat_scaler, model_dir / "feat_scaler.joblib")
    joblib.dump(tscalers, model_dir / "target_scalers.joblib")
    runtime_config = {
        "experiment": key,
        "feature_columns": FEATURE_COLUMNS,
        "seq_len": seq_lens,
        "horizons_minutes": HORIZON_MINUTES,
        "window": "baris t-seq_len+1 .. t (inklusif), target = volume pada t+h",
        "target_unit": "kend/jam (laju arus 1 menit, total semua lengan simpang)",
        "trained_on": TRAINED_ON[key],
        "models": {h: {"file": f"lstm_{h}.keras", "sha256": fe.sha256(model_dir / f"lstm_{h}.keras")}
                   for h in HORIZON_MINUTES},
        "scalers_sha256": {name: fe.sha256(model_dir / name)
                           for name in ("feat_scaler.joblib", "target_scalers.joblib")},
    }
    write_json(model_dir / "config.json", runtime_config)
    return {"results": results, "runtime_config": runtime_config, "models": models,
            "target_scalers": tscalers, "feat_scaler": feat_scaler, "seq_lens": seq_lens}


def summarise_experiment(frame: pd.DataFrame, fc: dict, key: str) -> dict:
    """Per-horizon comparison, bootstrap CI, error analysis; writes per-sample CSVs."""
    from ml.forecast import evaluate as fe

    experiment = fe.EXPERIMENTS[key]
    suffix = "" if experiment.served else f"_{key}"
    horizons = {}
    rows_csv = []
    for horizon, res in fc["results"].items():
        test = res.test_metrics
        val = res.val_metrics
        # Strongest naive baseline is chosen on VALIDATION MAE, never on test.
        strongest = min(fe.BASELINES, key=lambda b: val[b]["mae"])
        lstm_abs = np.abs(res.predictions["lstm"] - res.y_test)
        base_abs = np.abs(res.predictions[strongest] - res.y_test)
        ci = fe.block_bootstrap_mae_diff(lstm_abs, base_abs)
        comparison = []
        for name in ["lstm", *fe.BASELINES, *fe.COMPARATORS]:
            m = test[name]
            entry = {
                "model": name,
                "label": fe.MODEL_LABELS[name],
                "role": "model" if name == "lstm" else ("baseline" if name in fe.BASELINES else "pembanding"),
                "test": m,
                "validation": {k: val[name][k] for k in ("mae", "rmse", "wape_pct")},
                "lstm_mae_improvement_pct": None if name == "lstm" else fe.improvement_pct(m["mae"], test["lstm"]["mae"]),
                "lstm_wape_improvement_pct": None if name == "lstm" else fe.improvement_pct(m["wape_pct"], test["lstm"]["wape_pct"]),
                "lstm_mae_abs_diff": None if name == "lstm" else test["lstm"]["mae"] - m["mae"],
            }
            comparison.append(entry)
            rows_csv.append({"horizon": horizon, "model": name, "role": entry["role"],
                             **{f"test_{k}": v for k, v in m.items()},
                             **{f"val_{k}": v for k, v in entry["validation"].items()},
                             "lstm_mae_improvement_pct": entry["lstm_mae_improvement_pct"]})
        best_test = min(comparison, key=lambda e: e["test"]["mae"])
        ts = frame["timestamp_wib"].iloc[res.test_rows]
        target_ts = ts + pd.Timedelta(minutes=fe.HORIZON_MINUTES[horizon])
        pred_frame = pd.DataFrame({
            "intersection_id": frame["intersectionId"].iloc[res.test_rows].to_numpy(),
            "issue_time_wib": ts.dt.strftime("%Y-%m-%d %H:%M"),
            "target_time_wib": target_ts.dt.strftime("%Y-%m-%d %H:%M"),
            "actual": np.round(res.y_test, 2),
            **{name: np.round(p, 2) for name, p in res.predictions.items()},
        })
        pred_path = fe.ARTIFACT_DIR / f"predictions_test{suffix}_{horizon}.csv"
        pred_frame.to_csv(pred_path, index=False)

        hour = target_ts.dt.hour.to_numpy()
        by_hour = []
        for h in range(24):
            sel = hour == h
            if sel.any():
                by_hour.append({"hour": h, "n": int(sel.sum()),
                                "lstm_mae": float(lstm_abs[sel].mean()),
                                "baseline_mae": float(base_abs[sel].mean())})
        incident = (frame[["accident_count", "roadwork_flag", "event_flag"]].iloc[res.test_rows].sum(axis=1) > 0).to_numpy() \
            if {"accident_count", "roadwork_flag", "event_flag"} <= set(frame.columns) else None
        worst_idx = np.argsort(-lstm_abs)[:5]
        horizons[horizon] = {
            "horizon_minutes": fe.HORIZON_MINUTES[horizon],
            "n": res.n,
            "comparison": comparison,
            "strongest_baseline": {"model": strongest, "chosen_by": "MAE validasi terendah di antara baseline naif"},
            "lstm_vs_strongest_baseline": {
                "mae_improvement_pct": fe.improvement_pct(test[strongest]["mae"], test["lstm"]["mae"]),
                "wape_improvement_pct": fe.improvement_pct(test[strongest]["wape_pct"], test["lstm"]["wape_pct"]),
                "bootstrap": ci,
                "significant": bool(ci["ci95_high"] < 0 or ci["ci95_low"] > 0),
            },
            "best_on_test": {"model": best_test["model"], "mae": best_test["test"]["mae"]},
            "selection": res.selection,
            "error_by_target_hour": by_hour,
            "worst_cases": [
                {"intersection_id": pred_frame["intersection_id"].iloc[i],
                 "issue_time_wib": pred_frame["issue_time_wib"].iloc[i],
                 "target_time_wib": pred_frame["target_time_wib"].iloc[i],
                 "actual": float(res.y_test[i]), "lstm": float(res.predictions["lstm"][i]),
                 "abs_error": float(lstm_abs[i])}
                for i in worst_idx
            ],
            "incident_at_issue_mae": None if incident is None or not incident.any() else {
                "with_incident": {"n": int(incident.sum()), "lstm_mae": float(lstm_abs[incident].mean())},
                "without_incident": {"n": int((~incident).sum()), "lstm_mae": float(lstm_abs[~incident].mean())},
            },
            "lstm_training_history": res.lstm_history,
            "predictions_csv": rel(pred_path),
        }
    pd.DataFrame(rows_csv).to_csv(fe.ARTIFACT_DIR / f"baseline_comparison{suffix}.csv", index=False)
    return horizons


def summarise_forecast(frames: dict, fcs: dict, transfer: dict, legacy: dict, lineage: dict,
                       audit: dict, meta: dict) -> dict:
    from ml.forecast import evaluate as fe

    primary, secondary = "v4_replay", "hybrid_tmg"
    frame, fc = frames[primary], fcs[primary]
    horizons = summarise_experiment(frame, fc, primary)
    secondary_horizons = summarise_experiment(frames[secondary], fcs[secondary], secondary)
    replay_audit = next(d for d in audit["datasets"] if d["dataset"].startswith("live_replay"))
    hybrid_audit = next(d for d in audit["datasets"] if d["dataset"].startswith("hybrid"))
    test_split = lineage["splits"][primary]["15m"]["test"]
    return {
        "available": True,
        "task": "Peramalan volume lalu lintas multi-horizon per simpang",
        "question": ("Seberapa akurat LSTM meramalkan volume lalu lintas simpang (kend/jam) 15 menit, 2 jam, dan "
                     "4 jam ke depan dari 41 fitur yang tersedia pada waktu terbit, dibanding baseline naif dan "
                     "model tabular pada hari uji yang sama, untuk 6 simpang yang dipantau aplikasi?"),
        "target": {
            "definition": "volume_veh_per_hour pada menit t+h: laju arus 1 menit (jumlah kendaraan x 60) "
                          "dijumlah semua lengan simpang",
            "unit": "kend/jam",
            "horizons": {h: m for h, m in fe.HORIZON_MINUTES.items()},
        },
        "model": {
            "name": "LSTM (lstm_light: LSTM64 -> LSTM32 -> Dense64 -> Dense1)",
            "version": "d2-" + meta["generated_at"][:10],
            "selected_config": {h: {k: v for k, v in fc["results"][h].selection["lstm"].items() if k != "grid"}
                                for h in fc["results"]},
            "artifacts": {h: v for h, v in fc["runtime_config"]["models"].items()},
            "scalers_sha256": fc["runtime_config"]["scalers_sha256"],
        },
        "dataset": {
            "name": "live_replay_7d.csv.gz (replay v4) — 6 simpang × 7 hari, per menit",
            "provenance": "sintetis",
            "provenance_detail": replay_audit["provenance"],
            "sha256": replay_audit["sha256"],
            "rows": int(len(frame)),
            "intersections": int(frame["intersectionId"].nunique()),
            "why_this_dataset": "Data yang sama yang di-replay aplikasi, sehingga model yang melayani dievaluasi "
                                "pada distribusi yang ia layani. Uji transfer di bawah menunjukkan model yang dilatih "
                                "di simulator lain (hybrid) gagal mengalahkan persistence 15 menit di sini.",
        },
        "split": {
            "protocol": "kronologis per hari kalender; target harus di hari yang sama dengan waktu terbit; "
                        "jendela riwayat boleh dari hari sebelumnya",
            "train": "hari 1-5 (1-5 Mei 2026)",
            "validation": "hari 6 (6 Mei 2026)",
            "test": "hari 7 (7 Mei 2026)",
            "per_horizon": lineage["splits"][primary],
            "test_period": [test_split["issue_from"], test_split["issue_to"]],
        },
        "metric_definitions": {
            "mae": "rata-rata |prediksi - aktual|, kend/jam",
            "rmse": "akar rata-rata kuadrat galat, kend/jam",
            "wape_pct": "sum|galat| / sum|aktual| x 100 — tetap terdefinisi saat aktual = 0",
            "smape_pct": "rata-rata 2|galat| / (|aktual| + |prediksi|) x 100",
            "mape_pct": "rata-rata |galat| / |aktual| x 100 hanya untuk aktual != 0 (jumlah yang dilewati dilaporkan)",
            "improvement_pct": "(galat baseline - galat model) / galat baseline x 100; positif = model lebih baik",
            "bootstrap": "CI 95% moving-block bootstrap (blok 60 menit, 2000 ulangan, seed 42) untuk selisih MAE",
        },
        "horizons": horizons,
        "secondary_experiment": {
            "key": secondary,
            "title": fe.EXPERIMENTS[secondary].title,
            "dataset": "hybrid_traffic_7d.csv -> seri TMG-1012 (agregasi lengan, 7 hari)",
            "dataset_sha256": hybrid_audit["sha256"],
            "split": lineage["splits"][secondary],
            "models_dir": rel(fe.ARTIFACT_DIR / f"models_{secondary}"),
            "horizons": secondary_horizons,
        },
        "transfer_v4": transfer,
        "legacy_reproduction": legacy,
        "leakage_guard": lineage["checks"],
        "data_quality": {
            "cleaning_rules": audit["cleaning"]["rules"],
            "report": "docs/evidence/d2/DATA_QUALITY_REPORT.md",
        },
        "limitations": [
            "Seluruh data latih dan uji sintetis (simulator v4 seed 42, 6 simpang, 7 hari). Angka ini adalah "
            "kinerja pada benchmark sintetis, bukan akurasi pada lalu lintas Jakarta nyata.",
            "Simulator yang sama menghasilkan data latih dan uji; model bisa mempelajari aturan simulator. Uji "
            "transfer hybrid -> v4 menunjukkan model yang dilatih pada simulator lain jatuh di bawah persistence "
            "untuk 15 menit — risiko serupa berlaku saat pindah ke data lapangan.",
            "Target adalah volume titik 1 menit (jumlah kendaraan per menit x 60) yang berderau; model meramal "
            "pola, bukan derau per menit.",
            "Hanya satu hari uji (hari kerja). Pola akhir pekan/libur tidak diuji terpisah.",
            "Replay demo juga memutar hari 1-6; prediksi pada hari itu adalah in-sample dan diberi label di UI.",
            "Fitur flag kejadian (kecelakaan, perbaikan jalan, event) diasumsikan diketahui saat waktu terbit; "
            "di lapangan informasi ini bisa terlambat.",
        ],
        "not_claims": [
            "Tidak mengklaim pengurangan kemacetan, waktu tempuh, emisi, atau kecelakaan.",
            "Tidak mengklaim validasi lapangan atau pengendalian lampu lalu lintas otomatis.",
        ],
        "reproduce": COMMAND,
        "generated_at": meta["generated_at"],
        "git_commit": meta["git_commit"],
        "git_dirty": meta["git_dirty"],
        "seed": fe.SEED,
    }


# ------------------------------------------------------------------ 7. bottleneck

def bottleneck_reproduction() -> dict:
    import joblib

    from ml.bottleneck.features import (
        FEATURE_COLUMNS as B_FEATURES,
        assert_no_leakage as b_assert,
        build_feature_frame,
        evaluate_predictions,
        rule_based_cause,
    )

    log("[7/9] reproduksi klasifikasi penyebab bottleneck dari artefak")
    ticks = pd.read_csv(ROOT / "data" / "data_synthetic" / "v4" / "ticks_v4.csv.gz")
    ticks = ticks.sort_values(["section_id", "tick"]).reset_index(drop=True)
    features = build_feature_frame(ticks)
    b_assert(list(features.columns))
    bundle = joblib.load(BOTTLENECK_ARTIFACTS / "bottleneck_classifier.joblib")
    if list(bundle["feature_columns"]) != list(B_FEATURES):
        raise PipelineError("manifest fitur artefak bottleneck != features.FEATURE_COLUMNS")
    day = ticks["tick"] // 1440 + 1
    y = ticks["bottleneck_cause"].to_numpy()
    out = {"model_name": bundle.get("model_name"), "splits": {}}
    for name, mask in (("validation", day == 6), ("test", day == 7)):
        pred = bundle["model"].predict(features[mask.to_numpy()])
        out["splits"][name] = evaluate_predictions(y[mask.to_numpy()], pred)
    test_mask = (day == 7).to_numpy()
    majority = pd.Series(y[(day <= 5).to_numpy()]).mode().iloc[0]
    out["baselines_test"] = {
        "majority_class": evaluate_predictions(y[test_mask], np.full(test_mask.sum(), majority, dtype=object)),
        "rule_based": evaluate_predictions(y[test_mask], rule_based_cause(features[test_mask])),
    }
    stored = json.loads((BOTTLENECK_ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))
    rec = out["splits"]["test"]
    out["matches_stored_metrics"] = all(
        abs(rec[k] - stored["metrics"][k]) < 1e-4 for k in ("macro_f1", "balanced_accuracy", "accuracy"))
    out["stored_metrics"] = stored["metrics"]
    out["class_share_test"] = {p["cause"]: p["support"] for p in rec["per_class"]}
    log(f"  test macro-F1 {rec['macro_f1']} (tersimpan {stored['metrics']['macro_f1']}); "
        f"cocok={out['matches_stored_metrics']}")
    if not out["matches_stored_metrics"]:
        raise PipelineError("metrik bottleneck hasil hitung ulang tidak cocok dengan metrics.json")
    return out


# ------------------------------------------------------------------ 8. YOLO

def yolo_evidence(skip_yolo: bool) -> dict:
    log("[8/9] bukti YOLO")
    nb = json.loads(YOLO_NOTEBOOK.read_text(encoding="utf-8"))
    text = ""
    for cell in nb["cells"]:
        for o in cell.get("outputs", []):
            text += "".join(o.get("text", "")) + "".join(o.get("data", {}).get("text/plain", ""))
    def grab(label: str) -> float | None:
        m = re.findall(rf"{label}\s*:\s*([0-9.]+)", text)
        return float(m[-1]) if m else None
    counts = re.findall(r"(Train|Val) images\s*:\s*(\d+)", text)
    instances = re.findall(r"all\s+(\d+)\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", text)
    recorded = {
        "split": "validation",
        "source": rel(YOLO_NOTEBOOK) + " (output sel tersimpan, Colab Tesla T4)",
        "reproduced_in_this_run": False,
        "why_not_reproduced": "Dataset Kaggle (boukraailyesali/traffic-road-object-detection-dataset-using-yolo, "
                              "380 MB) tidak ada di repo; evaluasi ulang butuh unduhan dan kredensial Kaggle.",
        "dataset": "Kaggle traffic-road-object-detection-dataset-using-yolo — 1 kelas 'car'",
        "images": {k.lower(): int(v) for k, v in counts},
        "val_instances": int(instances[-1][1]) if instances else None,
        "ultralytics": {"precision": float(instances[-1][2]) if instances else None,
                        "recall": float(instances[-1][3]) if instances else None,
                        "map50": grab("mAP50"), "map50_95": grab("mAP50-95")},
        "iou50_matching_conf025": {k: grab(k) for k in ("TP", "FP", "FN", "Precision", "Recall", "F1-score")},
        "caveats": [
            "Tidak ada set uji independen: angka berasal dari set validasi yang juga dipakai early stopping "
            "untuk memilih epoch terbaik, sehingga cenderung optimistis.",
            "Hanya kelas 'car'; sepeda motor (moda dominan di Jakarta), bus, dan truk tidak dibedakan.",
            "Precision/recall versi IoU>=0,5 pada conf 0,25 dihitung notebook sendiri dan berbeda dari versi "
            "Ultralytics (P 0,955 / R 0,813) karena aturan pencocokan berbeda.",
        ],
    }
    frames_path = DETECTION_ARTIFACTS / "detections.json"
    if not skip_yolo:
        code = subprocess.call([sys.executable, str(BACKEND / "scripts" / "run_yolo_frames.py")], cwd=ROOT)
        if code != 0:
            raise PipelineError("run_yolo_frames.py gagal")
    frames = json.loads(frames_path.read_text(encoding="utf-8")) if frames_path.exists() else None
    log(f"  validasi tercatat: mAP50 {recorded['ultralytics']['map50']}, F1 {recorded['iou50_matching_conf025']['F1-score']}; "
        f"inferensi frame: {frames['summary']['frames'] if frames else 0} frame")
    return {"recorded_validation": recorded,
            "frame_inference": None if frames is None else {
                "path": rel(frames_path), "summary": frames["summary"], "model": frames["model"],
                "team_model": frames.get("team_model"), "generated_at": frames["generated_at"]}}


# ------------------------------------------------------------------ 9. plots + reports

def make_plots(forecast: dict, bottleneck: dict) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    written = []
    colors = {"actual": "#3b4252", "lstm": "#2563eb", "persistence": "#d97706",
              "moving_average_15": "#059669", "seasonal_naive_1d": "#9333ea",
              "ridge": "#64748b", "hist_gradient_boosting": "#be123c"}
    for horizon, data in forecast["horizons"].items():
        pred = pd.read_csv(ROOT / data["predictions_csv"])
        strongest = data["strongest_baseline"]["model"]
        fig, ax = plt.subplots(figsize=(11, 4))
        shown = pred["intersection_id"].iloc[0]
        one = pred[pred["intersection_id"] == shown]
        t = pd.to_datetime(one["target_time_wib"])
        ax.plot(t, one["actual"], color=colors["actual"], lw=0.6, alpha=0.55, label="aktual (volume 1 menit)")
        ax.plot(t, one["lstm"], color=colors["lstm"], lw=1.4, label="LSTM")
        ax.plot(t, one[strongest], color=colors[strongest], lw=1.0, ls="--",
                label=f"baseline terkuat: {strongest}")
        ax.set_title(f"{shown}, hari uji (7 Mei 2026, sintetis) — horizon {horizon}: prediksi vs aktual")
        ax.set_ylabel("kend/jam")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        path = FIGURES / f"forecast_vs_actual_{horizon}.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        written.append(rel(path))

        fig, ax = plt.subplots(figsize=(7, 3.2))
        resid = pred["lstm"] - pred["actual"]
        ax.hist(resid, bins=60, color=colors["lstm"], alpha=0.8)
        ax.axvline(0, color="#111", lw=0.8)
        ax.set_title(f"Residu LSTM pada hari uji — {horizon} (bias {resid.mean():.0f} kend/jam)")
        ax.set_xlabel("prediksi - aktual (kend/jam)")
        fig.tight_layout()
        path = FIGURES / f"residuals_{horizon}.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        written.append(rel(path))

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=False)
    for ax, (horizon, data) in zip(axes, forecast["horizons"].items()):
        rows = data["comparison"]
        names = [r["model"] for r in rows]
        maes = [r["test"]["mae"] for r in rows]
        ax.barh(names, maes, color=[colors[n] for n in names])
        for i, v in enumerate(maes):
            ax.text(v, i, f" {v:.0f}", va="center", fontsize=8)
        ax.set_title(f"MAE uji — {horizon} (n={data['n']['test']})")
        ax.set_xlabel("kend/jam (lebih kecil = lebih baik)")
        ax.invert_yaxis()
    fig.tight_layout()
    path = FIGURES / "model_vs_baseline_mae.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    written.append(rel(path))

    fig, ax = plt.subplots(figsize=(10, 3.4))
    for horizon, data in forecast["horizons"].items():
        hours = [r["hour"] for r in data["error_by_target_hour"]]
        ax.plot(hours, [r["lstm_mae"] for r in data["error_by_target_hour"]], marker="o", ms=3, label=f"LSTM {horizon}")
    ax.set_xlabel("jam target (WIB)")
    ax.set_ylabel("MAE kend/jam")
    ax.set_title("Galat LSTM per jam pada hari uji")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = FIGURES / "lstm_error_by_hour.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    written.append(rel(path))

    cm = bottleneck["splits"]["test"]["confusion_matrix"]
    matrix = np.asarray(cm["matrix"], dtype=float)
    norm = matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(cm["labels"])), cm["labels"], rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(cm["labels"])), cm["labels"], fontsize=8)
    for i in range(len(cm["labels"])):
        for j in range(len(cm["labels"])):
            if matrix[i, j]:
                ax.text(j, i, f"{norm[i, j]:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if norm[i, j] > 0.6 else "#111")
    ax.set_xlabel("prediksi")
    ax.set_ylabel("label simulator")
    ax.set_title("Matriks konfusi (dinormalisasi per baris) — hari 7, label sintetis")
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    path = FIGURES / "bottleneck_confusion_matrix.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    written.append(rel(path))

    per = bottleneck["splits"]["test"]["per_class"]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    x = np.arange(len(per))
    for k, (metric, off) in enumerate((("precision", -0.27), ("recall", 0), ("f1", 0.27))):
        ax.bar(x + off, [p[metric] for p in per], width=0.27, label=metric)
    ax.set_xticks(x, [p["cause"] for p in per], rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_title("Metrik per kelas — klasifikasi penyebab (hari 7, label sintetis)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = FIGURES / "bottleneck_per_class.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    written.append(rel(path))
    log(f"  {len(written)} gambar ditulis ke {rel(FIGURES)}")
    return written


def fmt(v, d=1):
    return "—" if v is None else f"{v:,.{d}f}".replace(",", " ")


def write_reports(forecast: dict, bottleneck: dict, yolo: dict, audit: dict, figures: list[str]) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    # Data quality (human-readable)
    lines = ["# Laporan kualitas data — Traffix D2", "",
             f"Dihasilkan `{forecast['generated_at']}` oleh `{COMMAND}`. JSON lengkap: "
             "`backend/ml/forecast/artifacts/data_quality_report.json`.", ""]
    for d in audit["datasets"]:
        lines += [f"## {d['dataset']}", "",
                  f"- Berkas: `{d['path']}` ({d['bytes']:,} byte, sha256 `{d['sha256'][:16]}…`)",
                  f"- Baris × kolom: {d['rows']:,} × {d['columns']}",
                  f"- Provenans: {d['provenance']}",
                  f"- Rentang waktu: {d.get('time_range', '—')} · zona: {d.get('timezone', '—')} · "
                  f"urut per entitas: {d.get('chronological_within_entity', '—')}",
                  f"- Entitas: {d.get('entities', {}).get('unique', '—')} unik ({d.get('entities', {}).get('column', '—')})",
                  f"- Nilai hilang: {d['missing_values'] or 'tidak ada'}",
                  f"- Baris duplikat: {d['duplicate_rows']} · kunci duplikat {d['key']}: {d['duplicate_keys']}",
                  f"- Nilai non-finit: {d['non_finite_values']}",
                  f"- Cek rentang: " + (", ".join(f"{k} [{v['min']:.2f}, {v['max']:.2f}] pelanggaran {v['violations']}"
                                                  for k, v in d['range_checks'].items()) or "—"),
                  f"- Asal target/label: {d['target_lineage']}",
                  f"- Klaim yang didukung: {d['supports_claim']}", ""]
        if d.get("label_distribution"):
            total = sum(d["label_distribution"].values())
            lines.append("- Distribusi label: " + ", ".join(
                f"{k} {v / total:.1%}" for k, v in d["label_distribution"].items()))
            lines.append("")
    lines += ["## Aturan pembersihan", ""] + [f"- {r}" for r in audit["cleaning"]["rules"]]
    (EVIDENCE / "DATA_QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Evaluation summary (human-readable)
    out = ["# Ringkasan evaluasi D2 — peramalan volume (tugas utama)", "",
           f"Dihasilkan `{forecast['generated_at']}` · commit `{(forecast['git_commit'] or '—')[:10]}`"
           f"{' (working tree berubah)' if forecast['git_dirty'] else ''} · seed {forecast['seed']} · "
           f"perintah `{COMMAND}`", "",
           "**Data sintetis.** Semua angka di bawah adalah kinerja pada benchmark simulator, bukan lalu lintas nyata.", "",
           f"Pertanyaan: {forecast['question']}", "",
           f"Split: {forecast['split']['protocol']}. Latih {forecast['split']['train']}, validasi "
           f"{forecast['split']['validation']}, uji {forecast['split']['test']}.", ""]
    for horizon, data in forecast["horizons"].items():
        out += [f"## Horizon {horizon} — n uji {data['n']['test']} (latih {data['n']['train']}, validasi {data['n']['validation']})",
                "", "| Model | Peran | MAE | RMSE | WAPE % | sMAPE % | MAPE % | R² | Δ MAE LSTM vs model ini |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r in data["comparison"]:
            t = r["test"]
            imp = r["lstm_mae_improvement_pct"]
            out.append(f"| {r['label']} | {r['role']} | {fmt(t['mae'])} | {fmt(t['rmse'])} | {fmt(t['wape_pct'], 2)} | "
                       f"{fmt(t['smape_pct'], 2)} | {fmt(t['mape_pct'], 2)} | {fmt(t['r2'], 3)} | "
                       f"{'—' if imp is None else f'{imp:+.1f}%'} |")
        v = data["lstm_vs_strongest_baseline"]
        b = v["bootstrap"]
        out += ["", f"Baseline terkuat (dipilih dengan MAE validasi): `{data['strongest_baseline']['model']}`. "
                f"Perbaikan MAE LSTM: {v['mae_improvement_pct']:+.1f}% · WAPE {v['wape_improvement_pct']:+.1f}% · "
                f"selisih MAE {b['mae_diff']:+.1f} kend/jam, CI 95% [{b['ci95_low']:+.1f}, {b['ci95_high']:+.1f}] "
                f"({'signifikan' if v['significant'] else 'tidak signifikan'}).",
                f"Model dengan MAE uji terendah: `{data['best_on_test']['model']}` ({fmt(data['best_on_test']['mae'])}).", ""]
    sec = forecast["secondary_experiment"]
    out += [f"## Eksperimen kedua: {sec['title']}", "",
            f"Protokol identik, dataset `{sec['dataset']}`. MAE uji (kend/jam):", "",
            "| Horizon | n uji | LSTM | Baseline terkuat | MAE baseline | Perbaikan | Terbaik di uji |",
            "|---|---|---|---|---|---|---|"]
    for h, data in sec["horizons"].items():
        lstm_m = next(r for r in data["comparison"] if r["model"] == "lstm")["test"]["mae"]
        sb = data["strongest_baseline"]["model"]
        sb_m = next(r for r in data["comparison"] if r["model"] == sb)["test"]["mae"]
        out.append(f"| {h} | {data['n']['test']} | {fmt(lstm_m)} | {sb} | {fmt(sb_m)} | "
                   f"{data['lstm_vs_strongest_baseline']['mae_improvement_pct']:+.1f}% | {data['best_on_test']['model']} |")
    tr = forecast["transfer_v4"]
    out += ["", "## Uji transfer: LSTM hybrid -> replay v4 (tanpa latih ulang)", "",
            "| Horizon | LSTM MAE | Persistence MAE | Perbaikan |", "|---|---|---|---|"]
    for h, v in tr["horizons"].items():
        out.append(f"| {h} | {fmt(v['lstm']['mae'])} | {fmt(v['persistence']['mae'])} | {v['mae_improvement_pct_vs_persistence']:+.1f}% |")
    lg = forecast["legacy_reproduction"]
    out += ["", "## Reproduksi angka notebook lama", "",
            f"Protokol: {lg['protocol']}. Periode uji {lg['test_period'][0]} → {lg['test_period'][1]} (n={lg['n_test']}).", "",
            "| Horizon | MAPE dihitung ulang | MAPE tersimpan | Cocok | MAE | Persistence (obs. terakhir) MAE |",
            "|---|---|---|---|---|---|"]
    for h, v in lg["horizons"].items():
        out.append(f"| {h} | {v['recomputed']['mape_pct']:.3f}% | {v['stored_mape_pct']}% | {'ya' if v['mape_matches_stored'] else 'TIDAK'} | "
                   f"{fmt(v['recomputed']['mae'])} | {fmt(v['persistence_last_observation']['mae'])} |")
    out += ["", "Masalah protokol yang ditemukan:"] + [f"- {i}" for i in lg["issues_found"]]
    bt = bottleneck["splits"]
    out += ["", "## Pendukung: klasifikasi penyebab bottleneck (label simulator)", "",
            "| Split | macro-F1 | balanced acc | accuracy | n |", "|---|---|---|---|---|"]
    for s in ("validation", "test"):
        out.append(f"| {s} | {bt[s]['macro_f1']} | {bt[s]['balanced_accuracy']} | {bt[s]['accuracy']} | {bt[s]['n']} |")
    for name, m in bottleneck["baselines_test"].items():
        out.append(f"| test · baseline {name} | {m['macro_f1']} | {m['balanced_accuracy']} | {m['accuracy']} | {m['n']} |")
    out += ["", f"Cocok dengan metrics.json tersimpan: {bottleneck['matches_stored_metrics']}.", "",
            "## Pendukung: YOLOv8", ""]
    rv = yolo["recorded_validation"]
    out += [f"Metrik **validasi** tercatat (bukan uji, tidak direproduksi di run ini): mAP50 {rv['ultralytics']['map50']}, "
            f"mAP50-95 {rv['ultralytics']['map50_95']}, P/R Ultralytics {rv['ultralytics']['precision']}/{rv['ultralytics']['recall']}, "
            f"F1 (IoU≥0,5, conf 0,25) {rv['iou50_matching_conf025']['F1-score']} pada {rv['images'].get('val')} gambar / "
            f"{rv['val_instances']} objek."]
    if yolo["frame_inference"]:
        fi = yolo["frame_inference"]
        s = fi["summary"]
        out.append(f"Detektor demo kamera: `{fi['model']['weights']}` ({fi['model'].get('description', '')}), "
                   f"kelas {', '.join(fi['model']['classes'])}, imgsz {fi['model']['imgsz']}. "
                   f"Inferensi nyata pada {s['frames']} frame CCTV replay, rata-rata kotak per frame "
                   + ", ".join(f"{p} {v['mean_vehicle_count']} (model tim {v.get('mean_team_model_count', '—')})"
                               for p, v in s["by_period"].items())
                   + f"; {s['mean_inference_ms']} ms/frame (CPU). Tanpa label acuan — bukan ukuran akurasi.")
    out += ["", "## Gambar", ""] + [f"- `{f}`" for f in figures]
    (EVIDENCE / "D2_EVALUATION_SUMMARY.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    # Metrics brief (one page, pitch)
    brief = ["# D2 Metrics Brief (dihasilkan otomatis)", "",
             f"Sumber: `backend/ml/forecast/artifacts/forecast_evaluation.json` · `{forecast['generated_at']}` · "
             f"`{COMMAND}`. Jangan diedit manual — jalankan ulang perintah.", "",
             "> Semua data **sintetis** (simulator, seed 42). Angka = kinerja pada benchmark simulasi, bukan lalu lintas nyata.", "",
             "## Tugas utama: peramalan volume simpang (kend/jam), hari uji 7 Mei 2026", "",
             "| Horizon | n uji | LSTM MAE | LSTM WAPE | Baseline terkuat | Baseline MAE | Perbaikan MAE | CI 95% selisih MAE | Terbaik di uji |",
             "|---|---|---|---|---|---|---|---|---|"]
    for h, data in forecast["horizons"].items():
        lstm = next(r for r in data["comparison"] if r["model"] == "lstm")["test"]
        sb = data["strongest_baseline"]["model"]
        base = next(r for r in data["comparison"] if r["model"] == sb)["test"]
        v = data["lstm_vs_strongest_baseline"]
        brief.append(f"| {h} | {data['n']['test']} | {fmt(lstm['mae'])} | {fmt(lstm['wape_pct'], 1)}% | {sb} | {fmt(base['mae'])} | "
                     f"{v['mae_improvement_pct']:+.1f}% | [{v['bootstrap']['ci95_low']:+.0f}, {v['bootstrap']['ci95_high']:+.0f}] | "
                     f"{data['best_on_test']['model']} |")
    sec = forecast["secondary_experiment"]
    brief += ["", f"Eksperimen kedua ({sec['title']}), MAE LSTM vs baseline terkuat: " + "; ".join(
        f"{h} {fmt(next(r for r in d['comparison'] if r['model'] == 'lstm')['test']['mae'])} "
        f"({d['lstm_vs_strongest_baseline']['mae_improvement_pct']:+.1f}%)"
        for h, d in sec["horizons"].items())]
    brief += ["", "Uji transfer LSTM hybrid -> replay v4 tanpa latih ulang (bukti pergeseran domain): " + "; ".join(
        f"{h} LSTM MAE {fmt(v['lstm']['mae'])} vs persistence {fmt(v['persistence']['mae'])} ({v['mae_improvement_pct_vs_persistence']:+.1f}%)"
        for h, v in forecast["transfer_v4"]["horizons"].items()), "",
        "## Pendukung", "",
        f"- Penyebab bottleneck (9 kelas, label simulator), hari 7: macro-F1 {bt['test']['macro_f1']} · balanced acc "
        f"{bt['test']['balanced_accuracy']} vs rule-based {bottleneck['baselines_test']['rule_based']['macro_f1']} / "
        f"majority {bottleneck['baselines_test']['majority_class']['macro_f1']} (macro-F1). Direproduksi: {bottleneck['matches_stored_metrics']}.",
        f"- YOLOv8 model tim (`best.pt`, 1 kelas 'car'), **validasi** 100 gambar Kaggle: mAP50 {rv['ultralytics']['map50']}, "
        f"F1 {rv['iou50_matching_conf025']['F1-score']} — tidak ada set uji independen; pada CCTV tol model ini melewatkan "
        f"sebagian besar kendaraan kecil/jauh.",
        *([f"- Demo kamera memakai YOLOv8m pretrained COCO (bukan dilatih tim), kelas mobil/motor/bus/truk: rata-rata "
           f"{yolo['frame_inference']['summary']['mean_vehicle_count']} kotak per frame vs "
           f"{yolo['frame_inference']['summary'].get('mean_team_model_count', '—')} untuk model tim pada "
           f"{yolo['frame_inference']['summary']['frames']} frame yang sama — keluaran model tanpa label acuan, bukan akurasi."]
          if yolo.get("frame_inference") and yolo["frame_inference"]["summary"].get("mean_team_model_count") is not None else []),
        "", "## Klaim yang TIDAK boleh dibuat", ""] + [f"- {c}" for c in forecast["not_claims"]] + [
        "- Akurasi di atas tidak boleh disebut akurasi lalu lintas Jakarta nyata.",
        "- Label penyebab bottleneck berasal dari aturan simulator, bukan kejadian lapangan."]
    pitch = ROOT / "docs" / "pitch"
    pitch.mkdir(parents=True, exist_ok=True)
    (pitch / "D2_METRICS_BRIEF.md").write_text("\n".join(brief) + "\n", encoding="utf-8")
    log("  laporan: DATA_QUALITY_REPORT.md, D2_EVALUATION_SUMMARY.md, docs/pitch/D2_METRICS_BRIEF.md")


def validate_outputs(forecast: dict) -> None:
    for horizon, data in forecast["horizons"].items():
        for r in data["comparison"]:
            for k in ("mae", "rmse", "wape_pct"):
                v = r["test"][k]
                if v is None or not np.isfinite(v):
                    raise PipelineError(f"metrik tidak valid: {horizon}/{r['model']}/{k}={v}")
        if data["n"]["test"] < 500:
            raise PipelineError(f"sampel uji {horizon} terlalu sedikit: {data['n']['test']}")


def refresh_yolo_only(skip_yolo: bool) -> None:
    """Re-run the YOLO step and rebuild every report from the stored artefacts.

    The forecasting and classifier numbers are read back from their JSON artefacts,
    unchanged; only the detection evidence is recomputed.
    """
    from ml.forecast import evaluate as fe

    paths = {
        "forecast": fe.ARTIFACT_DIR / "forecast_evaluation.json",
        "audit": fe.ARTIFACT_DIR / "data_quality_report.json",
        "bottleneck": BOTTLENECK_ARTIFACTS / "reproduction.json",
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise PipelineError(f"--refresh-yolo butuh artefak run penuh: {missing}")
    forecast, audit, bottleneck = (json.loads(p.read_text(encoding="utf-8")) for p in paths.values())
    yolo = yolo_evidence(skip_yolo)
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": git_commit(), "git_dirty": git_dirty()}
    forecast.setdefault("supporting", {})["yolo"] = yolo
    write_json(paths["forecast"], forecast)
    write_json(DETECTION_ARTIFACTS / "yolo_evidence.json", {**meta, **yolo})
    write_reports(forecast, bottleneck, yolo, audit, forecast.get("figures", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regenerate-v4", action="store_true", help="jalankan ulang generate_data_v4.py (seed 42)")
    parser.add_argument("--skip-yolo", action="store_true", help="lewati inferensi frame YOLO (pakai detections.json yang ada)")
    parser.add_argument("--refresh-yolo", action="store_true",
                        help="hanya perbarui bukti YOLO dan laporan dari artefak tersimpan (tanpa melatih ulang)")
    args = parser.parse_args()
    started = time.time()
    try:
        if args.refresh_yolo:
            refresh_yolo_only(args.skip_yolo)
            log(f"[SELESAI] {time.time() - started:.0f} detik")
            return 0
        if args.regenerate_v4:
            log("[0/9] regenerasi data v4 (seed 42)")
            code = subprocess.call([sys.executable, str(ROOT / "data" / "data_synthetic" / "v4" / "generate_data_v4.py")],
                                   cwd=ROOT / "data" / "data_synthetic" / "v4")
            if code:
                raise PipelineError("generate_data_v4.py gagal")
        pre = preflight(args.skip_yolo)
        meta = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "git_commit": git_commit(), "git_dirty": git_dirty()}
        audit = data_audit()
        from ml.forecast import evaluate as fe

        frames = {key: fe.load_experiment(key) for key in fe.EXPERIMENTS}
        lineage = lineage_and_leakage(frames)
        log("[4/9] reproduksi model LSTM notebook")
        legacy = fe.reproduce_legacy(log=log)
        if not all(v["mape_matches_stored"] for v in legacy["horizons"].values()):
            log("  [WARN] MAPE notebook tidak tereproduksi persis — lihat legacy_reproduction")
        log("[5/9] eksperimen protokol D2 (latih hari 1-5, validasi hari 6, uji hari 7)")
        fcs = {key: forecasting(frames[key], key) for key in fe.EXPERIMENTS}
        log("[6/9] uji transfer: model hybrid -> replay v4 (data yang dipakai aplikasi)")
        hyb = fcs["hybrid_tmg"]
        transfer = fe.transfer_v4(hyb["models"], hyb["target_scalers"], hyb["feat_scaler"], hyb["seq_lens"], log=log)
        forecast = summarise_forecast(frames, fcs, transfer, legacy, lineage, audit, meta)
        validate_outputs(forecast)
        bottleneck = bottleneck_reproduction()
        yolo = yolo_evidence(args.skip_yolo)
        log("[9/9] gambar, artefak, laporan")
        figures = make_plots(forecast, bottleneck)
        forecast["figures"] = figures
        forecast["supporting"] = {
            "bottleneck": {k: bottleneck[k] for k in ("model_name", "matches_stored_metrics", "stored_metrics")}
                          | {"validation": {k: bottleneck["splits"]["validation"][k] for k in ("macro_f1", "balanced_accuracy", "accuracy", "n")},
                             "test": {k: bottleneck["splits"]["test"][k] for k in ("macro_f1", "balanced_accuracy", "accuracy", "n")}},
            "yolo": yolo,
        }
        forecast["preflight"] = pre
        write_json(fe.ARTIFACT_DIR / "data_quality_report.json", {**meta, **audit, "lineage": lineage})
        write_json(fe.ARTIFACT_DIR / "forecast_evaluation.json", forecast)
        write_json(BOTTLENECK_ARTIFACTS / "reproduction.json", {**meta, **bottleneck})
        write_json(DETECTION_ARTIFACTS / "yolo_evidence.json", {**meta, **yolo})
        write_reports(forecast, bottleneck, yolo, audit, figures)
    except PipelineError as exc:
        log(f"[GAGAL] {exc}")
        return 1
    log(f"[SELESAI] {time.time() - started:.0f} detik")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
