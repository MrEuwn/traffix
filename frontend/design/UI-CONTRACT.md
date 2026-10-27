# Kontrak UI — Traffix (hasil rombak Stitch)

Baca ini dulu sebelum menyentuh halaman. Berkas ini beku; jangan diubah.

## Stack & larangan

- React 19 + TypeScript + Tailwind 3.4 + recharts + react-leaflet. **Dilarang menambah library UI/ikon/font baru.**
- Ikon: hanya `Icon` dari `src/components/ui/icons.tsx` (SVG inline). **Tanpa emoji**, tanpa `material-symbols`, tanpa karakter Unicode sebagai ikon.
- Tanpa gradien dekoratif, tanpa blur/glassmorphism, tanpa drop shadow. Kedalaman = tangga permukaan + border 1px.
- Satu aksen interaksi: `primary` (#2F6FED). Maksimal dua warna teks per panel.
- Semua teks UI Bahasa Indonesia. Angka format id-ID: `3.982` dan `0,847` (pakai `fmtInt`/`fmtNum`/`fmtPct` dari `src/lib/format.ts`).
- Ukuran teks minimum 11px (`text-micro`/`text-caps`; `text-label` = 10px hanya untuk angka mikro seperti jam pada strip). Label kecil wajib `text-ink-muted` atau `text-ink-soft` — JANGAN pakai warna lebih gelap.
- Target sentuh semua tombol/input ≥ 44px: pakai `Btn`/`Field` (sudah `min-h-11`).
- Status TIDAK BOLEH hanya warna: setiap status/penyebab wajib ikon atau pola + label teks.
- Semua panel wajib punya state loading / kosong / galat **setinggi sama** → pakai `StateBlock` dengan `height` tetap.
- Angka live: `.num` (mono + tabular-nums), tanpa animasi count-up, tanpa `transition` pada nilai.

## Token warna (Tailwind, otomatis ikut tema gelap/terang)

```
bg-base bg-surface bg-raised bg-hover border-line border-line-strong
text-ink text-ink-soft text-ink-muted
bg-primary text-primary border-primary bg-primary-quiet hover:bg-primary-hover
text-ok text-info text-warn text-high text-crit  (+ border-*/40, bg-*/10)
```
Radius: `rounded-bar` (4) `rounded-control` (6) `rounded-card` (10) `rounded-shell` (14) `rounded-full`.
Ukuran teks: `text-caps` (11 uppercase 0.08em) `text-micro` (11) `text-cell` (12) `text-body` (13) `text-title-sm` (15) `text-title-md` (22) `text-title-lg` (28) `text-metric` (26 tabular) `text-hero` (64).
Utilitas: `.num` (angka), `.label-caps`, `.pattern-r2/.pattern-r3/.pattern-r4/.pattern-r6`, `animate-live-pulse`, `animate-skeleton`, `animate-fade-in`.
Plafon lebar halaman: `max-w-canvas` (sudah dipasang di App).

## Primitif (import dari `src/components/ui`)

```tsx
Card({children, className, pad})                     // panel dasar
PanelHead({title, sub, right, icon})                 // kepala panel label-caps + ikon
StateBlock({state:"loading"|"empty"|"error", height, emptyText, hint, onRetry})
CauseBadge({cause, confidence?, size:"sm"|"md"})     // dot+ikon+label, confidence => "· Keyakinan model 94,2 %"
Confidence({value})                                  // 0..1 -> "· Keyakinan model 94,2 %"
StatusPill({tone:"ok"|"info"|"warn"|"high"|"crit"|"idle", label, icon})
LosBadge({los})                                      // "D · Padat"
SeedBadge()                                          // "data sintetis · seed 42"
Btn({variant:"primary"|"ghost"|"danger", icon, children, ...buttonProps})
Chip({active, dot, icon, label, count, onClick})
Segmented({label, options, value, onChange})
Field({label, hint, error, ...inputProps})
KpiCard({label, value, unit, context, tone:"idle"|"ok"|"warn"|"crit", series?:number[]})
Sparkline({data, tone, height, width})
ProbabilityBar({probabilities})                      // 9 segmen; hanya 3 teratas berlabel
VehicleMixBar({mix, total})                          // R2/R3/R4/R6+ dengan pola
HeatStrip({rows:{label, cells:(string|null)[]}[], playhead:0..100, onScrub})
TableWrap({children}) Th({children,align}) Td({children,align})
Modal({open, title, sub, onClose, children, footer})
useToast() -> { push({message, action:{label, run}}) }
```

## Metadata penyebab/LOS/kelas kendaraan (`src/lib/causes.ts`)

```ts
causeMeta("hujan") -> { label:"Hujan", color:"#2F81F7", icon:"cloud-rain" }
CAUSE_ORDER        // urutan 9 kelas untuk filter/chip
losMeta("D")       // { label:"Padat", color:"#D29922" }
VEHICLE_CLASSES    // [{key:"roda_2",label:"R2",desc:"Motor",pattern:"pattern-r2"}, ...]
```
`src/lib/format.ts` tetap dipakai: `fmtInt`, `fmtNum`, `fmtPct`, `causeLabel`.

## Satuan (jangan dicampur)

- Arus & kapasitas: **smp/jam**. Jumlah kendaraan: **kend**. Antrean: **kend** dengan meter dalam tanda kurung → `62 kend (178 m)`.
- Kecepatan: **km/jam**. Siklus/tundaan: **dtk** atau **dtk/kend**. Waktu tunggu: **menit**.
- Setiap angka wajib menampilkan satuannya di header atau di sebelah angka.

## Data

- Semua data dari hook `src/hooks/useTraffixData.ts` dan `src/lib/api.ts`. **Jangan fetch langsung**, jangan hardcode angka apa pun.
- Jika model/hasil belum tersedia, tampilkan `StateBlock state="error"` + tombol "Coba lagi", bukan angka palsu.
- Angka wajib dari API apa adanya; dilarang mengarang nilai, dilarang membulatkan tanpa fungsi format.

## Batasan berkas

Ubah **hanya** berkas halaman yang ditugaskan (+ komponen di folder halaman itu bila perlu).
JANGAN ubah: `src/components/ui/*`, `src/lib/*`, `src/App.tsx`, `src/index.css`, `tailwind.config.js`, `src/hooks/*`, `src/components/layout/*`.
JANGAN jalankan build/dev server (parent akan memverifikasi). Pastikan impor yang dipakai benar-benar ada, tidak ada variabel/tipe tak terpakai (tsconfig memakai `noUnusedLocals`).
