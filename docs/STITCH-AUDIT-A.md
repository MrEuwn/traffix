# Audit Prompt A — hasil Stitch vs checklist

Objek audit: project Stitch **Traffix Ops Console** (`projects/4707923122827099041`).
Ekspor yang diperiksa: HTML + screenshot HD dari 5 layar (login, dashboard, livemap, evaluasi, settings),
diunduh 27 Okt 2026 ke `design/stitch/`. Metode: pemeriksaan otomatis `design/stitch/audit.py`
(regex + hitung kontras WCAG) dan pembacaan visual screenshot 1600 px. Tidak ada nilai yang dikarang;
butir yang tak bisa dipastikan dari ekspor statis ditandai **tidak dapat diverifikasi (TDV)**.

Cakupan yang diminta: 6 layar. **Component sheet belum ada di project** (baru 5 layar) → butir yang
menyangkut component sheet tidak dapat dinilai.

## 1. Tabel kepatuhan — 10 cacat sebelumnya

| # | Butir | Layar | Status | Bukti |
|---|---|---|---|---|
| 1 | Persentase badge berlabel "Keyakinan model" | semua | **GAGAL** | kata "keyakinan" hanya 1× (dashboard); 39 kemunculan `x,y%` tanpa label (dashboard 9, livemap 12, evaluasi 18) |
| 2 | Satuan konsisten + tertulis | dashboard/livemap/settings | **SEBAGIAN** | "smp/jam" 3× (dashboard 2, evaluasi 1) vs "kend/kendaraan" 22× (livemap 12, dashboard 5); dashboard mencampur keduanya |
| 3 | Status tidak hanya warna (ikon/pola) | dashboard/livemap | **GAGAL** | total `<svg>` hanya 5 (dashboard 3, livemap 2) untuk 9 kelas penyebab + heat strip 6 baris + bar komposisi |
| 4 | Tidak ada teks < 11 px; kontras ≥ 4.5:1 | dashboard/livemap + token | **GAGAL** | ukuran arbitrer 9 / 9.5 / 10 / 10.5 px ada di dashboard & livemap; kontras `textMuted #6B7885` 3.95:1 di surface, dan `#4B5B6E` 2.56:1 (livemap) — dua-duanya di bawah AA teks normal |
| 5 | Metrik live tabular-nums, tanpa count-up | semua | **LULUS** | 137 kemunculan `tabular-nums`/`font-variant-numeric`; tidak ada animasi angka |
| 6 | Aksi kendali sinyal lewat modal konfirmasi + undo + jejak audit | dashboard/livemap/evaluasi | **GAGAL** | tombol `Setujui Rekomendasi`, `Tolak`, `Simulasi` ada; 0 `role="dialog"`/modal, 0 "Urungkan"; 27 dari 28 kelas tak punya tabel fase sebelum/sesudah |
| 7 | Daftar simpang 6/6 + penanda scroll + label peta utuh | livemap | **SEBAGIAN** | 6 nama simpang hadir (tomang 12, meruya 10, cawang 8, grogol 8, kebayoran 8, bekasi 7); penanda scroll & label terpotong TDV dari ekspor statis |
| 8 | Filter penyebab 9 kelas + "Semua penyebab" | livemap | **SEBAGIAN** | 9 kelas muncul sebagai chip; frasa "Semua penyebab" 0× (hanya "semua" 2×) |
| 9 | Heat strip punya penanda "Sekarang" + scrub | livemap | **GAGAL** | 0 kemunculan "sekarang"/playhead; 0 `type="range"`/slider |
| 10 | Popup peta → dock samping + "Sematkan" | livemap | **GAGAL** | 0 kemunculan "sematkan"/dock di livemap (1 kemunculan "audit" di evaluasi, tidak relevan) |

## 2. Tabel kepatuhan — aturan keras

