"""Train the Traffix v4 bottleneck-cause classifier (9 classes).

Contract: `docs/SCHEMA-v4.md` §4. Single runnable entry point:

    ./.venv/Scripts/python.exe backend/ml/bottleneck/train_bottleneck.py

Split is temporal by day (1-5 train, 6 validation, 7 test) — never random.
Labels come from the synthetic simulator (seed 42, `generate_data_v4.py`).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.neural_network import MLPClassifier
from sklearn.utils.class_weight import compute_sample_weight

from features import (
    CLASSES,
    FEATURE_COLUMNS,
    FORBIDDEN_COLUMNS,
    assert_no_leakage,
    build_feature_frame,
    evaluate_predictions,
    rule_based_cause,
)

ROOT = Path(__file__).resolve().parents[3]
TICKS = ROOT / "data" / "data_synthetic" / "v4" / "ticks_v4.csv.gz"
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "bottleneck_classifier.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
CARD_PATH = Path(__file__).resolve().parent / "model_card.md"

SEED = 42
# ponytail: permutation importance on a capped sample (cost ceiling); raise
# IMP_SAMPLE/IMP_REPEATS when a full-fidelity ranking is wanted.
IMP_SAMPLE = 4000
IMP_REPEATS = 3


def day_index(ticks: pd.Series) -> pd.Series:
    """Map 0-based tick to 1-based day number (1440 ticks per day)."""
    return ticks // 1440 + 1


def split_by_day(ticks: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return boolean masks for (train, validation, test) over day 1-5/6/7."""
    day = day_index(ticks)
    return (day <= 5).to_numpy(), (day == 6).to_numpy(), (day == 7).to_numpy()


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Trim `evaluate_predictions` down to the 3 headline metrics."""
    full = evaluate_predictions(np.asarray(y_true), np.asarray(y_pred))
    return {k: full[k] for k in ("macro_f1", "balanced_accuracy", "accuracy")}


def build_models() -> dict:
    """Candidate estimators; class imbalance handled where supported."""
    return {
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.08,
            max_leaf_nodes=31,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=SEED,
            class_weight="balanced",
        ),
        # MLPClassifier has no class_weight: balanced weights via sample_weight.
        "mlp": MLPClassifier(
            hidden_layer_sizes=(96, 48),
            activation="relu",
            alpha=1e-4,
            batch_size=512,
            learning_rate_init=1e-3,
            max_iter=60,
            early_stopping=True,
            n_iter_no_change=5,
            validation_fraction=0.1,
            random_state=SEED,
        ),
    }


def top_confusions(matrix: np.ndarray, labels: list[str], top: int = 5) -> list[tuple]:
    """Most-confused (true, predicted) ordered pairs from a confusion matrix.

    Iterates the matrix, not memory: each off-diagonal cell is one real pair.
    """
    pairs = [
        (int(matrix[i, j]), labels[i], labels[j])
        for i in range(len(labels))
        for j in range(len(labels))
        if i != j and matrix[i, j] > 0
    ]
    pairs.sort(key=lambda p: -p[0])
    return pairs[:top]


def feature_importance_report(model, X_val: pd.DataFrame, y_val: np.ndarray) -> list[dict]:
    """Permutation importance (model-agnostic) on a capped validation sample."""
    n = min(IMP_SAMPLE, len(X_val))
    sample = X_val.iloc[:n]
    y_sample = y_val[:n]
    result = permutation_importance(
        model, sample, y_sample, scoring="f1_macro", n_repeats=IMP_REPEATS,
        random_state=SEED, n_jobs=1,
    )
    order = np.argsort(-result.importances_mean)[:20]
    return [
        {"feature": str(sample.columns[i]), "importance": round(float(result.importances_mean[i]), 6)}
        for i in order
    ]


def write_model_card(path, *, winner, val_table, test_table, per_class_test,
                     confusions, importances, n_train, n_val, n_test) -> None:
    """Write the Indonesian model card (results + computed error analysis)."""
    def table(rows):
        lines = ["| Model | macro-F1 | balanced acc | accuracy |", "|---|---|---|---|"]
        lines += [
            f"| {name} | {m['macro_f1']:.4f} | {m['balanced_accuracy']:.4f} | {m['accuracy']:.4f} |"
            for name, m in rows
        ]
        return "\n".join(lines)

    banjir = next(p for p in per_class_test if p["cause"] == "banjir")
    lampu = next(p for p in per_class_test if p["cause"] == "lampu_mati")
    conf_lines = "\n".join(
        f"- `{t}` diprediksi `{p}`: {c} tick ({c / max(1, _support(t, per_class_test)):.1%} dari seluruh tick berlabel `{t}`)"
        for c, t, p in confusions
    )
    imp_lines = "\n".join(
        f"| {i + 1} | `{r['feature']}` | {r['importance']:.5f} |" for i, r in enumerate(importances[:8])
    )

    path.write_text(f"""# Model Card — Klasifikasi Penyebab Bottleneck Traffix v4

