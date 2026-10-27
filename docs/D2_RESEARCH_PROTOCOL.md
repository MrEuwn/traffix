# Protokol Riset D2 — Traffix

Dokumen ini membekukan pertanyaan riset, data, split, baseline, metrik, dan batas klaim
**sebelum** angka dibaca. Angka hasil tidak ditulis di sini; semuanya ada di
`backend/ml/forecast/artifacts/forecast_evaluation.json` dan diringkas otomatis di
`docs/pitch/D2_METRICS_BRIEF.md` oleh:

```bash
python backend/scripts/run_d2_evaluation.py
```

## 1. Pertanyaan riset utama

> Seberapa akurat LSTM meramalkan volume lalu lintas simpang (kend/jam) 15 menit, 2 jam,
> dan 4 jam ke depan dari 41 fitur yang tersedia pada waktu terbit, dibanding baseline naif
> dan model tabular pada hari uji yang sama, untuk 6 simpang yang dipantau aplikasi?

**Pengguna yang dituju:** operator pusat kendali lalu lintas (dinas perhubungan) yang ingin
tahu lebih awal simpang mana yang volumenya akan naik, supaya peninjauan waktu lampu dan
penempatan petugas bisa direncanakan. Traffix adalah **alat bantu keputusan**, bukan
pengendali lampu.

**Mengapa peramalan, bukan klasifikasi penyebab, sebagai tugas utama:** target peramalan
adalah besaran fisik yang dihitung dari data (volume pada t+h), sedangkan label penyebab
bottleneck dibuat oleh aturan simulator. Peramalan punya baseline alami yang kuat
(persistence, seasonal naive), sehingga klaim perbaikan bisa diuji dengan jujur. Klasifikasi
penyebab dan deteksi YOLO tetap dilaporkan sebagai modul pendukung.

## 2. Target dan keluaran

| Item | Definisi |
|---|---|
| Target | `volume_veh_per_hour` pada menit t+h: jumlah kendaraan 1 menit × 60, dijumlah semua lengan simpang |
| Satuan | kend/jam |
| Horizon | 15 menit, 2 jam (120 menit), 4 jam (240 menit) — tiga tugas terpisah, tiga model terpisah |
| Waktu terbit t | menit replay saat prediksi dibuat; jendela masukan = menit t−L+1 … t (inklusif) |
| Keluaran API | `GET /api/v1/predictions/{intersection_id}` → nilai per horizon, waktu target, sumber (`lstm`/`heuristic`), galat tipikal |

## 3. Data dan provenansnya

| Dataset | Peran | Status |
|---|---|---|
| `data/data_synthetic/v4/live_replay_7d.csv.gz` | **Eksperimen utama** + input replay aplikasi (6 simpang × 7 hari × 1 menit) | **Sintetis** — simulator v4, seed 42 |
| `data/data_synthetic/hybrid_traffic_7d.csv` | Eksperimen kedua (data latih notebook asli, seri TMG-1012) | **Sintetis** — simulator hybrid v3, dikalibrasi dari distribusi hitungan YOLO |
| `data/data_process/traffix_lstm_ready.csv` | Hanya untuk mereproduksi angka notebook lama | **Turunan** dari hybrid + 1.500 menit "low traffic" acak |
| `data/data_synthetic/v4/ticks_v4.csv.gz` | Klasifikasi penyebab (pendukung) | **Sintetis**; label dari aturan simulator |
| `inference_data/data_video/frames/` + metadata | Demo YOLO | **Observasi publik** — rekaman CCTV Bina Marga tol Jakarta–Tangerang, diputar ulang |
| Dataset Kaggle `traffic-road-object-detection-dataset-using-yolo` | Latih/validasi YOLO | Publik pihak ketiga; tidak disimpan di repo |

Tidak ada data lalu lintas lapangan yang diukur dan dilabeli oleh tim. Semua angka
peramalan dan klasifikasi adalah **evaluasi pada benchmark sintetis**.

**Mengapa replay v4 dipakai untuk eksperimen utama:** itulah data yang dilayani aplikasi.
Uji transfer menunjukkan LSTM yang dilatih di simulator hybrid, lalu diterapkan ke v4 tanpa
latih ulang, kalah dari persistence pada horizon 15 menit. Model yang melayani harus
dievaluasi pada distribusi yang ia layani.

## 4. Fitur dan penjaga kebocoran

- 41 fitur dari `data/data_process/feature_columns.json` (lag 1/5/15/30/60, rolling 15/60
  atas `shift(1)`, kecepatan/antrean lag 15, waktu siklik, cuaca one-hot, flag kejadian,
  hari libur).
- Satu implementasi: `backend/ml/forecast/features.py`, dipakai oleh evaluasi **dan**
  inferensi runtime.
- Pipeline gagal (exit non-nol) bila:
  - kolom `target_*` / `future_*` masuk ke input (`assert_no_leakage`);
  - fitur hasil hitung ulang dari data mentah berbeda > 1e-6 dari `traffix_lstm_ready.csv`;
  - mengubah data sesudah menit t mengubah fitur di menit ≤ t (uji gangguan masa depan);
  - split latih/validasi/uji beririsan, atau target sebuah split jatuh di split berikutnya.
- Flag kejadian (kecelakaan, perbaikan jalan, event) diasumsikan diketahui pada waktu
  terbit. Ini asumsi kuat dan dicatat sebagai batasan.

## 5. Split

Kronologis per hari kalender, berlaku untuk waktu terbit **dan** waktu target:

