# Audit repo Traffix untuk D2 — 27 Oktober 2026

Branch kerja: `d2-competition`, dibuat dari `main` @ `2de9216`. Perubahan yang belum
di-commit (`frontend/src/pages/Login.tsx`, tombol isi akun demo) tetap dipertahankan.
Folder `Traffix.id-main/` adalah salinan proyek legacy (Dewi Azizah) yang ditaruh di root.
Folder itu dipakai hanya sebagai referensi dan tidak diubah.

Status di bawah dibagi tiga: **terverifikasi berjalan**, **ada tetapi belum terverifikasi
atau rusak** (dengan perbaikannya), dan **tidak ada**. Setiap angka di sini dihitung
ulang di sesi ini dengan perintah yang dicantumkan.

## 1. Terverifikasi berjalan

| Komponen | Bukti | Perintah |
|---|---|---|
| Test backend awal | 27 lulus sebelum perubahan | `cd backend && pytest -q` |
| Lineage fitur LSTM | 41 fitur yang dihitung ulang dari `hybrid_traffic_7d.csv` (agregasi lengan) identik dengan `traffix_lstm_ready.csv` untuk seri TMG-1012 (9.780 baris, selisih maks 3,1e-10) | langkah 3 `run_d2_evaluation.py` |
| Semantik fitur | lag = shift positif; rolling di atas `shift(1)`; target = volume pada t+15/120/240 (selisih 0) | `tests/test_forecast_d2.py` |
| Angka LSTM notebook | MAPE uji 21,806 / 27,034 / 32,492% dan MAE 540,50 / 707,00 / 766,34 direproduksi dari bobot tersimpan sampai 4 desimal | langkah 4, `legacy_reproduction` |
| Klasifikasi penyebab bottleneck | split per hari, `assert_no_leakage`, baseline majority dan rule-based, macro-F1 dan balanced accuracy | `train_bottleneck.py`, langkah 7 |
| Endpoint `/api/v1/model/evaluation` + tab Evaluasi Model | menampilkan `metrics.json` classifier | browser + API |
| Bobot YOLO `best.pt` | dimuat ultralytics 8.4 dan dijalankan pada 123 frame CCTV rekaman | `backend/scripts/run_yolo_frames.py` |

## 2. Ada tetapi belum terverifikasi, atau rusak — dan yang diperbaiki

| Temuan | Dampak | Perbaikan |
|---|---|---|
| **Inferensi LSTM runtime tidak melihat riwayat.** `ml/predictor.py` mengulang **satu** baris fitur 15 kali sebagai sekuens; fitur lag diisi jumlah kendaraan per menit, padahal model dilatih dalam kend/jam | Prakiraan di aplikasi bukan keluaran model yang dievaluasi | `ml/forecast/runtime.py`: jendela riwayat nyata dari replay, dengan fungsi fitur yang sama dengan evaluasi |
| **Fallback "dataset" menampilkan target masa depan.** Saat model tidak dimuat, API mengembalikan kolom `target_volume_*`, yaitu nilai aktual masa depan, sebagai "prediksi" | Kebocoran label di UI | Dihapus. Fallback sekarang rata-rata 15 menit terakhir dan berlabel `heuristic` |
| `confidence_score` = 0,9 / 0,72 / 0,55 ditulis langsung di kode | Angka keyakinan karangan | `null`; diganti `expected_mae` dari artefak evaluasi |
| Split notebook LSTM 70/15/15 berdasarkan urutan baris; blok JKT-TMG-SIM-01 (8 Mei) masuk set latih padahal tanggalnya sesudah set uji | Bukan split kronologis | Protokol D2 baru per hari kalender, dengan *purging* |
| Jendela notebook `X[i-L:i] → y[i]` | Horizon efektif 16/121/241 menit | Jendela inklusif t, target t+h |
| Baseline "persistence" notebook = `target_15m` baris t−1, yaitu volume t+14 | Baseline memakai masa depan | Persistence = volume pada t; ditambah rata-rata 15 menit dan seasonal naive |
| Baseline hanya untuk 15 menit | Horizon 2 jam dan 4 jam tanpa pembanding | Lima pembanding untuk setiap horizon |
| Model LSTM dilatih di simulator hybrid (1 seri), tetapi aplikasi me-replay simulator v4 (6 simpang) | Uji transfer: kalah dari persistence pada 15 menit | Eksperimen utama dilatih dan diuji pada replay v4; hybrid menjadi eksperimen kedua |
| Kolom `target_volume_*` di replay v4 = rata-rata per ruas, padahal `volume_veh_per_hour` = jumlah | Skala target tidak konsisten | Target dihitung ulang dari volume; kolom file tidak dipakai |
| Metrik classifier yang tersimpan tidak tereproduksi persis: 24 dari 43.200 prediksi berbeda (macro-F1 0,8470 dibanding 0,8473) dengan sklearn 1.9.1 yang sama. Baseline rule-based, yang deterministik dari fitur, juga bergeser (accuracy 0,5506 → 0,5598); penyebabnya komputasi fitur yang berbeda di lingkungan pelatih awal, bukan modelnya | Angka UI ≠ yang dijalankan | Dilatih ulang dengan `train_bottleneck.py` (seed 42) di lingkungan yang di-pin. Hasil: test macro-F1 0,8475, validasi 0,7228. Reproduksi di langkah 7 cocok |
| Model card classifier berisi path Windows pribadi | Perintah reproduksi tidak bisa dipakai | Diganti perintah relatif repo |
| Metrik YOLO di README disebut tanpa split | Bisa terbaca sebagai metrik uji | Diberi label **validasi** (100 gambar, juga dipakai early stopping) |
| `PredictionChart.tsx` tidak dipakai di mana pun | Prakiraan LSTM tidak tampil di UI sama sekali | Dihapus; diganti `ForecastPanel` di Dashboard |
| Hook kamera legacy memanggil `/api/v1/cameras/by-video/*`, yang tidak ada di backend; video bergantung pada Google Drive | Antarmuka CCTV legacy tidak bisa dipakai offline | Dihapus; diganti `CctvReplayPanel` berbasis frame lokal + YOLO nyata |
| Dockerfile root: `$PORT` tanpa default, `tensorflow-cpu` tanpa wheel ARM, tanpa `.dockerignore` (ikut menyalin `.venv` 1,9 GB) | Build gagal di Mac M-series | Dockerfile baru, `requirements` di-pin, `.dockerignore` |
| Lint frontend: error lama di `Settings.tsx` (`react-hooks/static-components`) dan `any` di `types/index.ts:15` | — | Belum disentuh (di luar cakupan D2); dicatat di laporan verifikasi |

