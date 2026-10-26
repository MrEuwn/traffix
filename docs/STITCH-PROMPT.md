# Prompt Google Stitch — Rombak Total UI/UX Traffix

Cara pakai singkat:
1. Ambil API key di https://stitch.withgoogle.com/settings → **API Keys** → Create API Key.
2. Sambungkan MCP-nya ke Hermes (lihat bagian **Menyambungkan Stitch MCP** di bawah).
3. Di Stitch buat project baru: **Traffix Ops Console**.
4. Tempel **Blok Konteks + Prompt Utama** (bagian A). Hasilkan 1 layar dulu (Dashboard).
5. Lanjutkan dengan prompt per layar (bagian B), satu per satu, supaya tiap layar punya konteks penuh.
6. Ekspor hasilnya (share link / HTML / screenshot) → saya implementasikan ke React + Tailwind di repo.

---

## Menyambungkan Stitch MCP ke Hermes

Stitch menyediakan remote MCP resmi: `https://stitch.googleapis.com/mcp` (transport HTTP, auth API key).

```bash
# 1) tambahkan server (interaktif: pilih auth "header")
hermes mcp add stitch --url https://stitch.googleapis.com/mcp --auth header
#    nama header : X-Goog-Api-Key
#    nilai       : <API key Stitch kamu>

# 2) verifikasi (wajib — pastikan tool-nya terdeteksi)
hermes mcp test stitch
hermes mcp list          # harus muncul "stitch ... ✓ enabled"
```

Setelah tersambung, tool Stitch muncul sebagai `mcp_stitch_*` dan saya bisa membuat layar desain langsung dari sini.

Alternatif bila API key tidak ingin disimpan di config: OAuth Google Cloud
(`gcloud beta services mcp enable stitch.googleapis.com --project=<PROJECT_ID>` lalu `--auth oauth`),
atau MCP stdio komunitas `npx -y mcp-stitch` dengan env `GOOGLE_API_KEY`.

---

## A. Blok konteks + prompt utama (tempel apa adanya)

