# Handoff: prompt untuk Claude → prompt untuk Stitch

Dua bagian:

- **BAGIAN 1** = tempel apa adanya ke Claude (perannya: design-prompt engineer untuk Stitch).
- **BAGIAN 2** = lampiran fakta. Tempel hanya kalau Claude minta detail teknis, atau tempel sekalian di bawah BAGIAN 1.

---

## BAGIAN 1 — prompt untuk Claude

```
Kamu bertindak sebagai design-prompt engineer. Tugasmu: menghasilkan kumpulan prompt siap-tempel
untuk Google Stitch (AI UI generator) yang akan merombak total UI/UX sebuah aplikasi web nyata.

Aturan output:
- Tulis prompt untuk Stitch dalam BAHASA INGGRIS (Stitch bekerja lebih baik dalam Inggris), tetapi
  semua teks antarmuka yang diminta HARUS string Bahasa Indonesia yang persis — sertakan di prompt.
- Setiap prompt maksimum ±500 kata: struktur berurutan (topbar, lalu tiap blok dari atas ke bawah),
  sebut grid/spacing/elevasi/badge/status, dan tutup dengan aturan warna + tipografi.
- Jangan mengarang fitur, angka, atau field data yang tidak ada di fakta di bawah. Angka contoh boleh
  dipakai sebagai placeholder visual, tetapi harus konsisten dengan fakta (contoh: macro-F1 0,847).
- Keluarkan dalam format: (1) satu prompt DESIGN SYSTEM global, (2) satu prompt per layar,
  (3) prompt komponen bersama, (4) 8–12 prompt penyempurnaan untuk iterasi (pakai `edit_screens` /
  `generate_variants` di Stitch), (5) urutan eksekusi yang disarankan.

PRODUK
- Nama: Traffix (repo: github.com/MrEuwn/traffix). Console operasional lalu lintas berbasis AI untuk
  petugas Dinas Perhubungan di Indonesia. Dipakai di ruang kendali (monitor besar, ruangan gelap),
  sesekali laptop.
- Pekerjaan pengguna: "di mana bottleneck-nya, kenapa, dan apa yang harus saya lakukan sekarang —
  lalu buktikan AI-nya lebih baik daripada aturan ambang."
- Konteks kompetisi: kategori D2 (AI & ML Challenge, International Robotics & Data Science Competition
  2026). Juri menilai: peningkatan terukur vs baseline, evaluasi tanpa kebocoran data, kompleksitas
  sepadan, keterbukaan batasan. Artinya layar "Evaluasi Model" bukan pelengkap — itu bukti utama.

TIGA PARAMETER YANG HARUS TERLIHAT JELAS
1. Penyebab bottleneck per ruas: 9 kelas — normal, volume_puncak, perbaikan_jalan, hujan, banjir,
   kecelakaan, keramaian_event, lampu_mati, kendaraan_berat. Tampilkan penyebab dominan, keyakinan,
   sebaran probabilitas 9 kelas, 3 sinyal terkuat, dan saran tindakan operator.
2. Rata-rata waktu lampu merah: siklus, hijau, merah, tunggu, antrean, tundaan — untuk "semua lampu",
   "perempatan (4 lengan)" vs "pertigaan (3 lengan)", dan per simpang.
3. Inventaris ruas jalan: 30 ruas (21 pendekat ber-lampu + 9 koridor antar-simpang) dengan panjang,
   lajur, kapasitas dalam kendaraan, kapasitas smp/jam, volume, rasio V/C, LOS A–F, kecepatan, antrean,
   dan komposisi kendaraan roda 2/3/4/6+ (jumlah, persen, bar bertumpuk, smp ekivalen).
Plus: 6 simpang terpantau (3 perempatan + 3 pertigaan) dengan jumlah kendaraan, kecepatan, antrean,
okupansi, status sinyal, cuaca; dan badge keterbukaan "data sintetis · seed 42" di setiap panel AI.

STACK & BATASAN (wajib dihormati oleh prompt Stitch)
- Akan diimplementasikan ulang di React 19 + TypeScript + Tailwind, grafik pakai recharts, peta pakai
  react-leaflet. Tanpa library UI baru, tanpa komponen yang hanya bisa dibuat di Figma.
- Semua teks antarmuka Bahasa Indonesia, pendek dan operasional ("Penyebab dominan",
  "Rata-rata waktu lampu", "Kapasitas kendaraan", "Tingkat pelayanan").
- Format angka Indonesia: 3.982 dan 0,847. Angka metrik memakai tabular-nums.
- Setiap panel punya state loading, kosong, dan galat dengan tinggi sama supaya layout tidak melompat.
- WCAG AA, fokus ring terlihat, target sentuh ≥44 px, dan status TIDAK pernah hanya warna —
  selalu ada label teks atau ikon.
- Arah visual: padat, tenang, kelas ruang kendali (bahasa Linear/Grafana/Vercel). Dua warna teks per
  panel, satu aksen interaksi, tanpa gradien dekoratif, tanpa glassmorphism, tanpa emoji sebagai ikon.

DESIGN SYSTEM YANG SUDAH ADA DI STITCH (jangan dilanggar; prompt baru harus memperluasnya)
- Nama: "Traffix Ops — Control Room" (dark, Inter, aksen #2F6FED, radius 8).
- Palet: background #0B0F14, surface #111823, surfaceRaised #18202A, surfaceHover #1E2833,
  border #223041, borderStrong #31435A, textPrimary #E6EDF3, textSecondary #9AA7B4,
  textMuted #6B7885 (hanya metadata), primary #2F6FED, primaryHover #4682F5, primaryQuiet #14243F.
- Status: ok #2EA043, info #2F81F7, warn #D29922, high #DB6D28, critical #E5534B, idle #8B949E.
- Warna 9 penyebab (dipakai sebagai pill bertinta + label, bukan blok penuh): normal #2EA043,
  volume_puncak #D29922, perbaikan_jalan #DB6D28, hujan #2F81F7, banjir #1F6FEB, kecelakaan #E5534B,
  keramaian_event #A371F7, lampu_mati #C264C8, kendaraan_berat #9E8A1F.
- Tipografi: display 30/600 · display-md 22/600 · heading 15/600 · metric 26/600 tabular ·
  body 13/1.55 · body-sm 12 · tabel 12 tabular · label-caps 10/600/0.08em uppercase (minimum 10 px).
- Radius: 4 bar/swatch · 6 kontrol · 10 kartu · 14 container besar · pill untuk badge.

LAYAR YANG HARUS DIRANCANG
1. Login (split: brand + 3 poin bukti di kiri, kartu masuk + varian status galat di kanan)
2. Dashboard operasional (topbar, KPI, hero diagnosis penyebab, kartu rata-rata waktu lampu,
   tabel ruas padat, rail kanan rekomendasi AI + status sistem)
3. Live Map (peta gelap gaya GIS, 6 pin berwarna penyebab, kartu detail tersinkron, filter tipe &
   penyebab, heat strip riwayat 24 jam)
4. Evaluasi Model (bukti D2: model vs 2 baseline, metrik per kelas, matriks konfusi 9×9, fitur
   berpengaruh, protokol split, penjaga kebocoran, batasan sebagai konten kelas satu)
5. Settings (status sistem, kontrol simulasi, tampilan, sumber data + pengingat label sintetis)
6. Component sheet (app shell, KPI card, status pill, cause badge 9 varian, probability bar,
   kartu waktu lampu, tabel padat, LOS badge, bar komposisi kendaraan, kartu grafik,
   state loading/kosong/galat)

CACAT DESAIN YANG WAJIB DIPERBAIKI DI VERSI BARU (temuan dari desain sebelumnya)
1. Persentase di samping badge penyebab tidak berlabel — beri label eksplisit ("keyakinan model").
2. Satuan bercampur pada elemen berbeda (kendaraan vs smp) — pilih satu satuan primer dan selalu
   tulis satuannya.
3. Status hanya dibedakan warna (9 penyebab, heat strip riwayat) — tambahkan ikon atau pola.
4. Mikro-label 10 px abu redup di bawah kontras 4.5:1 — naikkan ke 11–12 px dan tingkatkan kontras.
5. Metrik live belum tabular-nums — angka bergoyang tiap detik.
6. Aksi kendali sinyal ("Terapkan +12s", "Setujui Rekomendasi") tanpa konfirmasi, trade-off fase,
   undo, atau jejak audit — rancang modal konfirmasi yang menunjukkan fase mana yang kehilangan waktu.
7. Daftar simpang menampilkan 5 dari 6 tanpa tanda bisa di-scroll; label peta terpotong.
8. Chip filter penyebab hanya 6 dari 9 kelas — tampilkan sembilan atau beri label "subset".
9. Heat strip 24 jam tanpa penanda "sekarang" dan tanpa scrub — tambahkan.
10. Detail popup peta menutupi area besar peta — beri perilaku pin/dock.

FORMAT AKHIR YANG SAYA BUTUHKAN
- Prompt design system (1), prompt per layar (6, termasuk component sheet), prompt penyempurnaan (8–12).
- Daftar urutan eksekusi: layar mana dulu, apa yang harus di-approve sebelum lanjut.
- Untuk setiap prompt per layar, sertakan blok "string UI yang harus muncul persis" (Bahasa Indonesia)
  supaya tidak ada teks yang dikarang Stitch.
```