| Butir | Status | Bukti |
|---|---|---|
| Tanpa gradien dekoratif (kata "gradient") | **LULUS** | 3 kemunculan, semuanya nama model `hist_gradient_boosting`, bukan CSS gradient |
| Tanpa blur/glassmorphism | **LULUS** | 0 `blur(` |
| Tanpa emoji sebagai ikon | **LULUS** | 0 emoji terdeteksi; ikon memakai Material Symbols |
| Satu aksen interaksi #2F6FED | **SEBAGIAN** | aksen resmi ada di 5 layar, tetapi settings memakai `#30363d` 10× (border di luar token) dan livemap memakai `#4B5B6E` 4× |
| Dua warna teks per panel | **SEBAGIAN** | token yang dipakai konsisten (E6EDF3/9AA7B4/6B7885), tetapi 6B7885 dipakai sebagai teks (di token hanya untuk metadata) |
| State loading / kosong / galat dengan tinggi sama | **GAGAL** | loading 2×, galat 8×, **kosong 0×**; tinggi sama TDV |
| Target sentuh ≥ 44 px | **TDV** | hanya 1 kemunculan `h-11`; hit area sebenarnya tidak bisa diukur dari HTML statis |
| Fokus ring terlihat | **LULUS** | 108 kemunculan `focus-visible`/`focus:ring` |
| Semua teks Bahasa Indonesia & persis | **SEBAGIAN** | judul & label Indonesia benar ("Pengaturan", "Sistem", "Simulasi", "Tampilan", "Matriks Konfusi 9×9"); ditemukan teks Inggris yang tersisa: `verified_user` (nama ikon Material, bukan teks UI) dan kata "placeholder" 6× (hanya di atribut input, aman) |
| Format angka Indonesia | **SEBAGIAN** | 129 angka format benar (0,847 / 3.982); 7 angka salah format titik-desimal (livemap 4, evaluasi 1, settings 2) |
| Tidak ada fitur/field/angka di luar fakta | **GAGAL** | tabel metrik per kelas & angka matriks konfusi di evaluasi.html tidak cocok dengan `metrics.json` (mis. F1 perbaikan_jalan di desain 0,762 vs nyata 0,968; lampu_mati 0,954 vs nyata 1,000) |
| Hanya komponen yang bisa dibuat React+Tailwind+recharts+leaflet | **LULUS** | impor eksternal hanya `fonts.googleapis.com` + `www.w3.org`; tidak ada library UI baru; grafik & peta digambar manual sehingga mudah dipetakan ke recharts/leaflet |

## 3. Tabel kepatuhan — bukti D2 di layar Evaluasi Model

| Butir | Status | Bukti |
|---|---|---|
| Peningkatan vs baseline dalam satu pandang | **LULUS** | kata "baseline" 5×, "macro" 5×; angka nyata muncul: 0,847 / 0,831 / 0,892 vs 0,176 / 0,224 / 0,551 vs 0,071 / 0,111 / 0,469 |
| Matriks konfusi 9×9 berangka | **SEBAGIAN** | "Matriks Konfusi 9×9" ada sebagai judul; 28 angka besar hadir, tetapi nilainya tidak cocok dengan `metrics.json` |
| Protokol split + penjaga kebocoran terlihat | **LULUS** | "split/latih/validasi/uji" 11×, "kebocoran/leakage" 5× |
| "Batasan model" berbobot visual setara hero | **SEBAGIAN** | section "Batasan dan Kondisi Gagal" ada dengan heading + ikon 18 px, tetapi berada di bawah blok matriks konfusi — bobot hero TDV dari ekspor statis |

## 4. Perbaikan berprioritas (prompt `edit_screens` siap tempel)

Urutan prioritas: P0 = memblokir kualitas bukti D2, P1 = melanggar aturan keras, P2 = penyempurnaan.

