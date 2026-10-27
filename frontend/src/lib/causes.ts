/* Satu sumber kebenaran untuk 9 kelas penyebab (SCHEMA-v4 §1):
   label Indonesia, warna, ikon. Status tidak pernah hanya warna. */
import type { IconName } from "../components/ui/icons";

export interface CauseMeta {
  label: string;
  color: string;
  icon: IconName;
}

export const CAUSE_META: Record<string, CauseMeta> = {
  normal: { label: "Normal", color: "#2EA043", icon: "check-circle" },
  volume_puncak: { label: "Volume puncak", color: "#D29922", icon: "trending-up" },
  perbaikan_jalan: { label: "Perbaikan jalan", color: "#DB6D28", icon: "cone" },
  hujan: { label: "Hujan", color: "#2F81F7", icon: "cloud-rain" },
  banjir: { label: "Banjir / genangan", color: "#1F6FEB", icon: "waves" },
  kecelakaan: { label: "Kecelakaan", color: "#E5534B", icon: "alert-triangle" },
  keramaian_event: { label: "Keramaian event", color: "#A371F7", icon: "users" },
  lampu_mati: { label: "Lampu mati", color: "#C264C8", icon: "lightbulb-off" },
  kendaraan_berat: { label: "Kendaraan berat", color: "#9E8A1F", icon: "truck" },
};

export const CAUSE_ORDER = [
  "normal",
  "volume_puncak",
  "perbaikan_jalan",
  "hujan",
  "banjir",
  "kecelakaan",
  "keramaian_event",
  "lampu_mati",
  "kendaraan_berat",
];

export const causeMeta = (cause: string): CauseMeta =>
  CAUSE_META[cause] ?? { label: cause, color: "#8493A1", icon: "info" };

/* Kelas kendaraan: pola isian berbeda per kelas (butir 3 audit). */
export const VEHICLE_CLASSES = [
  { key: "roda_2", label: "R2", desc: "Motor", pattern: "pattern-r2" },
  { key: "roda_3", label: "R3", desc: "Bajaj / bemo", pattern: "pattern-r3" },
  { key: "roda_4", label: "R4", desc: "Mobil", pattern: "pattern-r4" },
  { key: "roda_6plus", label: "R6+", desc: "Truk / bus", pattern: "pattern-r6" },
] as const;

/* Tingkat pelayanan (LOS) — selalu huruf + kata. */
export const LOS_META: Record<string, { label: string; color: string }> = {
  A: { label: "Lancar", color: "#2EA043" },
  B: { label: "Stabil", color: "#34D399" },
  C: { label: "Sedang", color: "#2F81F7" },
  D: { label: "Padat", color: "#D29922" },
  E: { label: "Sangat padat", color: "#DB6D28" },
  F: { label: "Macet", color: "#E5534B" },
};

export const losMeta = (los: string) => LOS_META[los] ?? { label: los, color: "#8493A1" };

export const SEED_BADGE = "data sintetis · seed 42";