---

## BAGIAN 2 — lampiran fakta (tempel kalau Claude minta detail)

### Aplikasi yang sudah jalan

- Backend FastAPI di `:8000` (Swagger `/docs`), dashboard React+Vite di `:5173`, login demo `admin/admin123`.
- Data berasal dari simulator deterministik seed 42: 302.400 baris, 30 ruas, 6 simpang, 7 hari, resolusi 1 menit.
- Replay berjalan 2 detik per menit simulasi, mulai 06:00 WIB (jam sibuk pagi).

### Endpoint yang harus dipetakan ke layar

| Endpoint | Isi | Layar |
|---|---|---|
| `GET /api/v1/intersections` | 6 simpang: jumlah kendaraan, kecepatan, antrean, okupansi, status sinyal, cuaca | Dashboard, Live Map |
| `GET /api/v1/bottlenecks` | penyebab dominan, `causes[]` (cause, sections, share, avg_vc_ratio, avg_queue_veh, avg_wait_time_min), `per_intersection[]` (intersection_name, tipe_persimpangan, dominant_cause, confidence, probabilities 9 kelas, top3, drivers) | Dashboard, Live Map |
| `GET /api/v1/bottlenecks/{id}` | satu simpang + `history[]` 60 tick + `sections[]` | Live Map detail |
| `GET /api/v1/segments` | 30 ruas: panjang_m, jumlah_lajur, kapasitas_smp_per_jam, kapasitas_kendaraan, volume_veh_per_hour, vc_ratio, los, avg_speed_kmh, queue_length_veh, wait_time_min, kendaraan{roda_2,roda_3,roda_4,roda_6plus,total,smp_ekivalen,persen}, bottleneck_cause | Dashboard tabel ruas |
| `GET /api/v1/segments/summary` | section_count 30, approach_count 21, corridor_count 9, total_capacity_vehicles 3.982, total_capacity_smp_per_jam, total_kendaraan, avg_vc_ratio, avg_speed_kmh, los_distribution | Dashboard |
| `GET /api/v1/signals/summary?scope=all\|perempatan\|pertigaan` | cycle_length_s, avg_green_s, avg_red_s, avg_wait_time_min, avg_queue_veh, avg_delay_s, items[], per_intersection[] | Dashboard kartu waktu lampu |
| `GET /api/v1/model/evaluation` | model_name, split, metrics{macro_f1, balanced_accuracy, accuracy}, baselines{majority_class, rule_based}, per_class[], confusion_matrix, feature_importance[], leakage_guard[], limitations[] | Evaluasi Model |
| `GET /api/v1/predictions/{id}`, `/recommendations`, `/weather/current`, `/simulation/status`, `/cameras`, `/system/status` | prediksi volume 15m/2j/4j, rekomendasi durasi hijau, cuaca, status simulasi, slot kamera, health | rail kanan, Settings |