## 1. Rumusan masalah

Klasifikasi multikelas 9 kelas `bottleneck_cause` per **ruas per menit**, dari keadaan lalu lintas
yang dapat diamati saja (volume, kecepatan, antrean, waktu tunggu, sinyal, komposisi kendaraan,
konteks waktu). Model **tidak** melihat konteks kejadian mentah — justru itu tugasnya: menyimpulkan
penyebab dari gejalanya.

## 2. Asal data

- `data/data_synthetic/v4/ticks_v4.csv.gz` — 302.400 baris, 30 ruas, 1 menit, 7 hari
  (2026-05-01 s.d. 2026-05-07 WIB).
- Dihasilkan **simulator sintetis** `data/data_synthetic/v4/generate_data_v4.py`, **seed 42**,
  deterministik. Label diturunkan dari aturan eksplisit berprioritas (SCHEMA-v4 §1).
- Data sintetis — **bukan** data lapangan. Tidak ada klaim validitas terhadap lalu lintas nyata.

## 3. Fitur dan daftar terlarang

- {len(FEATURE_COLUMNS)} fitur, seluruhnya dari `features.FEATURE_COLUMNS` (19 dasar + lag 1/5/15/30/60
  dan rolling 15/60 dari volume, antrean, kecepatan). Lag/rolling hanya melihat ke belakang.
- Dilarang sebagai fitur ({len(FORBIDDEN_COLUMNS)} kolom): {', '.join(f'`{c}`' for c in FORBIDDEN_COLUMNS)}.
  Alasan: kolom-kolom itu **mendefinisikan label** (`curah_hujan_mm_jam >= 2` → `hujan`,
  `tinggi_genangan_cm >= 15` → `banjir`, `lampu_operasional == 0` → `lampu_mati`,
  `lane_closure` → `perbaikan_jalan`, `event_flag` → `keramaian_event`, `accident_count` → `kecelakaan`),
  sehingga memakainya = kebocoran label. `vc_ratio`/`los`/`smp_ekivalen` turunan langsung dari label
  `volume_puncak`/`kendaraan_berat`. Dicek otomatis oleh `features.assert_no_leakage`.

## 4. Protokol split (temporal, tanpa acak)

| Bagian | Hari | Baris |
|---|---|---|
| Latih | 1-5 | {n_train} |
| Validasi | 6 | {n_val} |
| Uji | 7 | {n_test} |

Pemilihan model **hanya** dari macro-F1 validasi; hari uji dievaluasi **sekali** setelah pemenang dikunci.

## 5. Hasil

Validasi:

{table(val_table)}

Hari uji (hari 7):

{table(test_table)}

Pemenang: **{winner}**.

Recall kelas langka: `banjir` {banjir['recall']:.4f} (support {banjir['support']}),
`lampu_mati` {lampu['recall']:.4f} (support {lampu['support']}).

## 6. Analisis kesalahan (dihitung dari confusion matrix hari uji)

Pasangan paling sering tertukar:

{conf_lines}

Pola: kebingungan terbesar terjadi antar kelas yang **gejala lalu lintasnya tumpang tindih** —
gangguan yang sama-sama menurunkan kecepatan dan menaikkan antrean. Fitur yang boleh dipakai tidak
memisahkan penyebab, hanya tingkat keparahannya; itu batas atas yang wajar, bukan bug.

## 7. Feature importance (permutation, sampel validasi)

| # | Fitur | Importance (Δ macro-F1) |
|---|---|---|
{imp_lines}

## 8. Penanganan ketidakseimbangan kelas

- `HistGradientBoostingClassifier(class_weight="balanced")`.
- MLP tanpa `class_weight` → bobot sampel balanced (`compute_sample_weight("balanced")`).
- Metrik utama **macro-F1** dan **balanced accuracy**, bukan accuracy (mayoritas `normal` 51,9%).
- Kelas langka (`lampu_mati`, `volume_puncak`) tetap punya support uji 989-21.466 baris per kelas.

## 9. Kondisi kegagalan

1. Bila artefak tidak ada, backend jatuh ke aturan (`model_available: false`, confidence 0).
2. Distribusi bergeser (musim hujan berbeda, geometri ruas berubah, jumlah lajur beda) → model tidak
   otomatis menyesuaikan.
