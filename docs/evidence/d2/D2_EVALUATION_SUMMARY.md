# Ringkasan evaluasi D2 — peramalan volume (tugas utama)

Dihasilkan `2026-10-27T09:05:04+00:00` · commit `2de9216b32` (working tree berubah) · seed 42 · perintah `python backend/scripts/run_d2_evaluation.py`

**Data sintetis.** Semua angka di bawah adalah kinerja pada benchmark simulator, bukan lalu lintas nyata.

Pertanyaan: Seberapa akurat LSTM meramalkan volume lalu lintas simpang (kend/jam) 15 menit, 2 jam, dan 4 jam ke depan dari 41 fitur yang tersedia pada waktu terbit, dibanding baseline naif dan model tabular pada hari uji yang sama, untuk 6 simpang yang dipantau aplikasi?

Split: kronologis per hari kalender; target harus di hari yang sama dengan waktu terbit; jendela riwayat boleh dari hari sebelumnya. Latih hari 1-5 (1-5 Mei 2026), validasi hari 6 (6 Mei 2026), uji hari 7 (7 Mei 2026).

## Horizon 15m — n uji 8550 (latih 42396, validasi 8550)

| Model | Peran | MAE | RMSE | WAPE % | sMAPE % | MAPE % | R² | Δ MAE LSTM vs model ini |
|---|---|---|---|---|---|---|---|---|
| LSTM (model utama) | model | 364.9 | 518.5 | 11.70 | 11.85 | 11.58 | 0.888 | — |
| Persistence (volume saat ini) | baseline | 435.3 | 632.8 | 13.96 | 13.20 | 13.44 | 0.833 | +16.2% |
| Rata-rata 15 menit terakhir | baseline | 492.6 | 746.7 | 15.79 | 14.15 | 14.58 | 0.768 | +25.9% |
| Seasonal naive (kemarin, jam sama) | baseline | 369.4 | 507.5 | 11.84 | 12.15 | 12.25 | 0.893 | +1.2% |
| Ridge regression | pembanding | 325.2 | 457.9 | 10.43 | 10.50 | 10.42 | 0.913 | -12.2% |
| HistGradientBoosting | pembanding | 274.3 | 403.0 | 8.79 | 8.65 | 8.66 | 0.932 | -33.0% |

Baseline terkuat (dipilih dengan MAE validasi): `seasonal_naive_1d`. Perbaikan MAE LSTM: +1.2% · WAPE +1.2% · selisih MAE -4.5 kend/jam, CI 95% [-32.8, +25.0] (tidak signifikan).
Model dengan MAE uji terendah: `hist_gradient_boosting` (274.3).

## Horizon 2h — n uji 7920 (latih 41766, validasi 7920)

| Model | Peran | MAE | RMSE | WAPE % | sMAPE % | MAPE % | R² | Δ MAE LSTM vs model ini |
|---|---|---|---|---|---|---|---|---|
| LSTM (model utama) | model | 577.8 | 854.9 | 18.19 | 17.68 | 17.27 | 0.711 | — |
| Persistence (volume saat ini) | baseline | 1 761.9 | 2 402.9 | 55.47 | 47.45 | 56.58 | -1.282 | +67.2% |
| Rata-rata 15 menit terakhir | baseline | 1 778.8 | 2 404.4 | 56.00 | 47.94 | 57.26 | -1.284 | +67.5% |
| Seasonal naive (kemarin, jam sama) | baseline | 372.6 | 513.0 | 11.73 | 11.99 | 12.09 | 0.896 | -55.1% |
| Ridge regression | pembanding | 1 007.5 | 1 357.6 | 31.72 | 31.49 | 34.19 | 0.272 | +42.7% |
| HistGradientBoosting | pembanding | 356.0 | 482.7 | 11.21 | 11.55 | 11.47 | 0.908 | -62.3% |

Baseline terkuat (dipilih dengan MAE validasi): `seasonal_naive_1d`. Perbaikan MAE LSTM: -55.1% · WAPE -55.1% · selisih MAE +205.2 kend/jam, CI 95% [+142.9, +275.0] (signifikan).
Model dengan MAE uji terendah: `hist_gradient_boosting` (356.0).

## Horizon 4h — n uji 7200 (latih 41046, validasi 7200)

| Model | Peran | MAE | RMSE | WAPE % | sMAPE % | MAPE % | R² | Δ MAE LSTM vs model ini |
|---|---|---|---|---|---|---|---|---|
| LSTM (model utama) | model | 703.7 | 1 054.8 | 21.53 | 20.92 | 21.30 | 0.583 | — |
| Persistence (volume saat ini) | baseline | 1 579.2 | 2 147.4 | 48.33 | 42.73 | 49.84 | -0.726 | +55.4% |
| Rata-rata 15 menit terakhir | baseline | 1 496.7 | 2 052.8 | 45.80 | 40.53 | 46.95 | -0.578 | +53.0% |
| Seasonal naive (kemarin, jam sama) | baseline | 379.4 | 522.7 | 11.61 | 11.87 | 11.87 | 0.898 | -85.5% |
| Ridge regression | pembanding | 1 082.1 | 1 389.7 | 33.12 | 32.12 | 38.00 | 0.277 | +35.0% |
| HistGradientBoosting | pembanding | 397.0 | 535.8 | 12.15 | 12.44 | 12.88 | 0.893 | -77.2% |