Catatan: endpoint v4 mengirim body mentah (tanpa envelope `{data:...}`); endpoint lama memakai envelope.

### Angka terverifikasi (jangan diubah)

- Macro-F1 hari uji **0,8473** · balanced accuracy 0,8311 · accuracy 0,8916
- Baseline aturan ambang 0,1757 · baseline majority class 0,0710 (jadi ±4,8× lebih tinggi)
- Pembagian: hari 1-5 latih 216.000 baris · hari 6 validasi 43.200 · hari 7 uji 43.200
- Sebaran kelas di dataset: normal 49,3 % · hujan 11,2 % · kendaraan_berat 10,8 % · banjir 7,6 % ·
  perbaikan_jalan 6,4 % · keramaian_event 4,5 % · volume_puncak 4,2 % · kecelakaan 3,6 % · lampu_mati 2,4 %
- Kapasitas total ruas 3.982 kendaraan · 21 pendekat + 9 koridor · siklus perempatan 120 s, pertigaan 80 s
- Angka per kelas (presisi/recall/F1/support), matriks konfusi, dan feature importance HARUS dibaca dari
  `GET /api/v1/model/evaluation` — jangan ditulis manual.

### Nama 6 simpang (dipakai di mock data dan label)

Simpang Meruya Utara (INT-001, perempatan 4 lengan) · Simpang Tomang (INT-002, perempatan) ·
Pertigaan Cawang (INT-003, pertigaan 3 lengan) · Pertigaan Grogol (INT-004, pertigaan) ·
Simpang Kebayoran (INT-005, perempatan) · Pertigaan Bekasi Barat (INT-006, pertigaan)

### Aset desain yang sudah tersedia

- `docs/SCHEMA-v4.md` — kontrak data lengkap (kelas, aturan label, bentuk respons API, daftar fitur terlarang).
- `docs/STITCH-PROMPT.md` — prompt Stitch versi sebelumnya (yang sudah dieksekusi: 5 layar ter-generate).
- `frontend/design/DESIGN.md` — token design system (lint bersih) + ekspor `theme.css` dan
  `tailwind.theme.json` untuk implementasi Tailwind.
- `backend/ml/bottleneck/model_card.md` — model card (protokol, metrik, analisis kesalahan, batasan).

### Kejujuran data (wajib muncul di UI)

Label penyebab berasal dari simulator dengan aturan kausal eksplisit, bukan pengukuran lapangan.
Badge "data sintetis · seed 42" harus ada di setiap panel AI dan di halaman evaluasi model, dan
daftar batasan harus tampil sebagai konten, bukan catatan kaki.
