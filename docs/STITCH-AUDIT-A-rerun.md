# Audit Prompt A — putaran 2 (setelah perbaikan dijalankan via MCP)

Verifikasi ulang 27 Okt 2026 atas 6 layar kanonik, memakai ekspor HTML yang benar-benar
dipublikasikan Stitch (diunduh ke `design/stitch/v2/`, skrip `fetch_and_check.py`, keluaran `LAPORAN.txt`).

## Layar kanonik (id Stitch)

| Layar | Screen id | Catatan |
|---|---|---|
| Login | `8019019636ff43edba363628a06e5236` | "Penyempurnaan R1-R3" |
| Dashboard | `4da0c0e39fc243fc9d25f651320613c7` | "Penyempurnaan R1-R5" |
| Live Map | `3d90ec7e1c5e43bdb071c10690b32d0f` | "Penyempurnaan R1-R6" |
| Evaluasi Model | `0b056d679b8044e1b7c8c49a1895ef56` | "Koreksi Nilai & Tipografi" |
| Settings | `ad78ff6c10c74f14b93cda40eb1210e1` | "Penyempurnaan R1-R3" |
| Component Sheet | `09b7e47633894310b08333acf868ac8c` | baru, "Contoh Tampilan" |

Layar lama (5 layar versi pertama) masih ada di project — hapus manual di Stitch; MCP tidak punya tool hapus per-layar (hanya `delete_project`).

## Status butir, sebelum → sesudah

| # | Butir | Sebelum | Sesudah | Bukti pada ekspor baru |
|---|---|---|---|---|
| 1 | Persentase berlabel "Keyakinan model" | GAGAL | **LULUS** | dashboard 9x, livemap 11x |
| 2 | Satuan konsisten + tertulis | SEBAGIAN | **SEBAGIAN** | dashboard `smp/jam` 22x + `kend` 21x; livemap masih `kend` 18x tanpa `smp/jam` |
| 3 | Status bukan hanya warna (ikon/pola) | GAGAL | **LULUS** | pola `repeating-linear-gradient`/`radial-gradient` untuk R2/R3/R4/R6+ di dashboard + component sheet; ikon di tiap chip/pin |
| 4 | Teks ≥ 11 px & kontras ≥ 4,5:1 | GAGAL | **SEBAGIAN** | dashboard/settings/login/component bersih; livemap 10 kemunculan `text-[10px]`, evaluasi 14 |
| 5 | tabular-nums, tanpa count-up | LULUS | LULUS | dashboard 137x, evaluasi 8x, component 39x |
| 6 | Modal konfirmasi + Urungkan + Jejak audit | GAGAL | **LULUS** | dashboard: "Konfirmasi perubahan fase" 1x, "Urungkan" 2x, "Jejak audit" 4x + tabel fase |
| 7 | 6 simpang + penanda scroll | SEBAGIAN | SEBAGIAN | 6 nama tetap ada; penanda scroll tetap TDV dari HTML statis |
| 8 | Filter 9 penyebab + "Semua penyebab" | SEBAGIAN | **LULUS** | livemap "Semua penyebab" 2x + 9 chip berhitung |
| 9 | Heat strip "Sekarang" + scrub | GAGAL | **LULUS** | livemap "Sekarang 06:21 WIB" + `role="slider"` + `aria-valuetext` |
| 10 | Popup peta → dock + "Sematkan" | GAGAL | **LULUS** | livemap dock 360 px + "Sematkan"/"Lepas sematan" 2x |

Aturan keras:

| Butir | Sebelum | Sesudah |
|---|---|---|
| State loading/kosong/galat tinggi sama | GAGAL (kosong 0x) | **SEBAGIAN** → "Belum ada data" + "Gagal memuat data" ada di 5 layar (dashboard, livemap, settings, component); login pakai frame galat spesifik |
| Gradien dekoratif | LULUS | LULUS — 4 kemunculan gradien di dashboard/component semuanya **pola isian** swatch kelas kendaraan, bukan dekorasi |
| `#6B7885` sebagai teks | GAGAL | **LULUS** — hanya muncul sebagai definisi token `textMuted` di JSON design system yang di-inject, tidak dipakai sebagai warna teks |
| Angka id-ID | SEBAGIAN | SEBAGIAN — 25 desimal 4 digit di evaluasi semuanya format `0,NNNN` benar |
| Tanpa field/angka di luar fakta | GAGAL | **LULUS/SEBAGIAN** → lihat di bawah |
| Bisa dibuat React+Tailwind | LULUS | LULUS |

