# D2 Q&A Brief — jawaban jujur berbasis bukti

Angka dikutip dari run evaluasi 2026-10-27 (`forecast_evaluation.json`, seed 42). Bila
evaluasi dijalankan ulang, cek ulang terhadap `docs/pitch/D2_METRICS_BRIEF.md`.

## Pertanyaan inti

**1. Masalah apa yang diselesaikan model?**
Operator dinas perhubungan perlu tahu lebih awal simpang mana yang volumenya akan naik.
Model meramalkan volume simpang (kend/jam) 15 menit, 2 jam, dan 4 jam ke depan untuk
6 simpang. Prakiraan itu dipakai sebagai alat bantu peninjauan waktu lampu oleh manusia.

**2. Kenapa LSTM, YOLO, HistGradientBoosting, dan bukan baseline sederhana?**
- *Jawaban jujur:* kami **sudah** membandingkan dengan baseline sederhana, dan hasilnya
  campuran.
  - LSTM mengalahkan persistence dan rata-rata 15 menit di semua horizon.
  - LSTM seri dengan seasonal naive pada 15 menit (+1,2%, tidak signifikan) dan kalah
    telak pada 2 jam/4 jam (MAE 578 dibanding 373; 704 dibanding 379).
  - HistGradientBoosting lebih baik dari LSTM, baik di validasi maupun di uji.
- LSTM dipilih sejak awal karena memodelkan urutan, dan dipertahankan sebagai model yang
  dilayani supaya protokolnya tidak berubah setelah data uji terlihat.
- Langkah berikutnya yang sah: seleksi per horizon di validasi, lalu uji sekali pada seed
  data baru (model card §8).
- YOLO dipakai karena bisa berjalan di CPU. Model tim (YOLOv8n, 3 juta parameter) gagal
  pada CCTV tol, sehingga demo kamera memakai YOLOv8m pretrained COCO (bukan dilatih tim)
  di 1280 px. Kami menyebutnya terus terang.
- Klasifikasi penyebab memakai HGB karena data tabular besar (216 ribu baris) dan
  kelasnya tidak seimbang.

**3. Sumber data apa, dan berapa persen sintetis?**
- 100% data latih dan uji peramalan serta klasifikasi adalah **sintetis**: simulator v4
  seed 42 dan simulator hybrid yang dikalibrasi dari hitungan YOLO.
- Satu-satunya data observasi adalah frame rekaman CCTV publik Bina Marga (123 frame),
  dan itu hanya untuk demo YOLO.
- Model YOLO tim dilatih pada dataset Kaggle publik. Detektor demo kamera adalah
  checkpoint COCO publik dari Ultralytics.

**4. Lalu lintas yang ditampilkan live atau replay?**
Replay. Dashboard memutar ulang simulasi v4 mulai hari 7 (hari uji) pukul 06:00. Panel
kamera memutar ulang frame rekaman. Keduanya diberi label "replay" atau "bukan live" di layar.

**5. Bagaimana split dan pencegahan kebocoran?**
- Split per hari kalender, berlaku untuk waktu terbit **dan** target: latih 1–5 Mei,
  validasi 6 Mei, uji 7 Mei. Sampel yang targetnya menyeberang hari dibuang.
- Scaler hanya di-fit pada data latih.
- Pipeline gagal bila:
  - kolom `target_*` masuk ke input;
  - fitur hasil hitung ulang berbeda dari data notebook;
  - mengubah data masa depan mengubah fitur masa lalu;
  - split beririsan.
- Ada 46 test otomatis (`cd backend && pytest -q`).

**6. Apa arti MAE, WAPE, dan macro-F1 di sini?**
- MAE 365 kend/jam (15 menit) berarti prakiraan rata-rata meleset 365 kend/jam dari
  volume yang terjadi, terhadap volume rata-rata sekitar 3.100 kend/jam.
- WAPE 11,7% = total galat dibagi total volume.
- Macro-F1 0,85 (penyebab bottleneck) adalah rata-rata F1 sembilan kelas dengan bobot sama,
  sehingga kelas langka ikut dihitung. Akurasi saja menyesatkan, karena "normal" mencakup
  47% data uji.

**7. Seberapa jauh lebih baik dari baseline? Kalau tidak lebih baik, kenapa dipertahankan?**
- Terhadap persistence: +16% (15m), +67% (2j), +55% (4j).
- Terhadap baseline terkuat (seasonal naive): +1,2% (tidak signifikan), −55%, −86%.
- Kami tidak mengklaim LSTM unggul.
- Nilai bagi juri: pipeline yang bisa direproduksi dan jujur, yang **menemukan** kelemahan
  itu, termasuk lima kesalahan protokol di notebook lama yang angkanya terlihat lebih bagus.