### P0-1 — ganti angka metrik dengan data asli (evaluasi)
Screen: `3f9c824c17fa477f90c2de28d2b4c37d`
```
Replace all per-class metric numbers and the confusion-matrix numbers with the real evaluation values.
Per-class F1: banjir 0,958; hujan 0,607; kecelakaan 0,860; kendaraan_berat 0,947; keramaian_event 0,429;
lampu_mati 1,000; normal 0,923; perbaikan_jalan 0,968; volume_puncak 0,934. Keep macro-F1 0,847,
baseline aturan 0,176, baseline majority 0,071. Add the note "Nilai dibaca langsung dari metrics.json".
Do not invent any other number. Keep the "Batasan dan Kondisi Gagal" section as the final block.
```
### P0-2 — label keyakinan pada semua persentase
Screen: `9f45b490342c4bdcbafb27f4f45ab0c7`, `e91531d12fc7447a8784ae6eb4d3f088`
```
Wherever a cause badge shows a percentage, add the label "Keyakinan model" before the number,
e.g. "Volume puncak · Keyakinan model 94,2 %". Apply to the hero diagnosis panel, the intersection
list rows, the map pins and the map detail dock. Keep the existing cause colours and pill style.
```
### P0-3 — modal konfirmasi kendali sinyal
Screen: `9f45b490342c4bdcbafb27f4f45ab0c7`
```
Add a confirm modal for the "Setujui Rekomendasi" action. Content: title "Konfirmasi perubahan fase",
a before/after phase table (Pendekat, Hijau saat ini, Hijau usulan, Selisih), a line naming the phase
that loses time, a note field "Catatan operator", a checkbox-free footer with "Terapkan" (primary) and
"Batal" (ghost), a warning line "Simulasi pada data sintetis — tidak mengubah lampu nyata", and after
applying a toast "Perubahan diterapkan · Urungkan" plus an entry in "Jejak audit".
```
### P0-4 — dock peta menggantikan popup
Screen: `e91531d12fc7447a8784ae6eb4d3f088`
```
Replace the floating map popup with a right-side detail dock: fixed 360 px column inside the map area,
full height, with dock header, the intersection detail, the three signal lines and the action
"Terapkan +12 s". Use "Sematkan" / "Lepas sematan" as the pin toggle. Keep the existing right filter
column; when the dock is open, the filter column collapses to a narrow rail.
```
### P1-1 — ukuran teks minimum 11 px + kontras
Screen: semua (`a941520cbd754129975e094b668fe7f4`, `9f45b490342c4bdcbafb27f4f45ab0c7`, `e91531d12fc7447a8784ae6eb4d3f088`, `3f9c824c17fa477f90c2de28d2b4c37d`, `6096f5c0d7aa4045a53335df3b3c0098`)
```
Raise every arbitrary text size below 11 px to at least 11 px; label-caps uses 11 px / 600 / 0.08em.
For all small labels use textSecondary #9AA7B4 (never #6B7885 and never #4B5B6E) on surfaces, so
contrast stays above 4.5:1. Replace the off-token border #30363D with border #223041.
```
### P1-2 — ikon/pola untuk status selain warna
Screen: `e91531d12fc7447a8784ae6eb4d3f088`, `9f45b490342c4bdcbafb27f4f45ab0c7`
```
Add an icon or fill pattern to every colour-coded element: one distinct glyph per bottleneck cause
(9), a diagonal/dot/cross fill per vehicle class in the composition bar (R2/R3/R4/R6+), and a shape
key per row in the 24-hour history strip. Text labels must stay visible next to each colour.
```
### P1-3 — state kosong + tinggi tetap
Screen: semua
```
Add explicit loading, empty and error states to every panel, all with the same fixed height:
loading shows three skeleton bars, empty shows "Belum ada data" plus one explanatory line, error shows
"Gagal memuat data" plus "Coba lagi". The layout must not shift when live data arrives.
```
### P2-1 — penanda "Sekarang" dan scrub pada heat strip
Screen: `e91531d12fc7447a8784ae6eb4d3f088`
```
Add a vertical "Sekarang" marker to the 24-hour history strip at the current replay position, allow
arrow-key scrubbing with role="slider" and aria-valuetext in Indonesian time ("06:21 WIB"),
and show the selected block's cause, confidence and queue on hover/focus.
```
### P2-2 — chip "Semua penyebab" + 9 kelas
Screen: `e91531d12fc7447a8784ae6eb4d3f088`
```
Make the cause filter a complete list: a leading chip "Semua penyebab" followed by all nine cause chips
with their colour dot, icon and count, e.g. "Banjir / genangan (2)". Use multi-select styling and keep
the existing type filter above it.
```
### P2-3 — satuan tunggal + angka id-ID
Screen: `9f45b490342c4bdcbafb27f4f45ab0c7`, `e91531d12fc7447a8784ae6eb4d3f088`
```
Use one primary unit per metric and always print it: arus and capacity in "smp/jam", vehicle counts in
"kend", queues in "kend" with metres in brackets. Fix every number to Indonesian formatting
(0,847 and 3.982), including inside tables, chips and the map dock.
```