```
Design a complete UI/UX redesign for "Traffix" — an AI traffic-operations console used by
municipal traffic officers in Indonesia. Currently it is a dense, improvised dashboard;
we want a full redesign that looks like a professional operations product.

PRODUCT & USERS
- Users: traffic control room operators and city transport-agency analysts (traffic ops),
  plus a competition jury who must see evidence of AI model quality within 30 seconds.
- Job to be done: "tell me where the bottleneck is, why it happens, and what I should do
  next — then prove the AI is better than a rule of thumb."
- Session context: big monitor in a control room, dark room, occasional use on a laptop.

CORE DATA (design around these exact concepts, labels in Indonesian)
1. Bottleneck cause per road section (9 classes): normal, volume_puncak, perbaikan_jalan,
   hujan, banjir, kecelakaan, keramaian_event, lampu_mati, kendaraan_berat.
   Show: dominant cause, confidence %, probability distribution over all 9 classes,
   the 3 strongest signals ("waktu tunggu 0,6 menit", "kecepatan rata-rata 15,0 km/jam",
   "pangsa kendaraan berat 7,7 %"), and a suggested operator action.
2. Red-light timing averages: cycle length, average green, average red, average wait,
   average queue, average delay — aggregated "all signals", "perempatan (4-arm)" vs
   "pertigaan (3-arm)", and per intersection.
3. Road sections: 30 sections (21 signalised approaches + 9 mid-block corridors) with
   length, lanes, capacity in vehicles, capacity in SMP/hour, volume, V/C ratio,
   level of service A–F, average speed, queue, and vehicle composition
   roda 2 / 3 / 4 / 6+ (counts, shares, stacked bar, SMP equivalent).
4. Live intersections: 6 intersections (3 perempatan + 3 pertigaan) with vehicle count,
   average speed, queue length, occupancy %, signal state, weather, camera slot.
5. Model evaluation (the AI evidence screen): model vs two baselines (macro-F1,
   balanced accuracy, accuracy), per-class precision/recall/F1 with support,
   confusion matrix, feature importance, leakage guards, limitations, split protocol
   (train day 1-5 / validation day 6 / test day 7).
6. Data disclosure: every AI screen must carry a visible badge "data sintetis · seed 42".

STYLE DIRECTION
- Professional, restrained, control-room grade. Think Linear / Grafana / Vercel dashboards,
  not a colorful student project.
- Dark theme by default (also provide a light variant). Maximum two text colors plus
  semantic status colors (green/yellow/orange/red) used only for status.
- One professional sans-serif (Inter or Plus Jakarta Sans), disciplined type scale,
  12-column grid, 8-pt spacing rhythm, 10–14 px radius, subtle 1 px borders,
  low-elevation shadows. No gradients-for-decoration, no emoji as UI icons.
- Data density is a feature: tables must stay readable at 1280 px and collapse
  gracefully at 768 px (cards instead of table rows).
- Never encode meaning by color alone: pair status colors with text labels or icons.
- Accessibility: WCAG AA contrast, visible focus ring, 44 px minimum touch targets.

DELIVERABLES
Design these screens, each desktop (1440 px) and a mobile/tablet adaptation:
1. Login
2. Dashboard — the operations home
3. Live Map
4. Evaluasi Model (AI evidence)
5. Settings
Plus a shared component sheet: app shell (sidebar + topbar), KPI card, status pill,
cause badge, probability bar, signal-timing card, section table, LOS badge,
stacked composition bar, chart card, empty/loading/error states.

CONSTRAINTS FOR IMPLEMENTATION
- Will be rebuilt in React 19 + TypeScript + Tailwind CSS with recharts and react-leaflet
  (no new UI libraries, no component kit, no Figma-only widgets).
- All user-facing copy in Indonesian (short, operational, e.g. "Penyebab dominan",
  "Rata-rata waktu lampu", "Kapasitas kendaraan", "Tingkat pelayanan").
- Numbers formatted Indonesian style: 3.982 and 0,847.
- Every panel needs a loading, empty and error state; the app must remain usable when
  the AI model artifact is missing or the backend is unreachable.
```

---

## B. Prompt per layar (jalankan setelah prompt utama)

### B1. Dashboard (layar utama)
```
Dashboard for the traffic operations console. Top to bottom:
1) Slim topbar: product mark "Traffix", page tabs (Dashboard, Live Map, Evaluasi Model,
   Settings), live status pill ("Operasional" with a pulsing dot), notification bell,
   theme toggle, operator avatar + "Keluar".
2) KPI strip, 4 cards: Total kendaraan · Kecepatan rata-rata (km/jam) ·
   Simpang aktif (6) · Cuaca saat ini. Each card: large number, unit, one-line context,
   tiny sparkline. No decorative icons larger than 20 px.
3) "Diagnosis Penyebab" — the hero panel. Left: dominant cause badge + confidence +
   9-class probability bar (sorted, only non-zero classes labelled) + 3 signal chips.
   Right: ranked list of the 6 intersections with per-intersection cause, confidence and
   a 2-word operator hint. Provide a segmented control: Semua simpang / Perempatan / Pertigaan.
4) "Waktu Lampu Merah" — comparison card: three columns (Semua lampu · Perempatan ·
   Pertigaan) with cycle / green / red / wait / queue / delay, plus a compact per-intersection
   table underneath. Include a small "kenapa ini penting" one-liner.
5) "Ruas Jalan" — full-width dense table of 30 sections: search + filters (tipe ruas,
   LOS), sortable V/C column, LOS badge, and a stacked vehicle-composition bar
   (R2/R3/R4/R6+) with SMP equivalent. Sticky header, zebra rows, 11 px minimum text.
6) Right rail (collapsible): "Rekomendasi AI" approval card (current green vs recommended,
   risk %, Setujui / Simulasi / Tolak) and a system-status list.
Show how the layout behaves when the right rail is collapsed and at 1280 px.
Every AI panel carries the badge "data sintetis · seed 42".
```

