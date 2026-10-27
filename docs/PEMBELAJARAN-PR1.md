# Pembelajaran dari PR #1 (D2)

Catatan ini bukan laporan. Isinya hal yang saya pelajari waktu menarik masuk PR #1
(`d2-competition` ke `main`, 22 commit, 222 berkas, +51.941 / -1.519) lalu memverifikasinya
sendiri: menjalankan 46 tes, membangun frontend, menyalakan backend, dan menjalankan audit
UI. Setiap pelajaran di bawah punya bukti berupa berkas atau angka di repo ini, bukan opini.

Dokumen pendamping: `docs/PETA-PROYEK-END-TO-END.md` (orientasi proyek) dan
`docs/evidence/d2/D2_EVALUATION_SUMMARY.md` (laporan hasil model).

## Angka yang bergeser karena pelatihan ulang

| Hal | Sebelum PR | Setelah PR | Sumber |
|---|---|---|---|
| macro-F1 uji | 0,8473 | 0,8475 | `backend/ml/bottleneck/artifacts/metrics.json` |
| balanced accuracy | 0,8311 | 0,8317 | sama |
| akurasi | 0,8916 | 0,8928 | sama |
| akurasi baseline aturan | 0,5506 | 0,5598 | sama |
| fitur paling berpengaruh | waktu tunggu 0,451 | waktu tunggu 0,4213 | sama |

Yang tidak berubah: jumlah baris latih/validasi/uji (216.000 / 43.200 / 43.200), macro-F1
baseline mayoritas 0,0710, dan macro-F1 baseline aturan 0,1757.

## Pelajaran

### 1. Angka model punya masa kedaluwarsa, tempatnya tidak

Model dilatih ulang di PR ini dan enam angka di dokumen berubah tanpa ada yang sadar.
Dokumen proyek sempat menyebut 0,8473 di tujuh tempat. Aturannya: dokumen menunjuk berkas
(`metrics.json`), bukan mengutip angka. Kalau angka harus muncul di prosa, tulis juga tanggal
latihnya, karena `trained_at` di berkas itu sekarang berbunyi `2026-10-27T08:58:49Z`.

Saya sendiri kena aturan ini: baris "fitur paling berpengaruh" di peta proyek sempat memakai
angka sebelum pelatihan ulang (0,451 / 0,368 / 0,153). Yang benar sekarang 0,4213 / 0,1604 /
0,1144. Pelajarannya bukan "hati-hati", tapi "jangan salin".

### 2. Akurasi tanpa baseline tidak berarti apa pun

Akurasi 0,8928 terlihat hebat sampai kamu tahu menebak kelas mayoritas saja sudah 0,4694.
Karena itu proyek ini memakai macro-F1 dan balanced accuracy: kelas `lampu_mati` hanya 989
baris dari 43.200, jadi model yang mengabaikannya tetap punya akurasi tinggi. Macro-F1
memaksa semua sembilan kelas dihitung sama berat.

### 3. Baseline bisa tidak adil, dan itu harus dibongkar sendiri

`docs/evidence/d2/D2_EVALUATION_SUMMARY.md` mencatat temuan atas pekerjaan tim sendiri:
baseline "persistence" di notebook asli memakai kolom target baris t-1, artinya nilai masa
depan, sehingga pembandingnya tidak sah. Baseline yang memakai masa depan selalu menang dan
selalu bohong. Menemukan cacat di baseline sendiri lebih berharga daripada menambah model.

### 4. Kalau ada fitur lag atau rolling, split acak itu kebocoran

Menit t dan t+1 hampir identik. Kalau baris diacak, tetangga waktu masuk data latih dan model
seolah cerdas. Karena itu split di proyek ini kronologis per hari: hari 1-5 latih, hari 6
validasi, hari 7 uji. Ada juga penjaga kebocoran di `features.py` yang menolak kolom label
dan kolom cuaca mentah.

### 5. Uji transfer menjawab pertanyaan yang lebih jujur daripada melatih ulang

Model peramalan dilatih di satu himpunan lalu diuji tanpa latih ulang pada replay v4. Hasilnya
campur dan dilaporkan apa adanya: horizon 15 menit LSTM MAE 827,7 vs persistence 435,3 (90,1
persen lebih buruk), horizon 2 jam menang 26,4 persen, 4 jam menang 36,4 persen. Dua hal
sekaligus: pergeseran domain itu nyata, dan pada horizon pendek tebakan "sama seperti sekarang"
sangat sulit dikalahkan. Inilah alasan klaim utama D2 ada di klasifikasi penyebab, bukan di
peramalan.

### 6. Bedakan angka validasi dari angka uji

