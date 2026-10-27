/* Terjemahan label + format jam WIB untuk panel dashboard.
   Bukan data: hanya label enum dan format waktu dari API. */
const HM = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "Asia/Jakarta",
});

const HMS = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: "Asia/Jakarta",
});

/** ISO timestamp API -> "06:21". */
export const wibHm = (iso?: string | null) =>
  iso ? HM.format(new Date(iso)) : "—";

/** Jam sekarang WIB -> "06:21:44 WIB". */
export const wibClock = (date: Date = new Date()) => `${HMS.format(date)} WIB`;

/** Kode pendekat dataset v4 (N/E/S/W) -> label Indonesia. */
const APPROACH_LABEL: Record<string, string> = {
  N: "Utara",
  E: "Timur",
  S: "Selatan",
  W: "Barat",
};

export const approachLabel = (approach?: string | null) =>
  approach ? (APPROACH_LABEL[approach] ?? approach) : "—";

/** Kondisi cuaca API (label Inggris) -> label Indonesia. */
const WEATHER_LABEL: Record<string, string> = {
  Clear: "Cerah",
  Sunny: "Cerah",
  Cloudy: "Berawan",
  Hot: "Panas",
  Rain: "Hujan",
  Storm: "Badai",
  Haze: "Berkabut",
};

export const weatherLabel = (condition?: string | null) =>
  condition ? (WEATHER_LABEL[condition] ?? condition) : "—";
