# Peta proyek Traffix, dari nol sampai sekarang

Dokumen ini ditulis untuk kamu, bukan untuk juri. Isinya: apa yang sebenarnya sedang
dibangun, bagaimana potongan-potongannya nyambung, apa yang sudah jadi, apa yang belum,
dan ke mana harus buka kalau mau mengubah sesuatu. Baca bagian 2 dulu kalau kamu cuma
punya lima menit; baca berurutan kalau sudah lama tidak menyentuh repo ini.

Terakhir diperbarui: 27 Oktober 2026.

---

## 1. Apa yang sedang dibangun dan kenapa

Repo lama (`dewiazizah968/Traffix.id`) sudah pernah dilombakan dan isinya dua model:
YOLOv8 untuk mendeteksi kendaraan dari CCTV, dan LSTM untuk meramal volume lalu lintas
15 menit / 2 jam / 4 jam ke depan, plus backend FastAPI dan dasbor React. Yang tidak ada
di sana: penjelasan *kenapa* lalu lintas tersendat. Ramalan volume menjawab "berapa
kendaraan nanti", bukan "apa yang bikin macet sekarang".

Versi ini (`github.com/MrEuwn/traffix`) menjawab pertanyaan kedua. Setiap ruas jalan di
setiap menit diberi satu dari sembilan label penyebab, lalu sebuah classifier memprediksi
label itu dari keadaan lalu lintas fisik saja. Klaim lomba kategori D2 bertumpu pada satu
hal yang bisa dibandingkan angkanya: macro-F1 classifier versus dua baseline.

Tiga parameter yang kamu minta ditambahkan sudah ada semua:

1. penyebab bottleneck (9 kelas, misalnya perbaikan jalan, hujan, banjir, lampu mati),
2. rata-rata waktu lampu merah per tipe simpang, dan rata-rata gabungan semua simpang,
3. daftar ruas jalan: ada berapa, kapasitasnya berapa kendaraan, dan pecahan roda 2/3/4/6+.

Satu hal yang harus kamu hafal sebelum ngobrol dengan siapa pun: **label penyebab di
dataset v4 berasal dari aturan simulator, bukan dari pengamatan lapangan.** UI-nya
mengumumkan itu lewat badge `data sintetis · seed 42`, model card menuliskannya, dan
`metrics.json` juga. Jangan pernah menjualnya sebagai akurasi lapangan; yang dijual adalah
"isyarat fisik cukup untuk memulihkan mekanisme penyebab". Itu jujur dan tetap kuat.

## 2. Peta cepat: berkas yang paling sering dibuka

| Kalau kamu mau... | Buka ini |
|---|---|
| paham kontrak data dan label | `docs/SCHEMA-v4.md` |
| mengubah cara data v4 dibuat | `data/data_synthetic/v4/generate_data_v4.py` |
| melatih ulang classifier | `backend/ml/bottleneck/train_bottleneck.py` |
| lihat angka model apa adanya | `backend/ml/bottleneck/artifacts/metrics.json` |
| angka peramalan & deteksi | `backend/ml/forecast/artifacts/`, `backend/ml/detection/artifacts/` |
| jalan pakai Docker | `docker-compose.yml` |
| bahan presentasi yang sudah disiapkan | `docs/pitch/D2_DEMO_RUNBOOK.md`, `docs/pitch/D2_METRICS_BRIEF.md`, `docs/evidence/d2/` |
| tahu batasan model untuk juri | `backend/ml/bottleneck/model_card.md` |
| menambah endpoint | `backend/app/routes/` |
| menyetel perilaku runtime | `backend/core/config.py` dan `backend/.env` |
| mengubah tampilan | `frontend/src/components/ui/index.tsx` (primitif) lalu halaman di `frontend/src/pages/` |
| aturan desain yang tidak boleh dilanggar | `frontend/design/UI-CONTRACT.md` |
| mengganti warna atau font | `frontend/tailwind.config.js` + `frontend/src/lib/ThemeContext.tsx` |
| membuktikan UI masih benar | `frontend/scripts/ui_audit.py` |

