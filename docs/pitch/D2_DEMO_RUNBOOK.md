# D2 Demo Runbook — Traffix

Target: demo 7 menit yang **tidak bergantung** pada CCTV live, internet, kredensial Drive,
atau wifi ruangan. Semua angka yang ditunjukkan dibaca dari artefak
`run_d2_evaluation.py`, bukan ditulis tangan.

## A. Sehari sebelum (laptop presenter)

```bash
cd traffix
docker compose build                 # butuh internet SEKALI; sesudah itu offline
docker compose up -d
docker compose ps                    # backend + frontend: "healthy"
```

Buka http://localhost:8080 dan login `admin` / `admin123` (atau tombol **Isi akun admin**).
Cek empat hal:

1. Header Dashboard: pil **Peramal: LSTM** berwarna hijau.
2. Panel **Prakiraan volume simpang**: pil **LSTM** dan **Hari uji · tak terlihat saat latih**.
3. Tab **Evaluasi Model → Peramalan volume · utama**: blok "Model yang sedang melayani"
   bertuliskan *sha256 file model = file yang dievaluasi*.
4. Panel **Kamera CCTV**: frame berganti; tombol **Jalankan YOLO sekarang** aktif.

Lalu matikan wifi dan ulangi keempat cek itu. Harus tetap jalan.

## B. Lima menit sebelum tampil

```bash
docker compose restart backend       # replay mulai lagi dari hari 7 pukul 06:00 (hari uji)
docker compose ps                    # tunggu "healthy" (±20–40 detik)
```

Refresh browser dan buka Dashboard. Zoom browser 90–100%.

## C. Alur demo (≈ 3 menit di slot 2:15–3:30)

1. **Dashboard, 30 detik.** Tunjukkan bahwa ini replay sintetis v4 (pil *Replay sintetis v4*,
   *data sintetis · seed 42*), jam replay di sub-judul, dan KPI jaringan.
2. **Prakiraan, 45 detik.** Pada panel *Prakiraan volume simpang*:
   - volume kini dan prakiraan 15 menit / 2 jam / 4 jam dalam kend/jam;
   - waktu target dan *± galat tipikal* (MAE uji);
   - pil *Hari uji*: menit ini tidak pernah dilihat saat pelatihan.

   Ganti simpang di daftar simpang dan tunjukkan bahwa prakiraannya ikut berubah.
3. **Diagnosis & rekomendasi, 30 detik.** Panel diagnosis menampilkan klasifikasi penyebab
   (label simulator). Rekomendasi waktu hijau **berbasis aturan** dan butuh persetujuan
   operator (jejak audit). Katakan dengan jelas: *tidak mengendalikan lampu*.
4. **Kamera, 45 detik.** Panel *Kamera CCTV · deteksi kendaraan YOLOv8m*. Pilih frame
   **Siang** (deteksi paling jelas), lalu sebutkan bahwa detektornya YOLOv8m pretrained COCO,
   bukan model tim. Model tim hanya menemukan 1–4 kendaraan di frame yang sama (angka
   "model tim" di panel):
   - pil *Replay rekaman · bukan live*;
   - tekan **Jalankan YOLO sekarang**, tunggu ±4–7 detik di Docker → pil berubah menjadi
     *Inferensi langsung · xx ms*. Tekan sekali sebelum tampil supaya model sudah termuat;
   - tunjukkan jujur bahwa model melewatkan kendaraan kecil yang jauh (domain shift).
5. **Evaluasi Model, slot 3:30–4:45.** Tab *Peramalan volume · utama*:
   - kartu MAE LSTM, baseline terkuat, dan perbaikan dengan CI 95%;
   - pilih horizon 15m → 2j → 4j, termasuk tabel lima pembanding;
   - grafik aktual vs LSTM vs baseline; ganti simpang;
   - *Uji transfer*: model dari simulator lain kalah dari persistence pada 15 menit, dan
     itu alasan model dilatih pada data yang dilayani;
   - *Reproduksi angka notebook lama* beserta lima masalah protokol yang diperbaiki.

## C2. Kerangka presentasi 7 menit

