import axios from "axios";

// Default ke backend lokal untuk mode dev; build produksi memakai VITE_API_URL
// dari frontend/.env.production. Lihat frontend/.env.example.
// VITE_API_URL="" (image Docker) = path relatif, diproksikan Nginx ke backend.
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** URL absolut untuk aset yang dimuat browser langsung (mis. <img src>). */
export const apiUrl = (path: string) => `${BASE_URL}${path}`;

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

/** Respons API dibungkus `{data: ...}`; toleran bila route mengirim objek mentah. */
export const unwrap = <T>(res: { data: unknown }): T => {
  const body = res.data as { data?: T };
  return (body?.data ?? res.data) as T;
};