YOLO menyebut mAP50 0,9256, tetapi itu dari 100 gambar validasi Kaggle, satu kelas `car`,
tanpa set uji independen, dan artefaknya sendiri menulis `reproduced_in_this_run: False`.
Menyebut angka validasi sebagai performa uji adalah kesalahan yang paling cepat merusak
kredibilitas di depan juri. Berkas buktinya: `backend/ml/detection/artifacts/yolo_evidence.json`.

### 7. Sistem harus jalan dalam keadaan terdegradasi, dan mengakuinya

Di mesin pengembangan TensorFlow dan ultralytics tidak terpasang. Backend tetap boot dan
semua endpoint tetap menjawab 200, tetapi `GET /api/v1/system/status` melaporkan
`ml_mode: heuristic_fallback` dan `ml_fallback_active: true`, panel peramalan melabeli dirinya
"rata-rata 15 menit terakhir, bukan model", dan tombol inferensi YOLO ikut nonaktif. Fitur
berat punya jalur cadangan, dan statusnya bisa dibaca mesin sekaligus manusia.

### 8. Determinisme dan jejak audit

Seed 42, sha256 dataset (`417780f6...`), sha256 scaler (`aec98894...`), `git_commit`, dan
`git_dirty` semuanya dicatat di dalam artefak. Nilai `git_dirty: True` di
`yolo_evidence.json` justru pelajaran mahal: artefak yang lahir dari working tree kotor tidak
bisa direproduksi dari commit mana pun. Bersihkan working tree dulu, atau catat keadaannya.

### 9. Tes adalah jaring pengaman lintas penulis

Jumlah tes naik dari 27 ke 46 (antara lain `test_forecast_d2.py` 140 baris dan
`test_model_evidence_api.py` 65 baris). Efek praktisnya: seluruh PR orang lain bisa
diverifikasi dalam beberapa menit dengan empat perintah, bukan dengan menebak.

```bash
cd backend  && ../.venv/Scripts/pytest.exe -q   # 46 tes
cd frontend && npm run build
cd frontend && npm run check:render
cd frontend && npm run check:ui                 # butuh backend dan vite hidup
```

### 10. Kontrak beku membuat dua orang bisa menggarap satu UI tanpa tabrakan

PR ini menambah tiga sub-tab di halaman evaluasi dan tiga panel di dashboard, tetapi
`tailwind.config.js` dan `src/index.css` nol perubahan, dan skrip audit
`frontend/scripts/ui_audit.py` diperluas, bukan ditimpa. Sebabnya `frontend/design/UI-CONTRACT.md`:
nama token, ukuran teks minimum 11 px, target sentuh 44 px, dan larangan ditulis eksplisit.
Kontrak menulis batas, bukan selera.

### 11. Docker mengubah "di laptopku jalan" menjadi satu perintah

`docker-compose.yml` menyiapkan dua layanan, nginx satu origin, arg `WITH_YOLO`, healthcheck,
dan artefak yang dipanggang di dalam image. Satu detail kecil yang layak dicatat: Docker
memakai `REPLAY_START_TICK` 9000, artinya hari ke-7 pukul 06:00 WIB, sedangkan konfigurasi
lokal 360 berarti hari 1 pukul 06:00. Jadi demo bisa sengaja dimulai tepat di hari uji, tanpa
menyentuh kode.

### 12. Simpan prediksi mentah, bukan cuma grafik

`predictions_test_15m.csv` dan `predictions_test_2h.csv` ikut disimpan, jadi siapa pun bisa
menghitung ulang MAE-nya sendiri. Grafik meyakinkan; berkas prediksi membuktikan.

## Empat berkas paling padat pelajaran

```
docs/evidence/d2/D2_EVALUATION_SUMMARY.md         cara melaporkan hasil jujur, termasuk mengkritik baseline sendiri
backend/ml/forecast/artifacts/forecast_evaluation.json   bentuk artefak evaluasi yang lengkap
backend/ml/detection/artifacts/yolo_evidence.json        memisahkan klaim validasi dari klaim uji
backend/ml/bottleneck/artifacts/metrics.json      model utama D2, baseline, dan penjaga kebocoran
```

## Satu aturan penutup

Kekuatan proyek ini ada di klasifikasi penyebab (0,8475 vs 0,1757) dan di kejujuran
pelaporannya. Peramalan bukan kekuatan, karena pada horizon 15 menit dia kalah dari tebakan
naif, dan itu tertulis di artefak sendiri. Kalau juri bertanya, jawab dengan angka itu apa
adanya. Angka yang diakui lebih kuat daripada angka yang dibulatkan ke atas.
