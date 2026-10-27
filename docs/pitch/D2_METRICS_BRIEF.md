# D2 Metrics Brief (dihasilkan otomatis)

Sumber: `backend/ml/forecast/artifacts/forecast_evaluation.json` · `2026-10-27T09:05:04+00:00` · `python backend/scripts/run_d2_evaluation.py`. Jangan diedit manual — jalankan ulang perintah.

> Semua data **sintetis** (simulator, seed 42). Angka = kinerja pada benchmark simulasi, bukan lalu lintas nyata.

## Tugas utama: peramalan volume simpang (kend/jam), hari uji 7 Mei 2026

| Horizon | n uji | LSTM MAE | LSTM WAPE | Baseline terkuat | Baseline MAE | Perbaikan MAE | CI 95% selisih MAE | Terbaik di uji |
|---|---|---|---|---|---|---|---|---|
| 15m | 8550 | 364.9 | 11.7% | seasonal_naive_1d | 369.4 | +1.2% | [-33, +25] | hist_gradient_boosting |
| 2h | 7920 | 577.8 | 18.2% | seasonal_naive_1d | 372.6 | -55.1% | [+143, +275] | hist_gradient_boosting |
| 4h | 7200 | 703.7 | 21.5% | seasonal_naive_1d | 379.4 | -85.5% | [+226, +437] | seasonal_naive_1d |

Eksperimen kedua (Hybrid TMG-1012 — data latih notebook asli), MAE LSTM vs baseline terkuat: 15m 517.6 (+11.2%); 2h 698.6 (-7.2%); 4h 764.8 (-15.6%)

Uji transfer LSTM hybrid -> replay v4 tanpa latih ulang (bukti pergeseran domain): 15m LSTM MAE 827.7 vs persistence 435.3 (-90.1%); 2h LSTM MAE 1 297.2 vs persistence 1 761.9 (+26.4%); 4h LSTM MAE 1 005.0 vs persistence 1 579.2 (+36.4%)

## Pendukung

- Penyebab bottleneck (9 kelas, label simulator), hari 7: macro-F1 0.8475 · balanced acc 0.8317 vs rule-based 0.1757 / majority 0.071 (macro-F1). Direproduksi: True.
- YOLOv8 model tim (`best.pt`, 1 kelas 'car'), **validasi** 100 gambar Kaggle: mAP50 0.9256, F1 0.8755 — tidak ada set uji independen; pada CCTV tol model ini melewatkan sebagian besar kendaraan kecil/jauh.
- Demo kamera memakai YOLOv8m pretrained COCO (bukan dilatih tim), kelas mobil/motor/bus/truk: rata-rata 7.64 kotak per frame vs 1.34 untuk model tim pada 123 frame yang sama — keluaran model tanpa label acuan, bukan akurasi.

## Klaim yang TIDAK boleh dibuat

- Tidak mengklaim pengurangan kemacetan, waktu tempuh, emisi, atau kecelakaan.
- Tidak mengklaim validasi lapangan atau pengendalian lampu lalu lintas otomatis.
- Akurasi di atas tidak boleh disebut akurasi lalu lintas Jakarta nyata.
- Label penyebab bottleneck berasal dari aturan simulator, bukan kejadian lapangan.