| Bagian | Hari | Tanggal (WIB) | Kegunaan |
|---|---|---|---|
| Latih | 1–5 | 1–5 Mei 2026 | fit scaler, fit model |
| Validasi | 6 | 6 Mei 2026 | memilih konfigurasi dan baseline terkuat |
| Uji | 7 | 7 Mei 2026 | dinilai **sekali** setelah semua pilihan dikunci |

- Sampel yang targetnya menyeberang ke hari berikutnya dibuang (*purging*).
- Jendela riwayat boleh mengambil dari hari sebelumnya, karena itu data masa lalu.
- Semua model dinilai pada baris uji yang **identik**: baris yang memiliki jendela 60 menit
  penuh dari simpang yang sama.
- Tidak ada pengacakan baris. Scaler fitur dan target hanya di-fit pada baris latih.

## 6. Model dan pembanding

| Peran | Model | Alasan |
|---|---|---|
| Model utama | LSTM `lstm_light` (LSTM64 → LSTM32 → Dense64 → Dense1), loss MAE | Arsitektur notebook tim; kecil (~45 ribu parameter), cukup untuk pola harian 1 menit tanpa GPU |
| Baseline | Persistence: volume pada t | Pembanding minimum yang wajib dikalahkan |
| Baseline | Rata-rata 15 menit terakhir (t−14 … t) | Meredam derau per menit |
| Baseline | Seasonal naive: volume kemarin pada jam target | Data 7 hari × 1 menit mendukung musim harian; hari uji punya 1 hari riwayat penuh |
| Pembanding | Ridge (α dipilih di validasi) | Model linear murah pada fitur yang sama |
| Pembanding | HistGradientBoosting (grid 4 titik di validasi) | Model tabular kuat pada fitur yang sama |

Ruang pencarian dideklarasikan sebelum dijalankan (`backend/ml/forecast/evaluate.py`):
LSTM v4 `seq_len ∈ {15, 60}`, lr 1e-3, batch 128; LSTM hybrid `seq_len ∈ {15, 60}` ×
`lr ∈ {1e-3, 5e-4}`, batch 32; early stopping (patience 8) pada loss validasi; seed 42
dan determinisme operasi TensorFlow dinyalakan.

Bila model pembanding mengungguli LSTM di data uji, hal itu dilaporkan apa adanya
(`best_on_test`). LSTM tetap model yang dilayani karena dipilih sebelum data uji dibuka.
Pertimbangan untuk mengganti model dicatat sebagai langkah berikutnya, bukan diputuskan
dari skor uji.

## 7. Metrik

- **MAE** (kend/jam): metrik utama.
- **RMSE**, **WAPE** (= Σ|galat| / Σ|aktual|), **sMAPE**.
- **MAPE** hanya untuk target ≠ 0; jumlah target 0 yang dilewati ikut dilaporkan.
- R², bias.
- **Perbaikan** = (galat baseline − galat model) / galat baseline × 100. Nilai negatif
  ditampilkan apa adanya.
- **Ketidakpastian:** CI 95% *moving-block bootstrap* (blok 60 menit, 2.000 ulangan, seed 42)
  untuk selisih MAE LSTM terhadap baseline terkuat. Baseline terkuat dipilih dengan MAE
  **validasi**.
- Rincian per horizon, per jam target, dan lima kasus terburuk.

## 8. Reproduksi angka lama

Model notebook (`LSTM Training/artifacts/`) dinilai ulang dengan protokol notebook. Lima
masalah protokol yang ditemukan dicatat di `legacy_reproduction.issues_found`:

1. Split berdasarkan urutan baris, bukan kalender.
2. Horizon efektif 16/121/241 menit, bukan 15/120/240.
3. Baseline "persistence" notebook membaca nilai masa depan.
4. Baseline hanya dihitung untuk horizon 15 menit.
5. Tidak ada *purging* di batas split.

Karena itu angka README lama (MAPE 21,8/27,0/32,5%) **tidak** dipakai sebagai klaim D2.

## 9. Penggunaan yang dimaksud dan yang tidak

**Dimaksud:**
- Prototipe alat bantu keputusan.
- Menunjukkan alur data → fitur → model → prakiraan → rekomendasi berbasis aturan yang
  ditinjau operator.

**Bukan untuk:**
- Mengendalikan lampu lalu lintas secara otomatis.
- Mengklaim akurasi pada lalu lintas Jakarta nyata.
- Mengklaim pengurangan kemacetan, emisi, waktu tempuh, atau kecelakaan.
- Mendiagnosis penyebab macet di lapangan.

## 10. Klaim yang tidak boleh dibuat

- "Akurasi X% di lalu lintas Jakarta." Yang benar: "MAE X kend/jam pada hari uji benchmark
  sintetis."
- "Traffix mengurangi kemacetan." Belum ada studi dampak.
- "Kamera live." Yang benar: replay rekaman CCTV publik.
- "Model mendiagnosis banjir/kecelakaan nyata." Labelnya berasal dari aturan simulator.
- "YOLO teruji." Yang ada adalah metrik validasi tanpa set uji, satu kelas `car`.

## 11. Kaitan SDG

**SDG 11, target 11.2** (bunyi resmi, diverifikasi di <https://sdgs.un.org/goals/goal11>):
*"By 2030, provide access to safe, affordable, accessible and sustainable transport systems
for all, improving road safety, notably by expanding public transport, with special
attention to the needs of those in vulnerable situations, women, children, persons with
disabilities and older persons."*

Jalur dampak yang **dihipotesiskan, belum diukur:** prakiraan volume yang lebih awal →
operator meninjau waktu lampu dan penempatan petugas lebih awal → antrean dan waktu tunggu
di simpang berpotensi turun. Mengukur jalur ini membutuhkan uji lapangan atau eksperimen
simulasi dengan kebijakan kontrol pembanding. Keduanya belum dilakukan.