Selaraskan dengan aturan waktu resmi terbaru dari panitia. Jadwal terbaru tidak tersedia
di repo.

| Waktu | Isi | Bukti di layar |
|---|---|---|
| 0:00–0:45 | Masalah: operator tidak tahu simpang mana yang akan padat dan kenapa. Pengguna: operator dishub. SDG 11.2 (bunyi resmi) | Slide; Dashboard |
| 0:45–1:30 | Kenapa dashboard biasa tidak cukup: tanpa prakiraan, tanpa penyebab, tanpa jejak keputusan. Inovasi: prakiraan + diagnosis + rekomendasi dengan persetujuan operator, setiap angka bisa dilacak | Slide |
| 1:30–2:15 | Data: 100% sintetis (simulator v4, seed 42) + CCTV publik untuk YOLO. Pembersihan, target t+h, split per hari dengan purging | `DATA_QUALITY_REPORT.md`, blok pertama Evaluasi Model |
| 2:15–3:30 | Pipeline dan demo langsung (bagian C, langkah 1–4) | Aplikasi |
| 3:30–4:45 | Model vs baseline: tabel 15m/2j/4j, CI, grafik aktual vs prediksi, galat per jam, uji transfer, reproduksi notebook lama | Tab Evaluasi Model, `figures/model_vs_baseline_mae.png` |
| 4:45–5:30 | Jalur pemakaian: prakiraan → tinjauan operator → persetujuan → audit. Hipotesis dampak, **belum diukur**. TRL 3–4 | Panel diagnosis + jejak audit |
| 5:30–6:15 | Batasan: sintetis, satu hari uji, LSTM tidak mengalahkan pola harian di 2–4 jam, YOLO model tim gagal di CCTV tol (demo memakai YOLOv8m COCO), tanpa label acuan. Langkah berikut: seleksi per horizon di validasi lalu uji pada seed baru; data lapangan | Blok "Batasan" |
| 6:15–7:00 | Penutup + cadangan waktu | — |

## D. Pemulihan bila ada masalah

| Masalah | Tindakan cepat |
|---|---|
| Halaman putih / error jaringan | `docker compose ps`; bila backend `unhealthy`: `docker compose restart backend` |
| Pil "Peramal: heuristik (fallback)" | Model tidak dimuat. Tetap tunjukkan bahwa label jujur, lalu buka tab Evaluasi (artefak tetap ada). Sesudah demo: `docker compose logs backend` |
| Tombol YOLO gagal | Frame tersimpan tetap tampil. Lanjutkan dengan *Inferensi tersimpan* (boxes dari bobot yang sama) |
| Replay sudah lewat hari 7 (pil *Hari latih · in-sample*) | `docker compose restart backend` |
| Tab Live Map tanpa peta dasar (tanpa internet) | Tile OpenStreetMap butuh internet; marker simpang tetap tampil. Lewati tab ini atau sebutkan alasannya |
| Docker mati total | Mode tanpa Docker: `cd backend && ../.venv/bin/python scripts/run_dev.py` dan `cd frontend && npm run dev` → http://localhost:5173 |
| Tidak ada laptop yang bisa menjalankan app | Pakai gambar di `docs/evidence/d2/figures/` dan `docs/pitch/D2_METRICS_BRIEF.md` |

## E. Kalimat yang harus dihindari

- ~~"Kamera live"~~ → "rekaman CCTV publik yang diputar ulang".
- ~~"Akurasi 90% di Jakarta"~~ → "MAE X kend/jam pada hari uji benchmark sintetis".
- ~~"Mengurangi kemacetan"~~ → "dirancang untuk membantu operator meninjau lebih awal;
  dampaknya belum diukur".
- ~~"Mendeteksi banjir/kecelakaan"~~ → "memulihkan penyebab yang dibangkitkan simulator".

## F. Regenerasi angka (bukan saat demo)

```bash
.venv/bin/python backend/scripts/run_d2_evaluation.py        # ±1–2 jam di CPU laptop
docker compose build backend && docker compose up -d          # bakukan artefak baru ke image
```
