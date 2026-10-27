---
version: alpha
name: Traffix
description: Control-room grade interface for AI traffic bottleneck diagnosis. Dark-first, dense, restrained — one accent colour, semantic status only.
colors:
  background: "#0B0F14"
  surface: "#111823"
  surfaceRaised: "#18202A"
  surfaceHover: "#1E2833"
  border: "#223041"
  borderStrong: "#31435A"
  textPrimary: "#E6EDF3"
  textSecondary: "#9AA7B4"
  textMuted: "#6B7885"
  primary: "#2F6FED"
  primaryHover: "#4682F5"
  primaryQuiet: "#14243F"
  statusOk: "#2EA043"
  statusInfo: "#2F81F7"
  statusWarn: "#D29922"
  statusHigh: "#DB6D28"
  statusCritical: "#E5534B"
  statusIdle: "#8B949E"
  causeNormal: "#2EA043"
  causeVolume: "#D29922"
  causeRoadwork: "#DB6D28"
  causeRain: "#2F81F7"
  causeFlood: "#1F6FEB"
  causeAccident: "#E5534B"
  causeEvent: "#A371F7"
  causeSignalDown: "#C264C8"
  causeHeavy: "#9E8A1F"
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  display-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  heading-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.3
  metric-lg:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.01em"
    fontFeature: "tnum"
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.08em"
  table-cell:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.35
    fontFeature: "tnum"
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.4
rounded:
  xs: 4px
  sm: 6px
  md: 10px
  lg: 14px
  pill: 999px
spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
components:
  app-shell:
    backgroundColor: "{colors.background}"
    textColor: "{colors.textPrimary}"
  sidebar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textSecondary}"
    rounded: "{rounded.sm}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textPrimary}"
    rounded: "{rounded.md}"
    padding: 16px
  card-header:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textSecondary}"
    typography: "{typography.label-caps}"
  kpi-value:
    textColor: "{colors.textPrimary}"
    typography: "{typography.metric-lg}"
  kpi-label:
    textColor: "{colors.textMuted}"
    typography: "{typography.label-caps}"
  text-body:
    textColor: "{colors.textPrimary}"
    typography: "{typography.body-md}"
  text-secondary:
    textColor: "{colors.textSecondary}"
    typography: "{typography.body-sm}"
  table-header:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.textSecondary}"
    typography: "{typography.label-caps}"
  table-row:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textPrimary}"
    typography: "{typography.table-cell}"
  table-row-hover:
    backgroundColor: "{colors.surfaceHover}"
    textColor: "{colors.textPrimary}"
  badge-neutral:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.textSecondary}"
    rounded: "{rounded.pill}"
    padding: 4px
  badge-ok:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusOk}"
    rounded: "{rounded.pill}"
    padding: 4px
  badge-warn:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusWarn}"
    rounded: "{rounded.pill}"
    padding: 4px
  badge-critical:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusCritical}"
    rounded: "{rounded.pill}"
    padding: 4px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.sm}"
    padding: 10px
    height: 36px
  button-primary-hover:
    backgroundColor: "{colors.primaryHover}"
    textColor: "#FFFFFF"
  button-ghost:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textSecondary}"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.sm}"
    padding: 10px
    height: 36px
  button-ghost-hover:
    backgroundColor: "{colors.surfaceHover}"
    textColor: "{colors.textPrimary}"
  input:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.textPrimary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 10px
    height: 36px
  tab-active:
    backgroundColor: "{colors.primaryQuiet}"
    textColor: "{colors.textPrimary}"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.sm}"
    padding: 8px
  tab-idle:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.textMuted}"
    typography: "{typography.heading-sm}"
    rounded: "{rounded.sm}"
    padding: 8px
  probability-bar-track:
    backgroundColor: "{colors.surfaceRaised}"
    rounded: "{rounded.xs}"
    height: 8px
  probability-bar-fill:
    backgroundColor: "{colors.causeFlood}"
    rounded: "{rounded.xs}"
    height: 8px
  cause-badge-normal:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeNormal}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-volume-puncak:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeVolume}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-perbaikan-jalan:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeRoadwork}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-hujan:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeRain}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-banjir:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeFlood}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-kecelakaan:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeAccident}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-keramaian-event:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeEvent}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-lampu-mati:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeSignalDown}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  cause-badge-kendaraan-berat:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.causeHeavy}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 4px
  los-badge-a:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusOk}"
    rounded: "{rounded.xs}"
    padding: 4px
  los-badge-e:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusHigh}"
    rounded: "{rounded.xs}"
    padding: 4px
  los-badge-f:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusCritical}"
    rounded: "{rounded.xs}"
    padding: 4px
  live-status-pill:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusOk}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.pill}"
    padding: 6px
  info-banner:
    backgroundColor: "{colors.surfaceRaised}"
    textColor: "{colors.statusInfo}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 12px
  empty-state:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.statusIdle}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 24px
  chart-series-primary:
    backgroundColor: "{colors.primary}"
    height: 2px
  chart-series-warn:
    backgroundColor: "{colors.statusWarn}"
    height: 2px