## 3. Alur end-to-end, satu tarikan napas

```
generate_data_v4.py
   └─ ticks_v4.csv.gz        302.400 baris section-menit, 51 kolom, seed 42, 7 hari
   └─ intersections.csv      6 simpang (3 perempatan, 3 pertigaan)
   └─ sections.csv           30 ruas (21 pendekat + 9 koridor)
   └─ live_replay_7d.csv.gz  60.480 baris untuk replay lama
            │
            ▼
train_bottleneck.py  (46 fitur, hanya keadaan sensor + lag/rolling)
   └─ split temporal: hari 1-5 latih (216.000) · hari 6 validasi (43.200) · hari 7 uji (43.200)
   └─ artifacts/bottleneck_classifier.joblib + metrics.json
   └─ macro-F1 uji 0,8475  vs  aturan 0,1757  vs  majority 0,0710
            │
            ▼
FastAPI (backend/app)
   └─ tick engine membaca dataset, cursor berjalan 1 menit per detik
   └─ /api/v1/bottlenecks, /segments, /segments/summary, /signals/summary
   └─ /api/v1/model/evaluation            (klasifikasi penyebab)
   └─ /api/v1/model/evaluation/forecast   (peramalan volume, termasuk uji transfer ke v4)
   └─ /api/v1/model/evaluation/detection  (validasi YOLO + inferensi potongan gambar)
   └─ /api/v1/cameras/frames, /forecast, /frames/{id}/image, /frames/{id}/infer
   └─ endpoint lama tetap hidup: /intersections, /predictions, /recommendations, /weather, /simulation
   └─ semua endpoint analitik menerima ?tick= supaya semua panel menampilkan detik yang sama
            │
            ▼
React 19 + Tailwind (frontend)
   └─ Dashboard      : KPI, diagnosis penyebab, prakiraan volume simpang, replay rekaman CCTV,
                       kotak terdeteksi, waktu lampu, 6 simpang, tabel 30 ruas, heat strip, jejak audit
   └─ Live Map       : peta + dock detail 360 px, filter 9 penyebab
   └─ Evaluasi Model : tiga sub-tab, Penyebab bottleneck (bukti D2 utama) · Deteksi YOLO ·
                       Peramalan volume; semua angka dibaca dari berkas artefak
   └─ Settings       : status sistem, kontrol simulasi, tema, sumber data
```

Angka yang harus konsisten di ketiga lapisan: 6 simpang, 30 ruas, kapasitas total 3.982
kendaraan, siklus 120 detik (perempatan) dan 80 detik (pertigaan), macro-F1 0,8475.

## 4. Kronologi pengerjaan

Fase 0, recon. Repo lama dikloning, isinya diperiksa: YOLOv8 + LSTM + FastAPI + React,
dataset lama hanya satu simpang empat lengan, YOLO satu kelas (`car`). Tiga parameter yang
diminta belum ada satu pun. Keputusan penting di sini: repo baru (bukan lanjut di repo lama)
supaya versi lomba sebelumnya tetap utuh.

Fase 1, kontrak dibekukan lebih dulu. `docs/SCHEMA-v4.md` ditulis sebelum menulis kode
produksi: sembilan kelas penyebab, urutan prioritas label, daftar fitur terlarang (fitur yang
membocorkan jawaban), bentuk JSON tiap endpoint. Alasannya sederhana: kalau kontraknya
berubah di tengah, model, backend, dan UI akan saling menyalahkan.

Fase 2, data. `generate_data_v4.py` menghasilkan dataset 7 hari per menit. Fase ini yang
paling banyak kalibrasi ulang: satuan kapasitas awalnya memakai smp sehingga antrean mentok
di 250 kendaraan sepanjang hari, waktu tunggu sempat 51 menit (tidak masuk akal), dan
kecepatan 59 km/jam sehari penuh. Perbaikannya ada di bagian 11.

