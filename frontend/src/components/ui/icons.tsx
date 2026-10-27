/* Ikon garis SVG inline — tanpa emoji, tanpa font ikon tambahan.
   Semua 1.5–2px stroke, ukuran default 16px, warna mengikuti currentColor. */
import type { SVGProps } from "react";

const PATHS: Record<string, string[]> = {
  "check-circle": ["M22 11.08V12a10 10 0 1 1-5.93-9.14", "m9 11 3 3L22 4"],
  "trending-up": ["m22 7-8.5 8.5-5-5L2 17", "M16 7h6v6"],
  cone: ["M9.5 3h5l3.5 18h-12z", "M5 21h14", "M10.5 10h3"],
  "cloud-rain": ["M4 14a4 4 0 0 1 1.2-7.8A5.5 5.5 0 0 1 16 6.5a4.5 4.5 0 0 1 1 8.9", "M8 19v2", "M12 18v3", "M16 19v2"],
  waves: ["M2 6c2 0 3-1.5 5-1.5S10 6 12 6s3-1.5 5-1.5S20 6 22 6", "M2 12c2 0 3-1.5 5-1.5S10 12 12 12s3-1.5 5-1.5S20 12 22 12", "M2 18c2 0 3-1.5 5-1.5S10 18 12 18s3-1.5 5-1.5S20 18 22 18"],
  "alert-triangle": ["m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z", "M12 9v4", "M12 17h.01"],
  users: ["M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", "M9 7a4 4 0 1 0 0 8 4 4 0 0 0 0-8", "M22 21v-2a4 4 0 0 0-3-3.9", "M16 3.1a4 4 0 0 1 0 7.8"],
  "lightbulb-off": ["M9 18h6", "M10 22h4", "M8.5 5a5 5 0 0 1 7 4.5c0 1.6-.8 2.4-1.5 3.2", "m3 3 18 18"],
  truck: ["M2 17V6h11v11", "M13 9h4l4 4v4h-8", "M7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4", "M18 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4"],
  gauge: ["M12 14 16 9", "M3 20a9 9 0 1 1 18 0", "M12 14h.01"],
  activity: ["M22 12h-4l-3 8-4-16-3 8H2"],
  clock: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18", "M12 7v5l3 2"],
  map: ["m9 4-6 2v14l6-2 6 2 6-2V4l-6 2-6-2Z", "M9 4v14", "M15 6v14"],
  chart: ["M3 3v18h18", "M7 14v3", "M12 9v8", "M17 5v12"],
  settings: ["M4 21v-7", "M4 10V3", "M12 21v-9", "M12 8V3", "M20 21v-5", "M20 12V3", "M2 14h4", "M10 8h4", "M18 16h4"],
  sliders: ["M4 6h16", "M4 12h16", "M4 18h16", "M9 3v6", "M15 9v6", "M7 15v6"],
  pin: ["M12 21s7-5.3 7-11a7 7 0 1 0-14 0c0 5.7 7 11 7 11Z", "M12 10h.01"],
  search: ["M11 3a8 8 0 1 0 0 16 8 8 0 0 0 0-16", "m21 21-4.3-4.3"],
  close: ["M18 6 6 18", "m6 6 12 12"],
  "chevron-down": ["m6 9 6 6 6-6"],
  "chevron-right": ["m9 6 6 6-6 6"],
  "arrow-up": ["M12 19V5", "m5 12 7-7 7 7"],
  "arrow-down": ["M12 5v14", "m19 12-7 7-7-7"],
  refresh: ["M21 12a9 9 0 1 1-3-6.7", "M21 3v6h-6"],
  inbox: ["M22 12h-6l-2 3h-4l-2-3H2", "M5 5h14l3 7v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5l3-7Z"],
  bell: ["M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9", "M13.7 21a2 2 0 0 1-3.4 0"],
  info: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18", "M12 16v-4", "M12 8h.01"],
  sun: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8", "M12 2v2", "M12 20v2", "M4.9 4.9l1.4 1.4", "M17.7 17.7l1.4 1.4", "M2 12h2", "M20 12h2", "M4.9 19.1l1.4-1.4", "M17.7 6.3l1.4-1.4"],
  moon: ["M21 12.8A8.5 8.5 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8"],
  logout: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "m16 17 5-5-5-5", "M21 12H9"],
  download: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "m7 10 5 5 5-5", "M12 15V3"],
  layers: ["m12 2 9 5-9 5-9-5 9-5", "m3 12 9 5 9-5", "m3 17 9 5 9-5"],
  play: ["m6 3 14 9-14 9V3"],
  pause: ["M8 4h3v16H8z", "M13 4h3v16h-3z"],
  undo: ["M3 7v6h6", "M3 13a9 9 0 1 0 3-6.7L3 9"],
  car: ["M5 17h14", "M6 17v2", "M18 17v2", "m5 17-1-6 2-4h12l2 4-1 6", "M7 12h10"],
};

export type IconName = keyof typeof PATHS;

export const Icon = ({
  name,
  size = 16,
  className = "",
  ...rest
}: { name: string; size?: number; className?: string } & Omit<SVGProps<SVGSVGElement>, "name">) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
    className={`inline-block shrink-0 ${className}`}
    {...rest}
  >
    {(PATHS[name] ?? PATHS.info).map((d) => (
      <path key={d} d={d} />
    ))}
  </svg>
);