---

## Overview

Traffix is a traffic control room console: an operator watches it on a large monitor
in a dim room and must answer three questions in seconds — where is the bottleneck, why,
and what do I do next. The interface therefore behaves like an instrument panel, not a
marketing site. Density is a feature; decoration is a cost.

Two rules dominate everything below. First: **one accent colour**, `primary`, reserved for
interaction (active tab, primary button, selected row, focus ring). Colour never carries
meaning on its own — every status colour is paired with a text label or an icon.
Second: **hierarchy comes from typography, spacing and surface elevation**, not from
colour variety.

## Colors

- **background (#0B0F14):** the app canvas — near-black, low chroma, so data glows.
- **surface / surfaceRaised:** three-step elevation ladder for cards, table headers and
  popovers. Elevation is a lighter surface plus a 1 px `border`, never a drop shadow.
- **textPrimary / textSecondary / textMuted:** exactly two text weights in practice —
  primary for values, secondary for labels and supporting lines; `textMuted` is for
  metadata only (timestamps, units, hints), never for content the operator must read.
- **primary (#2F6FED):** interaction only — active tab, primary action, selected row,
  focus ring, chart series 1.
- **Semantic status:** `statusOk` (normal, LOS A-B), `statusInfo` (informational, rain),
  `statusWarn` (building congestion, LOS D), `statusHigh` (LOS E, roadwork),
  `statusCritical` (LOS F, accident), `statusIdle` (no data).
- **Cause palette (9 classes):** each bottleneck cause owns one colour used *as a tint with
  a text label*, never as a full-saturation fill. `causeFlood` is deliberately deeper blue
  than `causeRain` so the two rain-family causes remain distinguishable, and
  `causeSignalDown` (magenta) is the only purple-family token, reserved for lampu_mati.

## Typography

Inter throughout (JetBrains Mono only for identifiers: section ids, file paths, rule names).
Numbers in metrics and tables use `font-variant-numeric: tabular-nums` so columns align and
values do not jitter while the replay advances. `display-lg` is for page titles, `metric-lg`
for KPI values, `label-caps` for panel headers and table headers — uppercase, letterspaced,
`textSecondary`. Body copy stays at 13 px; table cells at 12 px. Nothing below 10 px.

## Layout

12-column grid, 8 px base rhythm, 16 px card padding, 12 px gap between cards, 24 px page
padding. Three breakpoints: ≥1440 px full console (sidebar + 12 columns + optional right rail),
1280 px rail collapses, ≤768 px single column with cards instead of table rows. Tables get a
sticky header and horizontal scroll inside their own container — never the page.

## Elevation & Depth

No shadows. Depth is expressed with the surface ladder (`surface` → `surfaceRaised` →
`surfaceHover`), 1 px `border`/`borderStrong` lines, and a 2 px `primary` ring for focus and
selection. Modals sit on a 60 % black scrim over `surfaceRaised`.

## Shapes

Radius: `xs` 4 px for bars and swatches, `sm` 6 px for controls, `md` 10 px for cards,
`lg` 14 px for the largest containers, `pill` for status and cause badges. One radius per
element role — never mix two radii in one component.

## Components

`card` is the only container: 16 px padding, `md` radius, 1 px border, optional
`card-header` in label-caps. `kpi-value` + `kpi-label` form the KPI card (value, unit,
one-line context, 24 px sparkline). Badges (`badge-neutral`, `badge-ok`, `badge-warn`,
`badge-critical`) are pills with a tinted background from `surfaceRaised` and semantic text
colour — never a saturated fill. Buttons: exactly one `button-primary` per view, everything
else `button-ghost`. Tables use `table-header` + `table-row` (+`table-row-hover`), zebra
striping limited to a 3 % surface tint. `probability-bar-track`/`probability-bar-fill` render
the 9-class cause distribution; only the top three classes get labels, the remainder collapses
into a muted "lainnya" segment.

## Do's and Don'ts

- **Do** keep exactly two text colours in any panel and let spacing carry hierarchy.
- **Do** show the disclosure badge `data sintetis · seed 42` on every AI panel and the model
  evaluation page; honesty about simulated labels is part of the design.
- **Do** give every panel loading, empty and error states of the same height so the console
  never reflows while data refreshes.
- **Don't** use saturated fills, gradients, glassmorphism, oversized icons or emoji as icons.
- **Don't** encode state by colour alone, and never use a cause colour for a non-cause element.
- **Don't** animate anything that changes value every second (KPI numbers update in place,
  no count-up animations, no pulsing indicators except one live-status dot).