Fase 3, model. 46 fitur, split temporal (bukan acak, supaya tidak ada kebocoran antar hari),
penjaga kebocoran yang menolak kolom label dan kolom cuaca mentah. Hasil latihan pertama
macro-F1 uji 0,8473, lalu menjadi 0,8475 setelah dilatih ulang di fase 6. Dua kelas memang
lemah dan itu dibiarkan apa adanya: `keramaian_event` dan `hujan`, karena gejalanya
bertumpang tindih dengan antrean jam sibuk.

Fase 4, backend. Endpoint v4 ditambahkan tanpa merusak yang lama. `REPLAY_START_TICK`
disetel 360 (06:00 WIB) supaya demo dibuka saat jam sibuk pagi, bukan tengah malam.

Fase 5, frontend. Versi pertama UI masih pakai inline style dan font Poppins. Lalu dirombak
total: rancangan visual dikerjakan terpisah lebih dulu dan diaudit terhadap aturan keras,
baru ditulis ulang ke React. Token warna, tipografi Inter + JetBrains Mono, kumpulan primitif
bersama, dan empat halaman ditulis ulang di atas primitif itu. Sekarang ada dua skrip yang
menjaga hasilnya (bagian 8).

Fase 6, modul pendukung dan kemasan lomba (dikerjakan di cabang `d2-competition`, masuk lewat
PR #1). Tiga hal ditambahkan: modul peramalan LSTM dengan halaman evaluasinya sendiri
(termasuk uji transfer ke dataset v4), modul deteksi YOLO beserta artefaknya dan panel
inferensi potongan gambar CCTV, serta Docker Compose supaya seluruh tumpukan bisa dijalankan
dengan satu perintah. Halaman Evaluasi Model dipecah jadi tiga sub-tab: penyebab bottleneck,
deteksi YOLO, dan peramalan volume. Classifier penyebab dilatih ulang, angkanya bergeser tipis
(macro-F1 0,8475). Berkas pendukung presentasi juga masuk: `docs/pitch/` dan `docs/evidence/d2/`.

Fase 7, berkas lomba. Belum selesai, lihat bagian 12. Deck-nya sudah punya template resmi
IRDSC 2026 di Canva (13 halaman) yang sebagian baru terisi identitas tim.

## 5. Kontrak yang sudah dibekukan (jangan diubah sembarangan)

Sembilan kelas penyebab: `normal`, `volume_puncak`, `perbaikan_jalan`, `hujan`, `banjir`,
`kecelakaan`, `keramaian_event`, `lampu_mati`, `kendaraan_berat`.

Urutan prioritas pelabelan penting: kejadian yang lebih spesifik menang atas yang umum
(lampu mati dan banjir menang atas volume puncak, dan seterusnya). Urutan penuhnya ada di
`docs/SCHEMA-v4.md`.

Aturan satuan, dicampur = salah dan juri akan menanyakannya:

| Besaran | Satuan | Contoh penulisan |
|---|---|---|
| arus, kapasitas | `smp/jam` | 3.982 smp/jam |
| jumlah kendaraan | `kend` | 1.284 kend |
| antrean | `kend` + meter dalam kurung | 62 kend (178 m) |
| kecepatan | `km/jam` | 24,6 km/jam |
| siklus, tunda | `dtk` | hijau 28,6 dtk dari siklus 120 dtk |
| waktu tunggu | menit | 0,58 menit |

## 6. Angka final, dan di mana angkanya hidup

| Hal | Nilai | Sumber kebenaran |
|---|---|---|
| macro-F1 model | 0,8475 | `artifacts/metrics.json`, disajikan `/api/v1/model/evaluation` |
| balanced accuracy | 0,8317 | sama |
| akurasi | 0,8928 | sama |
| baseline aturan | 0,1757 / 0,2237 / 0,5598 | sama |
| baseline majority | 0,0710 / 0,1111 / 0,4694 | sama |
| baris uji | 43.200 (hari 7) | sama |
| F1 per kelas | lampu_mati 1,0000 · perbaikan_jalan 0,9652 · banjir 0,9549 · kendaraan_berat 0,9511 · volume_puncak 0,9375 · normal 0,9241 · kecelakaan 0,8487 · hujan 0,6259 · keramaian_event 0,4204 | sama |
| dataset v4 | 302.400 baris, 51 kolom | `data/data_synthetic/v4/` |
| kapasitas total | 3.982 kendaraan | `/api/v1/segments/summary` |
| fitur paling berpengaruh | waktu tunggu 0,4213 · pangsa kendaraan berat 0,1604 · kecepatan 0,1144 · jumlah kendaraan 0,0645 · jam 0,0645 | `metrics.json` |
| deteksi YOLO | mAP50 0,9256 · F1 0,8755 pada validasi 100 gambar Kaggle (satu kelas `car`), tanpa set uji independen | `docs/pitch/D2_METRICS_BRIEF.md`, `/api/v1/model/evaluation/detection` |

Angka di tabel ini pernah bergeser setelah model dilatih ulang, jadi jangan hafal angkanya:
hafalkan tempat angkanya hidup. Kalau angka di UI berbeda dengan `metrics.json`, UI yang salah.
Angka 0,8473 dan 0,8916 yang tertulis di dokumen desain lama adalah hasil latihan sebelum PR #1.

## 7. Menjalankan dari nol

```bash
git clone https://github.com/MrEuwn/traffix.git
cd traffix

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # atau backend/requirements.txt kalau cuma mau API

cd backend
cp .env.example .env               # default sudah cocok untuk susunan folder ini
python scripts/run_dev.py          # http://localhost:8000, dokumentasi di /docs
```

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Masuk dengan `admin` / `admin123`. Login ini murni di sisi browser, backend tidak punya
endpoint autentikasi. Kalau API ada di host lain, tulis
`VITE_API_URL=http://host:port` di `frontend/.env`.

Ingin data dibuat ulang (butuh beberapa menit):

```bash
python data/data_synthetic/v4/generate_data_v4.py
python backend/ml/bottleneck/train_bottleneck.py
```

## 8. Cara memverifikasi, dan artinya

```bash
cd backend  && pytest -q          # 46 tes: model, peramalan, endpoint, integrasi
cd frontend && npm run build      # tsc -b + bundel produksi
cd frontend && npm run lint
cd frontend && npm run check:render   # render panel tanpa browser, cek angkanya dari API nyata
cd frontend && npm run check:ui       # audit Playwright aplikasi yang benar-benar jalan
docker compose up --build             # jalur lain: seluruh tumpukan termasuk ML di dalam image
```

`check:ui` (butuh backend dan vite hidup) membuka browser sungguhan lalu gagal kalau: ada
state galat terlihat, font UI bukan Inter, utilitas angka bukan JetBrains Mono, ada teks di
bawah 11 px, ada emoji dipakai sebagai ikon, ada tombol lebih kecil dari target sentuh
wajar, modal konfirmasi atau toast "Urungkan" tidak jalan, atau ada halaman meluber
horizontal di 1600 / 1440 / 1280 px. Skrip ini juga menelusuri sub-tab Evaluasi Model dan
panel baru di Dashboard. Alamat bisa diganti lewat env `TRAFFIX_URL` (Docker memakai
`http://localhost:8080`). Screenshot-nya jatuh di `frontend/screenshots/` dan folder itu
sengaja tidak masuk git.

Satu hal yang wajib dicek sebelum demo: `GET /api/v1/system/status`. Di mesin ini
`ml_mode` bernilai `heuristic_fallback` dan `ml_fallback_active` bernilai true, karena
TensorFlow belum dipasang di `.venv`. Artinya panel peramalan menampilkan rata-rata
bergerak 15 menit terakhir, bukan keluaran LSTM, dan tombol inferensi YOLO langsung ikut
nonaktif tanpa `ultralytics`. Docker Compose memasang keduanya di dalam image, jadi lewat
jalur itu jatuh ke fallback tidak akan terjadi.

## 9. Urutan demo lima menit

1. Buka `http://localhost:5173`, masuk `admin` / `admin123`.
2. Dashboard: tunjuk baris KPI (arus, kecepatan, antrean, waktu tunggu), lalu panel diagnosis
   dengan badge penyebab dan tulisan "Keyakinan model". Sebut satu angka dengan satuannya.
3. Tab Evaluasi Model: ini puncaknya, dan sekarang ada tiga sub-tab. Buka "Penyebab
   bottleneck", tunjukkan macro-F1 0,8475 versus baseline aturan 0,1757, matriks konfusi 9×9,
   lalu blok batasan yang sengaja dibuat sebesar hero. Sub-tab "Deteksi YOLO" menyebut
   mAP50 0,9256 dengan jujur bahwa itu validasi, bukan set uji. Sub-tab "Peramalan volume"
   menampilkan MAPE per horizon beserta uji transfer ke dataset v4.
4. Tab Live Map: klik satu simpang, dock kanan terbuka, sebut "Sematkan" dan filter
   "Semua penyebab" beserta sembilan kelasnya.
5. Balik ke Dashboard, tekan "Setujui Rekomendasi", biarkan modal konfirmasi fase muncul,
   klik Terapkan, tunjukkan toast "Urungkan" dan entri baru di Jejak audit.

Empat hal yang jangan didemokan: video CCTV asli (butuh kredensial Google Drive yang tidak ada
di repo), panel peramalan sebagai keluaran LSTM (cek `ml_mode` dulu, di mesin ini masih
fallback heuristik), angka heat strip sebagai "24 jam penuh" (API hanya menyimpan 60 tik
terakhir), dan klaim akurasi lapangan (labelnya dari simulator).

## 10. Kalau mau mengubah sesuatu

| Mau ubah | Sentuh | Ingat |
|---|---|---|
| warna, font, jarak | `tailwind.config.js`, `ThemeContext.tsx`, `index.css` | warna lewat `rgb(var(--c-*) / <alpha-value>)` supaya tema terang tetap jalan |
| komponen bersama | `frontend/src/components/ui/index.tsx` | jangan sebarkan `{...rest}` setelah `className`, itu menimpa seluruh kelas dasar |
| label/ikon kelas penyebab | `frontend/src/lib/causes.ts` | satu sumber untuk badge, chip, pin peta, dan heat strip |
| isi halaman | `frontend/src/pages/*.tsx` | patuhi `frontend/design/UI-CONTRACT.md`, lalu jalankan `npm run check:ui` |
| endpoint baru | `backend/app/routes/` | tambahkan juga hook di `frontend/src/hooks/useTraffixData.ts` |
| aturan label penyebab | `docs/SCHEMA-v4.md` dulu, baru generator dan model | mengubah kontrak berarti melatih ulang dan menyetel ulang `metrics.json` |
| perilaku replay | `backend/core/config.py` | `REPLAY_START_TICK` menentukan jam buka demo |

## 11. Masalah yang pernah muncul, dan obatnya

| Gejala | Penyebab sebenarnya | Obat |
|---|---|---|
| UI bilang "backend tidak merespon" padahal backend hidup | `VITE_API_URL` tidak pernah dimuat, repo cuma punya `.env.production` | tulis `frontend/.env`, default di `src/lib/api.ts` diarahkan ke `localhost:8000` |
| halaman putih, dev server balas 500 di `index.css` | vite dev sudah jalan sebelum `tailwind.config.js` diubah, jadi masih memegang config lama | restart dev server, build produksi tidak terpengaruh |
| antrean mentok 250 dan okupansi 80% seharian | kapasitas dihitung dalam smp padahal antrean disimpan dalam kendaraan | kapasitas kendaraan dipakai untuk antrean, `SAT_FLOW_VEH_PER_LANE`, `DEMAND_SCALE` dan `CORRIDOR_LINK_FACTOR` dikalibrasi ulang |
| waktu tunggu 51 menit | dihitung dari `queue/discharge` | pakai tundaan sinyal Webster/HCM, ambang di `features.py` ikut disesuaikan |
| validasi macro-F1 cuma 0,18 | fitur diurut per `(section_id, tick)` tapi label tidak ikut terurut, jadi fitur dan label tidak sepasang | urutkan data sebelum split |
| `ts.dt.dayofweek` error | pandas 3.x mengganti nama properti | `ts.dt.day_of_week` |
| `frontend/src/lib/` tidak ikut ter-commit tanpa pesan | `.gitignore` punya aturan `lib/` | tambah pengecualian `!frontend/src/lib/` |
| peta penuh tulisan "API KEY REQUIRED" | tile CARTO sekarang menuntut API key | ganti ke tile OpenStreetMap tanpa key, digelapkan lewat filter CSS `.map-dark` |
| badge Settings berbahasa Inggris | enum backend ditampilkan mentah | dipetakan ke "Operasional" / "Terbatas" |
| header tabel terpotong jadi "TUNGGU MENI" | tabel lebih lebar dari panelnya | header dipendekkan, kolom Panjang dan Lajur disembunyikan di bawah 1280 px |
| input login jadi kotak putih 20 px | `Field` menyebar `{...rest}` setelah `className`, jadi kelas pemanggil menimpa kelas dasar | `className` di-destructure dan digabung paling akhir |
| edit desain di kanvas tidak ikut terbit ke berkas ekspor | jalur penyuntingan hanya mengubah kanvas, berkas ekspor tidak diterbitkan ulang | minta ekspor ulang layar penuh dari penyedia alat desain |

## 12. Yang belum selesai

Berkas lomba masih jadi prioritas pertama dan masih kosong: ringkasan dua halaman, deck
presentasi, dan pernyataan orisinalitas. Template deck resmi IRDSC 2026 sudah ada di Canva
(13 halaman) dan identitas tim sudah masuk, tetapi sebagian besar halaman masih placeholder.
Bahan pendukungnya sudah tersedia di `docs/pitch/` dan `docs/evidence/d2/`, termasuk tangkapan
layar dan angka yang sudah diverifikasi.

Repo masih perlu dipastikan publik atau privat, dan halaman detail per simpang belum ada
(klik simpang baru membuka dock, belum ada halaman sendiri). Hijau per pendekat tidak
tersedia dari simulator, jadi tabel fase memakai fase bottleneck plus baris agregat dan
mengatakannya apa adanya. Heat strip terisi dari 60 tik terakhir, bukan 24 jam. Replay lama
masih menggambarkan empat simpang sementara dataset v4 punya enam, jadi tampilan
rekomendasi lama dan analitik v4 belum sepenuhnya sejajar.

Di mesin lokal ini, dua hal membuat demo belum memakai model penuh: TensorFlow dan
`ultralytics` belum terpasang di `.venv`, sehingga peramalan jalan sebagai heuristik dan
inferensi YOLO langsung nonaktif. Pilihannya memasang keduanya (unduhannya besar) atau
menjalankan lewat Docker Compose yang sudah menyiapkan semuanya di dalam image.

## 13. Istilah

`smp` satuan mobil penumpang, satuan arus yang menyamakan motor dan truk ke mobil.
`kend` jumlah kendaraan apa adanya. `V/C` rasio volume terhadap kapasitas, di atas 1 berarti
permintaan melampaui kapasitas. `LOS` tingkat pelayanan A sampai F, dari lancar sampai macet.
`perempatan` simpang empat lengan (siklus 120 dtk), `pertigaan` simpang tiga lengan
(80 dtk). `macro-F1` rata-rata F1 semua kelas tanpa memandang jumlah sampel, dipakai karena
kelas di sini timpang. `balanced accuracy` akurasi yang ditimbang per kelas. `MAPE` rata-rata
persentase kesalahan ramalan. `tick` satu menit waktu simulasi; satu detik nyata sama dengan
satu menit simulasi.