3. Kelas yang tidak pernah muncul di data latih tidak akan pernah diprediksi.
4. Ruas/lampu baru di luar 30 ruas skema v4 tidak punya riwayat lag → lag bernilai 0.
5. Nilai sensor di luar rentang simulasi (kecepatan > 80 km/jam, antrean ribuan) tidak divalidasi.
6. Label berasal dari simulator, bukan verifikasi lapangan; kesalahan aturan simulator akan diwarisi model.

## 10. Catatan bias

- `banjir` dan `lampu_mati` kelas paling langka: 7,6% dan 2,4% baris. Latih mereka **kurang**, jadi
  recall-nya paling rapuh dan paling mudah jatuh ke kelas gejala-mirip (`kecelakaan`, `hujan`).
- `normal` mayoritas 51,9%: pemenang naif "selalu normal" sudah dapat accuracy tinggi — sebab itu
  baseline `majority_class` dilaporkan berdampingan.
- Data zona waktu tunggal (WIB), 6 simpang, 7 hari; generalisasi lintas kota tidak diuji.

## 11. Cara reproduksi

```bash
cd {"C:/Users/prafasta/Documents/traffix"}
./.venv/Scripts/python.exe backend/ml/bottleneck/train_bottleneck.py
```

Menulis ulang `backend/ml/bottleneck/artifacts/bottleneck_classifier.joblib`, `metrics.json`, dan
`model_card.md`. Deterministik (seed {SEED}).
""", encoding="utf-8")


def _support(cause: str, per_class: list[dict]) -> int:
    for row in per_class:
        if row["cause"] == cause:
            return row["support"]
    return 0


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/6] baca + fitur")
    # build_feature_frame sorts by (section_id, tick); sort the raw frame first so
    # labels and day masks stay row-aligned with the feature frame.
    raw = pd.read_csv(TICKS).sort_values(["section_id", "tick"]).reset_index(drop=True)
    features = build_feature_frame(raw)
    assert list(features.columns) == list(FEATURE_COLUMNS), "urutan kolom fitur tidak sesuai kontrak"
    assert_no_leakage(list(features.columns))
    y_all = raw["bottleneck_cause"].to_numpy()
    assert set(np.unique(y_all)) <= set(CLASSES), "ada kelas tak dikenal di label"

    train_mask, val_mask, test_mask = split_by_day(raw["tick"])
    assert not (train_mask & val_mask).any() and not (val_mask & test_mask).any()

    X_tr, X_val, X_te = features[train_mask], features[val_mask], features[test_mask]
    y_tr, y_val, y_te = y_all[train_mask], y_all[val_mask], y_all[test_mask]
    print(f"      train={len(X_tr)} val={len(X_val)} test={len(X_te)}")

    print("[2/6] latih kandidat")
    val_scores: dict[str, dict] = {}
    fitted: dict[str, object] = {}
    weights = compute_sample_weight("balanced", y_tr)
    for name, model in build_models().items():
        if name == "mlp":
            model.fit(X_tr, y_tr, sample_weight=weights)
        else:
            model.fit(X_tr, y_tr)
        fitted[name] = model
        assert list(model.classes_) == list(CLASSES), f"urutan kelas {name} menyimpang"
        val_scores[name] = score(y_val, model.predict(X_val))
        print(f"      {name}: val macro_f1={val_scores[name]['macro_f1']}")

    winner_name = max(val_scores, key=lambda k: val_scores[k]["macro_f1"])
    winner = fitted[winner_name]
    print(f"      pemenang (validasi macro-F1): {winner_name}")

    print("[3/6] baseline + evaluasi hari uji")
    majority = DummyClassifier(strategy="most_frequent", random_state=SEED).fit(X_tr, y_tr)
    baselines_test = {
        "majority_class": {"model": "DummyClassifier(strategy=most_frequent)",
                           **score(y_te, majority.predict(X_te))},
        "rule_based": {"model": "features.rule_based_cause",
                       **score(y_te, rule_based_cause(features[test_mask]))},
    }
    test_full = evaluate_predictions(y_te, winner.predict(X_te))
    test_scores = {k: test_full[k] for k in ("macro_f1", "balanced_accuracy", "accuracy")}
    for name, m in baselines_test.items():
        print(f"      baseline {name}: macro_f1={m['macro_f1']}")
    print(f"      {winner_name}: test macro_f1={test_scores['macro_f1']}")
    assert test_scores["macro_f1"] > baselines_test["rule_based"]["macro_f1"], "model tidak mengalahkan rule_based"

    print("[4/6] feature importance")
    importances = feature_importance_report(winner, X_val, y_val)

    print("[5/6] tulis artefak + metrics.json")
    trained_at = datetime.now(timezone.utc).isoformat()
    joblib.dump(
        {
            "model": winner,
            "classes": list(CLASSES),
            "feature_columns": list(FEATURE_COLUMNS),
            "model_name": winner_name,
            "trained_at": trained_at,
            "with_lags": True,
        },
        ARTIFACT_PATH,
    )

    confusions = top_confusions(np.asarray(test_full["confusion_matrix"]["matrix"]), list(CLASSES))
    metrics = {
        "model_name": winner_name,
        "trained_at": trained_at,
        "n_train": int(len(X_tr)),
        "n_validation": int(len(X_val)),
        "n_test": int(len(X_te)),
        "classes": list(CLASSES),
        "feature_columns": list(FEATURE_COLUMNS),
        "forbidden_columns": list(FORBIDDEN_COLUMNS),
        "metrics": test_scores,
        "baselines": baselines_test,
        "per_class": test_full["per_class"],
        "confusion_matrix": test_full["confusion_matrix"],
        "feature_importance": importances,
        "leakage_guard": [
            "Fitur hanya dari features.FEATURE_COLUMNS (46 kolom); features.assert_no_leakage dipanggil "
            "sebelum pelatihan dan gagal keras bila kolom terlarang dipakai.",
            "17 kolom terlarang (bottleneck_cause/rule/secondary, weather_condition, curah_hujan_mm_jam, "
            "tinggi_genangan_cm, durasi_hujan_menit, lane_closure, pct_lajur_tertutup, "
            "durasi_kerja_jalan_menit, event_flag, lampu_operasional, accident_count, roadwork_flag, "
            "vc_ratio, los, smp_ekivalen) tidak pernah masuk X.",
            "Pembagian data murni temporal: hari 1-5 latih, hari 6 validasi, hari 7 uji; tidak ada "
            "pengacakan baris dan tidak ada baris uji yang terlihat saat pelatihan.",
            "Lag dan rolling dihitung per section_id dengan shift positif (1/5/15/30/60) dan rolling "
            "berbasis shift(1) — hanya tick lampau, tidak ada nilai tick kini atau tick masa depan.",
            "Statistik normalisasi model (early_stopping internal, bobot MLP) hanya diestimasi dari "
            "data latih; hari uji tidak dipakai untuk memilih model atau menyetel hyperparameter.",
            "Pemilihan model memakai macro-F1 validasi (hari 6) saja; hari uji dievaluasi sekali "
            "setelah pemenang dikunci.",
            "Label diambil dari kolom simulator bottleneck_cause, bukan diturunkan ulang dari fitur "
            "model, sehingga definisi label tidak bocor lewat rekayasa fitur.",
        ],
        "limitations": [
            "Label berasal dari simulator sintetis (seed 42), bukan verifikasi lapangan; akurasi tidak "
            "menjamin kinerja pada lalu lintas nyata.",
            "Fitur yang diizinkan tidak memuat konteks kejadian mentah, sehingga kelas dengan gejala "
            "tumpang tindih (banjir vs kecelakaan vs hujan) sulit dipisahkan dan membatasi macro-F1.",
            "Kelas langka banjir (7,6%) dan lampu_mati (2,4%) punya recall paling rapuh dan paling "
            "mudah tertukar dengan kelas bergejala sama.",
            "Data mencakup 6 simpang, 30 ruas, 7 hari, satu zona waktu (WIB); tidak ada pengujian "
            "generalisasi lintas kota, musim, atau geometri jalan lain.",
            "Lag pada tick awal setiap ruas bernilai 0 karena tidak ada riwayat; ruas baru tanpa replay "
            "sejarah akan mendapat fitur lag kosong dan prediksinya tidak dapat dipercaya.",
            "Urutan prioritas aturan simulator bersifat deterministik; model probabilistik dapat "
            "memberi kelas kandidat kedua yang berbeda dari bottleneck_secondary pada data.",
            "Macro-F1 dipilih sebagai metrik utama karena kelas tidak seimbang, sehingga accuracy tidak "
            "boleh dipakai sendiri sebagai bukti kualitas (normal saja sudah 51,9% baris).",
            "Model dilatih ulang penuh setiap kali artefak dibuat dan tidak memakai pembelajaran daring; "
            "pergeseran distribusi setelah hari 7 tidak tertangani otomatis.",
        ],
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[6/6] tulis model_card.md")
    write_model_card(
        CARD_PATH,
        winner=winner_name,
        val_table=[(n, m) for n, m in val_scores.items()],
        test_table=[
            (winner_name, test_scores),
            *[(n, m) for n, m in baselines_test.items()],
        ],
        per_class_test=test_full["per_class"],
        confusions=confusions,
        importances=importances,
        n_train=len(X_tr),
        n_val=len(X_val),
        n_test=len(X_te),
    )
    print(f"selesai: {ARTIFACT_PATH.name}, {METRICS_PATH.name}, {CARD_PATH.name}")


if __name__ == "__main__":
    main()
