import axios from "axios";

// Default ke backend lokal untuk mode dev; build produksi memakai VITE_API_URL
// dari frontend/.env.production. Lihat frontend/.env.example.
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
