# D2 Verification Report — 27 Oktober 2026

Lingkungan: macOS (Apple Silicon), Python 3.11.16 venv (`.venv/`), Node 26, Docker 29.6
(native arm64). Hanya perintah yang benar-benar dijalankan yang ditandai LULUS.

## Ringkasan

| # | Perintah | Hasil | Ringkasan keluaran |
|---|---|---|---|
| 1 | `cd backend && pytest -q` (sebelum perubahan) | LULUS | 27 passed |
| 2 | `python backend/ml/bottleneck/train_bottleneck.py` | LULUS | exit 0; val macro-F1 HGB 0,7228 / MLP 0,695 → HGB; test macro-F1 0,8475 |
| 3 | `python backend/scripts/run_yolo_frames.py` (detektor demo YOLOv8m COCO @1280 + `best.pt` sebagai pembanding) | LULUS | 123 frame; rata-rata 7,64 kotak per frame (model tim 1,34); 393 ms/frame di CPU Mac. Run awal dengan `best.pt` @640 (0,94 / 3,38 / 0,76 kotak) diganti setelah inspeksi visual menunjukkan sebagian besar kendaraan terlewat |
| 4 | `python backend/scripts/run_d2_evaluation.py` | LULUS | exit 0, 2.385 detik. 9 langkah; lineage 3,1e-10; uji gangguan masa depan 0; reproduksi notebook cocok; reproduksi classifier cocok; 10 gambar |
| 5 | `cd backend && pytest -q` (akhir) | LULUS | **46 passed** (termasuk hitung ulang MAE dari CSV prediksi, API artefak hilang, mode fallback) |
| 6 | `cd frontend && npx tsc -b --noEmit` | LULUS | tanpa error |
| 7 | `cd frontend && npm run build` | LULUS | built; peringatan ukuran chunk > 500 kB (bukan error) |
| 8 | `cd frontend && npx eslint .` | GAGAL (error lama) | 21 error, **semuanya di file yang tidak diubah**: `Settings.tsx` (16, `react-hooks/static-components`), `ui/index.tsx` (2), `AuthContext.tsx` (1), `ThemeContext.tsx` (1), `types/index.ts:15` (`any` lama). Sebelum perubahan 25; 4 hilang bersama hook kamera lama yang dihapus. File baru dan yang diubah bersih |
| 9 | `docker compose config -q` | LULUS | |
| 10 | `docker compose build` (dengan cache) | LULUS | `traffix-backend:competition` 4,86 GB, `traffix-frontend:competition` 77,5 MB |
| 11 | `docker compose up -d` (percobaan pertama) | GAGAL → diperbaiki | backend `PermissionError: /app/backend/logs/traffix.log` (user non-root). Fix: Dockerfile meng-`chown` `backend/logs`. Rebuild → kedua container `healthy` |
| 12 | Cek host lewat Nginx `:8080` (`verify_stack.py`, 18 cek) | LULUS | 18/18: SPA, `/health`, mode `lstm`, sha256 cocok, API evaluasi == artefak (semua MAE), seri per simpang, reproduksi classifier, YOLO berlabel validasi, prediksi `lstm` di hari uji, `confidence_score` null, katalog 123 frame, gambar beranotasi/mentah, **inferensi YOLO langsung di container** (1 kotak, sama dengan tersimpan), path traversal → 404 |
| 13 | `TRAFFIX_URL=http://localhost:8080 python frontend/scripts/ui_audit.py` (Playwright Chromium) | LULUS | 4 halaman + 2 sub-tab evaluasi; string wajib ada; tidak ada state galat atau permintaan API gagal; modal konfirmasi + toast urungkan; klik "Jalankan YOLO sekarang" → "Inferensi langsung"; tanpa luber horizontal di 1600/1440/1280/**390** px. Screenshot: `frontend/screenshots/` |
| 14 | Stabilitas restart: hash `GET /model/evaluation/forecast` sebelum dan sesudah `docker compose restart backend` | LULUS | identik (`cc9e4581…`); replay mulai ulang di 2026-05-07 06:01 (hari uji) |
| 16 | Setelah detektor diganti: `run_d2_evaluation.py --refresh-yolo --skip-yolo`, `pytest -q`, `docker compose build && up`, 18 cek host, audit UI | LULUS | laporan YOLO diperbarui tanpa melatih ulang LSTM; 46 passed; 18/18 (inferensi langsung di container 11 kotak = tersimpan; ±4 detik per frame setelah model termuat); audit UI lulus (pembatalan unduhan gambar frame saat autoplay tidak dihitung sebagai kegagalan API) |
| 15 | `docker compose build --no-cache` + `docker compose up -d --force-recreate` + 18 cek ulang | LULUS | build exit 0 dari nol; backend dan frontend `healthy`; 18/18 cek host lulus |

## Angka yang diverifikasi (dari artefak run #4)

| Model | Set | n | Metrik | Baseline / pembanding | Direproduksi di sesi ini |
|---|---|---|---|---|---|
| LSTM 15m | uji hari 7, replay v4, sintetis | 8.550 | MAE 364,9, WAPE 11,7% | seasonal naive 369,4 (+1,2%, CI [−32,8; +25,0]); persistence 435,3 (+16,2%); HGB 274,3 | ya (dilatih ulang, seed 42) |
| LSTM 2h | idem | 7.920 | MAE 577,8, WAPE 18,2% | seasonal naive 372,6 (−55,1%); persistence 1.761,9 (+67,2%); HGB 356,0 | ya |
| LSTM 4h | idem | 7.200 | MAE 703,7, WAPE 21,5% | seasonal naive 379,4 (−85,5%); persistence 1.579,2 (+55,4%); HGB 397,0 | ya |
| LSTM (eksperimen kedua, hybrid TMG-1012) | uji hari 7 | 1.425 / 1.320 / 1.200 | MAE 517,6 / 698,6 / 764,8 | baseline terkuat 583,0 / 651,6 / 661,4 | ya |
| LSTM notebook lama | protokol notebook | 1.633 | MAPE 21,806 / 27,034 / 32,492% | — | ya, cocok sampai 4 desimal (tidak dipakai sebagai klaim) |
| Classifier penyebab (HGB) | uji hari 7, ticks v4, label simulator | 43.200 | macro-F1 0,8475, bal. acc 0,8317, acc 0,8928 | rule-based 0,1757; majority 0,071 | ya (dilatih ulang; validasi 0,7228) |
| YOLOv8n | **validasi** Kaggle | 100 gambar / 493 objek | mAP50 0,926, mAP50-95 0,532, F1 0,876 | tidak ada | **tidak**; diambil dari output notebook tersimpan |

## Kondisi kegagalan yang diuji

| Kondisi | Cara | Hasil |
|---|---|---|
| Model tidak dimuat | `test_model_status_reports_fallback_not_lstm_when_models_absent`, `test_without_history_the_heuristic_is_labelled_and_never_reads_targets` | mode `heuristic_fallback`, `matches_evaluation: false`, sumber `heuristic`, tidak membaca target |
| Artefak evaluasi hilang | `test_forecast_evaluation_missing_artefact_is_explicit` | `available: false` + perintah reproduksi; seri → 404 |
| Deteksi YOLO hilang | `test_frames_catalogue_and_missing_detections` | `available: false` + perintah |
| Frame atau horizon tidak dikenal, path traversal | test + cek host #12 | 404 |
| Image tanpa ultralytics | Tidak dijalankan (build `WITH_YOLO=false` tidak diuji) | Kode: `live_inference_available: false` dan 503 dengan alasan; UI menonaktifkan tombol dan menampilkan alasannya |
| Tanpa internet | Tidak diuji dengan memutus jaringan | Runtime tidak memanggil layanan eksternal, kecuali tile peta Live Map (OSM) dan tombol BMKG yang memang tidak dipakai di demo |

## Docker no-cache

`docker compose build --no-cache` dijalankan sesudah semua perubahan kode runtime. Exit 0.
Kedua image dibangun ulang dari nol (unduh paket ulang), lalu `up --force-recreate` → kedua
container `healthy`, dan `verify_stack.py` kembali 18/18 lulus. Image
`traffix-backend:latest` (3,08 GB) adalah sisa build manual di awal sesi dan tidak dipakai
compose. Hapus dengan `docker image rm traffix-backend:latest` bila tidak diperlukan.

## Yang tidak dijalankan atau tidak bisa diverifikasi

- Evaluasi ulang YOLO: dataset Kaggle tidak ada di repo dan butuh kredensial.
- `npm run check:render`: tidak dijalankan.
- `npm run check:ui` lewat `package.json` memakai path Windows (`../.venv/Scripts/python.exe`); skrip yang sama dijalankan langsung (#13).
- pytest di **dalam** container: ultralytics menaikkan `httpx` ke 0.28.1, sehingga `TestClient` Starlette 0.37 kemungkinan gagal di image. Runtime API tidak terpengaruh. Test resmi dijalankan di venv.
- Uji pengguna atau juri, dan uji di jaringan ruangan kompetisi.