Bukti D2 (Evaluasi Model):

| Butir | Sebelum | Sesudah | Bukti |
|---|---|---|---|
| Peningkatan vs baseline | LULUS | LULUS | 0,847 / 0,831 / 0,892 vs 0,176 / 0,224 / 0,551 vs 0,071 / 0,111 / 0,469 |
| Matriks konfusi 9×9 berangka | GAGAL (dikarang) | **LULUS** | 81 sel cocok matriks `metrics.json`; header "Maks sel 20.151 · total pengujian 43.200 sampel" |
| Tabel metrik per kelas | GAGAL (dikarang) | **LULUS** | 25 nilai presisi/recall/F1 dgn 4 desimal; semuanya ∈ `metrics.json`, nol nilai asing |
| Protokol split + penjaga kebocoran | LULUS | LULUS | Hari 1–5 216.000 · Hari 6 43.200 · Hari 7 43.200 |
| "Batasan dan Kondisi Gagal" | SEBAGIAN | SEBAGIAN | 2 kemunculan "Batasan"; bobot visual hero tetap tidak dapat diverifikasi dari HTML |

## Sisa catatan jujur (belum bersih di ekspor)

1. **Livemap**: 10 × `text-[10px]` masih ada di HTML ekspor; `smp/jam` belum muncul di ekspor livemap; string galat di ekspor masih "Gagal memuat" (bukan "Gagal memuat data").
2. **Evaluasi**: 14 × ukuran < 11 px masih ada (area sidebar/nav), meski nilai angkanya sudah 100% benar.
3. **Dashboard**: 1 karakter `⚠` (U+26A0) masih ada di ekspor.

Ketiganya **sudah diperbaiki di kanvas Stitch** (DOM op dilaporkan sukses), tetapi tidak ikut terbit ke file ekspor.

## Pelajaran operasional MCP Stitch (penting untuk pengulangan)

- `edit_screens` punya dua jalur: (a) menghasilkan **layar baru** dengan `htmlCode` baru → ekspor ikut berubah; (b) **DOM op di tempat** pada layar lama (`payload_type: DomOperationEvent`) → kanvas berubah, **file ekspor tidak ikut diperbarui**.
- Timeout 300 s pada `edit_screens` **bukan** kegagalan: dashboard "timeout" ternyata tetap menghasilkan layar baru. Verifikasi dengan `list_screens`/`get_screen` sebelum mengulang.
- Cara memaksa jalur (a): minta regenerasi/re-publish layar penuh dalam satu prompt besar, seperti pada evaluasi ("Republish this screen with two corrections") dan livemap ("Penyempurnaan R1-R6").
- Cara verifikasi tercepat: `get_screen` → samakan `htmlCode.name` (hash file) dengan unduhan terakhir. Hash sama = tidak terbit.

## Keputusan terbuka sebelum Prompt B (versi repo, bukan versi dokumen)

1. Baseline nyata: `rule_based` macro-F1 0,1757 · `majority_class` 0,0710. Tidak ada "Baseline A 0,612" / "Baseline B 0,701".
2. Split nyata: hari 1–5 / 6 / 7 = 216.000 / 43.200 / 43.200 (bukan 70/15/15).
3. Fitur paling berpengaruh menurut repo: waktu tunggu 0,451 · kecepatan 0,368 · pangsa kendaraan berat 0,153 · jam 0,127 · jumlah kendaraan 0,116.
4. Layer "Editorial Control Room" sudah dipakai Stitch (display-xl 64, numeric-hero 96) tetapi belum ada di repo.
