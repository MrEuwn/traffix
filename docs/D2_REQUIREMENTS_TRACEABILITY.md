# D2 Requirements Traceability — Traffix

Setiap baris menghubungkan satu persyaratan dengan file, kode, metrik, test, atau
screenshot yang membuktikannya. Status: ✅ terpenuhi · ⚠️ terpenuhi sebagian (lihat
catatan) · ❌ belum.

## A–J: bukti kategori D2

| # | Persyaratan | Status | Bukti |
|---|---|---|---|
| A | Masalah dan keluaran model terdefinisi | ✅ | `docs/D2_RESEARCH_PROTOCOL.md` §1–2; `GET /api/v1/model/evaluation/forecast` → `question`, `target`; UI Evaluasi Model, blok pertama |
| B | Sumber data, pengumpulan, definisi target, skema, pembersihan | ✅ | `docs/evidence/d2/DATA_QUALITY_REPORT.md` + `backend/ml/forecast/artifacts/data_quality_report.json` (6 dataset: path, sha256, baris, rentang waktu, duplikat, cek rentang, provenans, asal target); `data/data_process/data_dictionary.md` |
| C | Pilihan model dan alasan kompleksitasnya | ⚠️ | Protokol §6, model card §3. Catatan: data menunjukkan model yang lebih sederhana (seasonal naive, HGB) lebih akurat untuk horizon panjang; ini dilaporkan, tidak disembunyikan |
| D | Hasil latih, validasi, dan uji terpisah | ✅ | `forecast_evaluation.json` → `comparison[].validation` dan `.test`; `selection.lstm.grid` (MAE validasi per konfigurasi); classifier: `reproduction.json` (validasi 0,7228 / uji 0,8475) |
| E | Baseline adil pada sampel uji yang sama | ✅ | 3 baseline + 2 pembanding pada baris uji identik (`split_masks`); `tests/test_forecast_d2.py::test_baselines_only_read_the_past`, `test_v4_splits_keep_windows_inside_one_intersection` |
| F | Perbaikan terukur, atau kesimpulan jujur bila tidak ada | ✅ | Perbaikan vs persistence +16 / +67 / +55%; vs seasonal naive +1,2% (tidak signifikan) / −55% / −86%, dengan CI bootstrap; `D2_METRICS_BRIEF.md`; peringatan "MAE terendah dicapai …" di UI |
| G | Analisis galat per horizon/kelas, kondisi gagal, ketidakpastian | ✅ | `error_by_target_hour`, `worst_cases`, `incident_at_issue_mae`; gambar `lstm_error_by_hour.png`, `residuals_*.png`; per-kelas classifier dan confusion matrix (`bottleneck_confusion_matrix.png`); CI 95% bootstrap blok |
| H | Kebocoran, bias, AI bertanggung jawab, privasi | ✅ | Langkah 3 pipeline (exit non-nol bila gagal); `assert_no_leakage` untuk kedua model; model card §8 dan YOLO model card (bias motor/malam, privasi); Q&A #11 |
| I | Prototipe yang membuat input/output model dapat dipahami | ✅ | Dashboard: panel Prakiraan volume (sumber, hari split, galat tipikal) dan panel Kamera (replay, inferensi tersimpan/langsung); screenshot `frontend/screenshots/ops-*.png` |
| J | Keselarasan SDG dengan target spesifik | ⚠️ | SDG 11.2, bunyi diverifikasi di sdgs.un.org (Protokol §11). Dampak **belum diukur**, sengaja tidak diklaim |

## Rubrik 100 poin