## 3. Tidak ada

| Item | Status sekarang |
|---|---|
| Baseline yang adil untuk setiap horizon | Ditambahkan (persistence, MA-15, seasonal naive, Ridge, HGB) |
| Prediksi per sampel tersimpan | `backend/ml/forecast/artifacts/predictions_test_*.csv` |
| Ketidakpastian | CI bootstrap blok 60 menit |
| Laporan kualitas data | `docs/evidence/d2/DATA_QUALITY_REPORT.md` + JSON |
| Docker Compose frontend + backend | `docker-compose.yml`, `frontend/Dockerfile`, `frontend/nginx.conf` |
| **Set uji independen untuk YOLO** | **Masih tidak ada.** Dataset Kaggle tidak di repo; tidak ada label untuk frame CCTV |
| **Data lalu lintas lapangan berlabel** | **Tidak ada.** Semua evaluasi tetap sintetis |
| Uji dampak (waktu tunggu, antrean) terhadap kebijakan pembanding | Tidak ada — klaim dampak tidak dibuat |
| Jadwal kompetisi terbaru | Tidak tersedia di repo; tidak ditulis ke aplikasi atau dokumen |

## 4. Provenans data (ringkas)

Lihat `docs/evidence/d2/DATA_QUALITY_REPORT.md` untuk ukuran, hash, rentang waktu,
duplikat, dan cek rentang setiap file.

- **Sintetis:**
  - `live_replay_7d.csv.gz` dan `ticks_v4.csv.gz` (simulator v4, seed 42);
  - `hybrid_traffic_7d.csv` (simulator hybrid v3, dikalibrasi dari distribusi YOLO).
- **Turunan:**
  - `traffix_lstm_ready.csv`, termasuk 1.500 menit acak tambahan;
  - `vehicle_count.csv` (keluaran YOLO notebook; kecepatan dan densitas berupa estimasi aturan).
- **Observasi publik:** frame CCTV Bina Marga, tol Jakarta–Tangerang (rekaman Mei–Juni 2026).
  Koordinat dicari manual; cuaca dari Open-Meteo.
- **Pihak ketiga:** dataset Kaggle `boukraailyesali/traffic-road-object-detection-dataset-using-yolo`
  (lisensi mengikuti halaman Kaggle; tidak disimpan di repo).

## 5. Penghambat saat ini

1. Tidak ada data lapangan berlabel. Semua klaim kinerja terbatas pada benchmark sintetis.
2. YOLO hanya punya metrik validasi, dan pada CCTV tol model melewatkan banyak kendaraan
   kecil atau jauh. Hitungan YOLO tidak dipakai sebagai input peramalan.
3. Jadwal dan aturan waktu presentasi terbaru dari panitia tidak tersedia di repo.