Baseline terkuat (dipilih dengan MAE validasi): `seasonal_naive_1d`. Perbaikan MAE LSTM: -85.5% · WAPE -85.5% · selisih MAE +324.3 kend/jam, CI 95% [+226.1, +436.6] (signifikan).
Model dengan MAE uji terendah: `seasonal_naive_1d` (379.4).

## Eksperimen kedua: Hybrid TMG-1012 — data latih notebook asli

Protokol identik, dataset `hybrid_traffic_7d.csv -> seri TMG-1012 (agregasi lengan, 7 hari)`. MAE uji (kend/jam):

| Horizon | n uji | LSTM | Baseline terkuat | MAE baseline | Perbaikan | Terbaik di uji |
|---|---|---|---|---|---|---|
| 15m | 1425 | 517.6 | moving_average_15 | 583.0 | +11.2% | ridge |
| 2h | 1320 | 698.6 | seasonal_naive_1d | 651.6 | -7.2% | hist_gradient_boosting |
| 4h | 1200 | 764.8 | seasonal_naive_1d | 661.4 | -15.6% | hist_gradient_boosting |

## Uji transfer: LSTM hybrid -> replay v4 (tanpa latih ulang)

| Horizon | LSTM MAE | Persistence MAE | Perbaikan |
|---|---|---|---|
| 15m | 827.7 | 435.3 | -90.1% |
| 2h | 1 297.2 | 1 761.9 | +26.4% |
| 4h | 1 005.0 | 1 579.2 | +36.4% |

## Reproduksi angka notebook lama

Protokol: notebook: 70/15/15 split by row order, window ends at i-1, target row i. Periode uji 2026-05-06 16:32:00+07:00 → 2026-05-07 19:59:00+07:00 (n=1633).

| Horizon | MAPE dihitung ulang | MAPE tersimpan | Cocok | MAE | Persistence (obs. terakhir) MAE |
|---|---|---|---|---|---|
| 15m | 21.806% | 21.8059% | ya | 540.5 | 701.5 |
| 2h | 27.034% | 27.0345% | ya | 707.0 | 1 477.1 |
| 4h | 32.492% | 32.4923% | ya | 766.3 | 1 254.9 |

Masalah protokol yang ditemukan:
- Split 70/15/15 mengikuti urutan baris file, bukan kalender: blok JKT-TMG-SIM-01 (8 Mei, data low-traffic acak yang ditambahkan di notebook) berada di set latih padahal tanggalnya sesudah set uji.
- Jendela urutan menutup di baris i-1 untuk memprediksi target baris i, sehingga horizon efektif 16/121/241 menit, bukan 15/120/240.
- Baseline 'Persistence' di notebook memakai target_volume_15m baris t-1 (= volume pada t+14), yaitu nilai masa depan; itu bukan baseline yang adil.
- Baseline hanya dihitung untuk horizon 15 menit; 2 jam dan 4 jam tidak punya pembanding.
- Target validasi di tepi split boleh jatuh di periode uji (tidak ada purging).

## Pendukung: klasifikasi penyebab bottleneck (label simulator)

| Split | macro-F1 | balanced acc | accuracy | n |
|---|---|---|---|---|
| validation | 0.7228 | 0.7658 | 0.7899 | 43200 |
| test | 0.8475 | 0.8317 | 0.8928 | 43200 |
| test · baseline majority_class | 0.071 | 0.1111 | 0.4694 | 43200 |
| test · baseline rule_based | 0.1757 | 0.2237 | 0.5598 | 43200 |

Cocok dengan metrics.json tersimpan: True.

## Pendukung: YOLOv8

Metrik **validasi** tercatat (bukan uji, tidak direproduksi di run ini): mAP50 0.9256, mAP50-95 0.5324, P/R Ultralytics 0.955/0.813, F1 (IoU≥0,5, conf 0,25) 0.8755 pada 100 gambar / 493 objek.
Detektor demo kamera: `yolo pipeline/model/yolov8m_coco.pt` (YOLOv8m pretrained COCO (Ultralytics), tidak dilatih ulang oleh tim; lisensi AGPL-3.0), kelas car, motorcycle, bus, truck, imgsz 1280. Inferensi nyata pada 123 frame CCTV replay, rata-rata kotak per frame pagi 6.04 (model tim 0.94), siang 20.08 (model tim 3.38), malam 3.29 (model tim 0.76); 392.62 ms/frame (CPU). Tanpa label acuan — bukan ukuran akurasi.

## Gambar

- `docs/evidence/d2/figures/forecast_vs_actual_15m.png`
- `docs/evidence/d2/figures/residuals_15m.png`
- `docs/evidence/d2/figures/forecast_vs_actual_2h.png`
- `docs/evidence/d2/figures/residuals_2h.png`
- `docs/evidence/d2/figures/forecast_vs_actual_4h.png`
- `docs/evidence/d2/figures/residuals_4h.png`
- `docs/evidence/d2/figures/model_vs_baseline_mae.png`
- `docs/evidence/d2/figures/lstm_error_by_hour.png`
- `docs/evidence/d2/figures/bottleneck_confusion_matrix.png`
- `docs/evidence/d2/figures/bottleneck_per_class.png`