| Kriteria | Bukti terkuat | Celah yang diakui |
|---|---|---|
| Relevansi masalah & SDG (15) | Protokol §1, §11; Q&A #1, #10 | Tidak ada data dampak |
| Inovasi & diferensiasi (20) | Prakiraan + diagnosis penyebab + rekomendasi dengan persetujuan operator; sha256 model yang melayani = yang dievaluasi | Model tunggal tidak unggul atas baseline terkuat |
| Kualitas teknis/analitis (20) | Pipeline satu perintah, lineage fitur 3e-10, uji gangguan masa depan, reproduksi notebook, 46 test | Hanya satu hari uji, satu simulator |
| Kelayakan & TRL (15) | Docker Compose sehat, 18/18 cek API, audit UI Playwright lulus; TRL 3–4 (Q&A #12) | Belum ada pilot atau data lapangan |
| Keberlanjutan & dampak (15) | Jalur dampak hipotesis yang eksplisit; langkah berikutnya di model card §8 | Belum terukur |
| Presentasi & jawaban (15) | `D2_DEMO_RUNBOOK.md`, `D2_QA_BRIEF.md`, `D2_METRICS_BRIEF.md`, gambar | Tim harus berlatih menyampaikan hasil negatif dengan percaya diri |

## Pemetaan path keluaran (bila berbeda dari spesifikasi)

| Spesifikasi | Path di repo |
|---|---|
| Laporan validasi data (JSON + MD) | `backend/ml/forecast/artifacts/data_quality_report.json`, `docs/evidence/d2/DATA_QUALITY_REPORT.md` |
| Prediksi per sampel, metrik uji, perbandingan baseline | `backend/ml/forecast/artifacts/predictions_test_{15m,2h,4h}.csv`, `forecast_evaluation.json`, `baseline_comparison.csv` (+ varian `_hybrid_tmg`) |
| Gambar | `docs/evidence/d2/figures/*.png` (10 berkas) |
| Model card | `backend/ml/forecast/model_card.md`, `backend/ml/bottleneck/model_card.md` (dibuat trainer), `backend/ml/detection/model_card.md` |
| Entry point evaluasi | `backend/scripts/run_d2_evaluation.py` (+ `backend/scripts/run_yolo_frames.py`) |
| Docker | `Dockerfile` (backend, root), `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `.dockerignore`, `frontend/.dockerignore`, `.env.docker.example`, `docs/DOCKER_DEPLOYMENT.md` |
| Generator data sintetis | Generator yang ada dipakai ulang (`data/data_synthetic/v4/generate_data_v4.py`, seed 42); tidak ada generator baru. `--regenerate-v4` tersedia di pipeline |

## Kriteria penerimaan (spesifikasi §5)

| Kriteria | Status | Catatan |
|---|---|---|
| Pertanyaan riset utama terlihat | ✅ | UI + protokol |
| Provenans/rentang/skema/baris setiap dataset | ✅ | DATA_QUALITY_REPORT |
| Pembersihan reproducible | ✅ | Aturan tertulis; tidak ada outlier yang dibuang |
| Split eksplisit | ✅ | Per hari, dengan purging |
| Guard kebocoran dijalankan | ✅ | Langkah 3 + test |
| Peringatan sintetis tampil | ✅ | Pil/badge di setiap panel model |
| Model utama benar-benar dimuat; fallback bukan inferensi | ✅ | `mode: lstm`, `matches_evaluation: true`; fallback berlabel `heuristic` |
| Baseline pada sampel identik | ✅ | |
| Metrik LSTM per horizon | ✅ | |
| Metrik classifier lengkap | ✅ | |
| YOLO berlabel validasi + provenans | ✅ | |
| Selisih absolut dan relatif dari output tersimpan | ✅ | Test `test_headline_metrics_recompute_from_saved_predictions` |
| Kegagalan dan batasan konkret | ✅ | |
| Tanpa klaim dampak nyata | ✅ | |
| Judge melihat output yang bisa dilacak | ✅ | |
| Grafik/angka dari artefak, bukan hardcode | ✅ | Test API == artefak (cek host #6) |
| Model, fallback, replay, dan artefak hilang bisa dibedakan | ✅ | StateBlock "artefak belum ada" + perintahnya |
| Demo tanpa CCTV live atau internet | ⚠️ | Semua komponen offline, **kecuali** tile peta Live Map (OpenStreetMap). Tanpa internet, peta dasar kosong sementara marker tetap tampil |
| Satuan konsisten | ✅ | kend/jam di API, UI, grafik |
| Image backend dan frontend terbangun | ✅ | `traffix-backend:competition` 4,86 GB, `traffix-frontend:competition` 77,5 MB |
| Compose valid, health check | ✅ | |
| Routing via proxy dari browser | ✅ | Audit Playwright di :8080 |
| Path model/data ada di image, tidak tertimpa volume | ✅ | Tanpa volume |
| Perintah terdokumentasi; hanya yang dijalankan ditandai lulus | ✅ | `D2_VERIFICATION_REPORT.md` |
| Test suite, build frontend, lint | ⚠️ | Test dan build lulus; lint punya error lama di file yang tidak diubah (lihat laporan verifikasi) |