**8. Kelas atau horizon mana yang paling sering gagal, dan kenapa?**
- *Peramalan:* puncak pagi 06:00–07:00 (MAE LSTM 2j sampai 1.852, 4j sampai 2.787).
  Jendela riwayat dini hari tidak memuat sinyal kenaikan, dan model cenderung meramal
  terlalu rendah (bias negatif).
- *Klasifikasi:*
  - `keramaian_event` (F1 0,42) dan `hujan` (F1 0,63) paling lemah;
  - pertukaran terbesar: hujan→normal (2.079 menit) dan event→normal (1.015 menit),
    karena gejala lalu lintasnya mirip kondisi normal;
  - macro-F1 validasi (hari 6) hanya 0,72, dibanding 0,85 di hari uji. Kinerjanya
    bervariasi antarhari.
- *YOLO:*
  - model tim (`best.pt`) melewatkan sebagian besar kendaraan kecil di CCTV tol
    (rata-rata 1,3 kotak per frame) dan sempat menandai papan "JAKARTA" sebagai mobil;
  - detektor demo YOLOv8m COCO rata-rata 7,6 kotak per frame pada frame yang sama;
  - frame malam tetap paling lemah karena silau lampu;
  - tanpa label acuan, kedua angka itu jumlah deteksi, bukan akurasi.

**9. Apa bedanya dengan dashboard lalu lintas biasa?**
- Prakiraan multi-horizon dengan galat tipikal yang jujur.
- Diagnosis penyebab (9 kelas) dari gejala, bukan dari laporan.
- Rekomendasi berbasis aturan dengan persetujuan operator dan jejak audit.
- Setiap angka bisa dilacak ke artefak. UI menunjukkan apakah model yang melayani identik
  (sha256) dengan yang dievaluasi.

**10. Bagaimana kaitannya dengan SDG 11 target 11.2, dan dampak apa yang sudah diukur?**
- Target 11.2 berbunyi: sistem transportasi yang aman, terjangkau, mudah diakses, dan
  berkelanjutan, serta keselamatan jalan.
- Jalur dampak yang **dihipotesiskan:** prakiraan dan diagnosis lebih awal → operator
  meninjau lampu dan petugas lebih awal → antrean dan waktu tunggu berpotensi turun.
- **Belum ada dampak yang diukur.** Mengukurnya butuh uji simulasi dengan kebijakan
  pembanding atau pilot lapangan.

**11. Apa keterbatasan privasi, keadilan, keselamatan, dan deployment?**
- *Privasi:* CCTV publik beresolusi 640×480 (plat dan wajah tidak terbaca), tidak ada data
  pribadi, dan URL stream tidak disajikan.
- *Keadilan dan bias:*
  - model YOLO tim hanya mengenal mobil; detektor demo mengenal motor, tetapi belum diuji
    di jalan non-tol tempat motor dominan;
  - kinerja malam dan hujan lebih buruk;
  - data dari satu kota, satu simulator, dan 7 hari.
- *Keselamatan:* tidak mengendalikan lampu; rekomendasi berbasis aturan dan butuh
  persetujuan operator.
- *Deployment:* login hanya di sisi klien, tanpa TLS, dan ditujukan untuk demo lokal.

**12. Bukti apa yang mendukung TKT/TRL yang diklaim?**
- **TRL 3–4 (proof of concept tervalidasi di lingkungan lab/simulasi).** Buktinya:
  - pipeline evaluasi bisa direproduksi;
  - 46 test lulus;
  - container berjalan dan health check lulus;
  - 18 pemeriksaan API dari host lulus;
  - audit UI dengan Playwright lulus.
- **Belum** TRL 5+: belum ada data lapangan, belum ada integrasi dengan sistem dinas,
  dan belum ada uji pengguna.

## Pengungkapan penggunaan AI (untuk slide/deklarasi)

- Asisten AI (Claude Code) dipakai untuk:
  - mengaudit repo;
  - menulis pipeline evaluasi, test, integrasi UI, dan konfigurasi Docker;
  - menyusun draf dokumen ini.
- Semua angka berasal dari kode yang dijalankan di repo, bukan dari AI.
- Tim wajib bisa menjelaskan setiap bagian: split, baseline, metrik, dan batasan.

## Kalimat aman untuk presentasi

- "Pada benchmark sintetis kami, LSTM meleset rata-rata 365 kend/jam untuk 15 menit ke
  depan, lebih baik 16% dari persistence, tetapi tidak lebih baik dari pola kemarin.
  Untuk 2–4 jam, model gradient boosting dan pola harian lebih akurat. Kami melaporkannya
  apa adanya."
- "Kamera yang Anda lihat adalah rekaman CCTV publik yang diputar ulang. Deteksi YOLO-nya
  berjalan sungguhan di server, dan Anda bisa melihat kegagalannya."
