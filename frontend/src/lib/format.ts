/* Format angka gaya Indonesia + metadata kelas penyebab (SCHEMA-v4 §1). */
import type { CSSProperties } from "react";

const nf = (min: number, max: number) =>
  new Intl.NumberFormat("id-ID", { minimumFractionDigits: min, maximumFractionDigits: max });

export const fmtInt = (n: number | null | undefined) =>
  n == null || Number.isNaN(n) ? "—" : nf(0, 0).format(n);

export const fmtNum = (n: number | null | undefined, d = 2) =>
  n == null || Number.isNaN(n) ? "—" : nf(d, d).format(n);

export const fmtPct = (n: number | null | undefined, d = 1) =>
  n == null || Number.isNaN(n) ? "—" : `${nf(d, d).format(n * 100)}%`;

export const CAUSE_LABEL: Record<string, string> = {
  banjir: "Banjir / genangan",
  kecelakaan: "Kecelakaan",
  lampu_mati: "Lampu mati",
  perbaikan_jalan: "Perbaikan jalan",
  keramaian_event: "Keramaian event",
  hujan: "Hujan",
  kendaraan_berat: "Kendaraan berat",
  volume_puncak: "Volume puncak",
  normal: "Normal",
};

export const causeLabel = (c: string) => CAUSE_LABEL[c] ?? c;

export const CAUSE_COLOR: Record<string, string> = {
  banjir: "#14b8a6",
  kecelakaan: "var(--red)",
  lampu_mati: "#f472b6",
  perbaikan_jalan: "var(--orange)",
  keramaian_event: "var(--purple)",
  hujan: "var(--blue)",
  kendaraan_berat: "var(--yellow)",
  volume_puncak: "#a3e635",
  normal: "var(--green)",
};

const RED = { color: "var(--red)", bg: "var(--red-bg)", border: "var(--red-border)" };
const ORANGE = { color: "var(--orange)", bg: "var(--orange-bg)", border: "var(--orange-border)" };
const YELLOW = { color: "var(--yellow)", bg: "var(--yellow-bg)", border: "var(--yellow-border)" };
const GREEN = { color: "var(--green)", bg: "var(--green-bg)", border: "var(--green-border)" };

export const LOS_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  A: GREEN,
  B: GREEN,
  C: YELLOW,
  D: YELLOW,
  E: ORANGE,
  F: RED,
};

export const losStyle = (los: string) => LOS_STYLE[los] ?? GREEN;

/* Gaya kartu + badge sumber data sintetis (dipakai panel & halaman evaluasi). */
export const CARD: CSSProperties = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: 12,
};

export const BADGE_SINTETIS: CSSProperties = {
  fontSize: 9,
  fontWeight: 600,
  letterSpacing: ".04em",
  color: "var(--purple)",
  background: "var(--purple-bg)",
  border: "1px solid var(--purple-border)",
  padding: "2px 8px",
  borderRadius: 20,
  whiteSpace: "nowrap",
};