### B2. Live Map
```
Live Map screen: left 2/3 is a map of Jakarta with 6 intersection markers, each colored by
dominant bottleneck cause, with a compact popover (name, cause, confidence, queue, speed,
"lihat detail"). Right 1/3 is a scrollable list synchronized with the map: selecting a row
highlights the marker and vice versa. Top of the list: filter by tipe (perempatan/pertigaan)
and by cause (9-class chips, multi-select). Bottom: a 24-hour heat strip of cause changes per
intersection. Keep the map chrome minimal (no default Leaflet look): custom pin shapes,
no popup balloons, cluster four states (normal / congestion / incident / severe).
```

### B3. Evaluasi Model (bukti AI)
```
"Evaluasi Model" screen for the AI evidence, readable by a non-engineer juror in 30 seconds:
1) Header: model name, trained timestamp, badge "data sintetis · seed 42", and a status chip
   "Artefak tersedia" / "Artefak belum ada".
2) Headline comparison: our model vs two baselines as a horizontal bar comparison on macro-F1
   (0,847 vs 0,176 vs 0,071) with a plain-language delta ("4,8x lebih baik daripada aturan").
3) Metric table: candidate / macro-F1 / balanced accuracy / accuracy, our row highlighted.
4) Per-class table: 9 classes with precision / recall / F1 / support, mini bar per row,
   and the weak classes visually flagged with a note, not hidden.
5) Confusion matrix 9x9: readable heat grid, labelled axes, diagonal emphasised, hover shows
   count and row share.
6) Feature importance: horizontal bars, top 15, plain-language names where possible.
7) Split protocol + leakage guards: a simple 3-step timeline (hari 1-5 latih, hari 6 validasi,
   hari 7 uji) and a checklist of the 17 forbidden columns.
8) Limitations: a calm, honest list — designed as first-class content, not a footnote.
```

### B4. Login + Settings
```
Login: split layout. Left: brand, one-line value proposition ("Diagnosis penyebab macet,
bukan sekadar prediksi volume"), three proof points (macro-F1 0,85 · 6 simpang · 30 ruas),
and a footer line about the synthetic dataset. Right: card with username + password,
show/hide toggle, "Masuk" CTA, inline error state, no signup link.
Settings: sections "Sistem" (backend health: model, dataset, simulation, kamera),
"Simulasi" (start/stop, tick interval, replay position), "Tampilan" (tema gelap/terang,
kerapatan tabel nyaman/padat), "Sumber data" (jalur dataset v4, badge sintetis, tombol
unduh metrics.json). Each row: label, description, control, state.
```

### B5. Komponen bersama (component sheet)
```
Component sheet: app shell (sidebar + topbar, collapsed state), KPI card, status pill
(4 levels), cause badge (9 variants, color + label), probability bar, signal-timing column,
dense table (header, zebra, hover, sorted column, empty state), LOS badge A–F,
stacked vehicle-composition bar with legend, line/area chart card, toast, modal,
loading skeleton, error panel, and a footer showing "data sintetis · seed 42".
Show each component in its default, hover, focus, disabled and loading state if applicable.
```

---

## C. Perintah penyempurnaan (dipakai saat hasil pertama kurang pas)

- "Make it denser and quieter: reduce padding by 25 %, drop the accent color to borders and
  text only, remove all decorative icons."
- "Increase contrast for the LOS and cause badges so they pass WCAG AA on the dark surface."
- "Give me the same screen for a 768 px tablet: table becomes cards, right rail becomes a
  bottom sheet."
- "Turn the probability bar into a 9-segment bar with only the top 3 classes labelled,
  the rest as a muted remainder."
- "The signal-timing card must let me compare perempatan vs pertigaan at a glance —
  try a small-multiples layout instead of three columns."
- "Show the empty, loading and error variants of this screen."
- "Produce the light theme variant of every screen, same structure."

## D. Yang saya butuhkan kembali dari Stitch
- share link tiap layar (atau ekspor HTML/screenshot),
- plus catatan: mana komponen yang berubah dari versi sekarang, dan token yang dipakai
  (warna, radius, spacing, font size) supaya saya bisa menurunkannya ke Tailwind.
