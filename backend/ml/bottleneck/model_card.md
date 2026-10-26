# Model Card — Klasifikasi Penyebab Bottleneck Traffix v4

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

- 46 fitur, seluruhnya dari `features.FEATURE_COLUMNS` (19 dasar + lag 1/5/15/30/60
  dan rolling 15/60 dari volume, antrean, kecepatan). Lag/rolling hanya melihat ke belakang.
- Dilarang sebagai fitur (17 kolom): `bottleneck_cause`, `bottleneck_rule`, `bottleneck_secondary`, `weather_condition`, `curah_hujan_mm_jam`, `tinggi_genangan_cm`, `durasi_hujan_menit`, `lane_closure`, `pct_lajur_tertutup`, `durasi_kerja_jalan_menit`, `event_flag`, `lampu_operasional`, `accident_count`, `roadwork_flag`, `vc_ratio`, `los`, `smp_ekivalen`.
  Alasan: kolom-kolom itu **mendefinisikan label** (`curah_hujan_mm_jam >= 2` → `hujan`,
  `tinggi_genangan_cm >= 15` → `banjir`, `lampu_operasional == 0` → `lampu_mati`,
  `lane_closure` → `perbaikan_jalan`, `event_flag` → `keramaian_event`, `accident_count` → `kecelakaan`),
  sehingga memakainya = kebocoran label. `vc_ratio`/`los`/`smp_ekivalen` turunan langsung dari label
  `volume_puncak`/`kendaraan_berat`. Dicek otomatis oleh `features.assert_no_leakage`.

## 4. Protokol split (temporal, tanpa acak)

| Bagian | Hari | Baris |
|---|---|---|
| Latih | 1-5 | 216000 |
| Validasi | 6 | 43200 |
| Uji | 7 | 43200 |

Pemilihan model **hanya** dari macro-F1 validasi; hari uji dievaluasi **sekali** setelah pemenang dikunci.

## 5. Hasil

Validasi:

| Model | macro-F1 | balanced acc | accuracy |
|---|---|---|---|
| hist_gradient_boosting | 0.8349 | 0.8561 | 0.8933 |
| mlp | 0.6793 | 0.7567 | 0.6754 |

Hari uji (hari 7):

| Model | macro-F1 | balanced acc | accuracy |
|---|---|---|---|
| hist_gradient_boosting | 0.9002 | 0.8853 | 0.9371 |
| majority_class | 0.0710 | 0.1111 | 0.4694 |
| rule_based | 0.1730 | 0.2237 | 0.5597 |

Pemenang: **hist_gradient_boosting**.

Recall kelas langka: `banjir` 1.0000 (support 3151),
`lampu_mati` 0.9980 (support 989).

## 6. Analisis kesalahan (dihitung dari confusion matrix hari uji)

Pasangan paling sering tertukar:

- `keramaian_event` diprediksi `normal`: 801 tick (42.5% dari seluruh tick berlabel `keramaian_event`)
- `hujan` diprediksi `normal`: 774 tick (16.4% dari seluruh tick berlabel `hujan`)
- `keramaian_event` diprediksi `kendaraan_berat`: 292 tick (15.5% dari seluruh tick berlabel `keramaian_event`)
- `hujan` diprediksi `keramaian_event`: 248 tick (5.2% dari seluruh tick berlabel `hujan`)
- `keramaian_event` diprediksi `hujan`: 158 tick (8.4% dari seluruh tick berlabel `keramaian_event`)

Pola: kebingungan terbesar terjadi antar kelas yang **gejala lalu lintasnya tumpang tindih** —
gangguan yang sama-sama menurunkan kecepatan dan menaikkan antrean. Fitur yang boleh dipakai tidak
memisahkan penyebab, hanya tingkat keparahannya; itu batas atas yang wajar, bukan bug.

## 7. Feature importance (permutation, sampel validasi)

| # | Fitur | Importance (Δ macro-F1) |
|---|---|---|
| 1 | `wait_time_min` | 0.45092 |
| 2 | `avg_speed_kmh` | 0.36822 |
| 3 | `proporsi_roda_6plus` | 0.15339 |
| 4 | `hour` | 0.12705 |
| 5 | `vehicle_count_1min` | 0.11578 |
| 6 | `weather_temp_c` | 0.04419 |
| 7 | `roll60_mean_avg_speed_kmh` | 0.03168 |
| 8 | `volume_veh_per_hour` | 0.02540 |

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
cd C:/Users/prafasta/Documents/traffix
./.venv/Scripts/python.exe backend/ml/bottleneck/train_bottleneck.py
```

Menulis ulang `backend/ml/bottleneck/artifacts/bottleneck_classifier.joblib`, `metrics.json`, dan
`model_card.md`. Deterministik (seed 42).