## 5. Risiko saat implementasi React/Tailwind

| Elemen Stitch | Risiko | Alternatif |
|---|---|---|
| Peta gelap gaya GIS dengan poligon jalan | react-leaflet tidak bisa membuat gaya ini tanpa tile/gambar kustom | gambar layer SVG statis Jakarta di bawah `MapContainer` dengan `L.CRS.Simple`, atau `Polyline`/`Polygon` dari GeoJSON ringkas yang di-commit |
| Grafik sparkline & heat strip (SVG inline Stitch) | sulit dipertahankan sebagai markup | recharts `AreaChart` mini untuk sparkline; heat strip sebagai grid `div` + tooltip sendiri (bukan library grafik) |
| Tabel padat 12 kolom + sticky header | banyak kolom bertabrakan di 1280 px | `overflow-x-auto` di container tabel, kolom Komposisi roda jadi bar mini, sembunyikan kolom Panjang dan Lajur di bawah 1280 px |
| Modal konfirmasi + toast + jejak audit | tidak ada komponen siap pakai | `role="dialog"` + fokus trap manual (20 baris), toast sebagai `aria-live="polite"` di context kecil |
| Ikon Material Symbols | perlu font tambahan | ganti ke SVG inline 16/18 px (satu file `icons.tsx`) supaya tidak menambah dependensi |
| `text-[9px]`/`text-[10px]` di ekspor | melanggar aturan dan tidak terbaca | token `text-[11px]` + `leading-tight`; audit lint khusus mencari ukuran < 11 px |
| Animasi replay 1 detik | layout shift | semua angka `tabular-nums` + lebar kolom tetap; tanpa animasi nilai |

## 6. Keputusan terbuka sebelum Prompt B

1. **Component sheet belum digenerate** (layar ke-6). Perlu `generate_screen_from_text` dulu, atau Prompt B
   membangun komponen bersama dari token tanpa acuan visual.
2. **Angka placeholder di dokumen Prompt B tidak ada di ekspor maupun repo**: "Baseline A · aturan ambang 0,612",
   "Baseline B 0,701", dan rasio split 70/15/15. Kenyataan repo: baseline = `rule_based` 0,1757 dan
   `majority_class` 0,0710; split = hari 1-5 / 6 / 7 (216.000 / 43.200 / 43.200 baris). Prompt B harus
   memakai versi repo, dan baris "Baseline B" tidak perlu dibuat.
3. **Daftar fitur berpengaruh di Prompt B** ("Okupansi, Kecepatan, Antrean, Volume, Cuaca") tidak cocok dengan
   `feature_importance` repo (waktu tunggu 0,451; kecepatan 0,368; pangsa kendaraan berat 0,153; jam 0,127;
   jumlah kendaraan 0,116). Pakai daftar repo.
4. **Layer "Editorial Control Room"** (display-xl 64, numeric-hero 96) disebut di brief tetapi tidak ada di
   design system project maupun di ekspor; perlu dikonfirmasi apakah memang mau ditambahkan.
