# Traffix — Docker deployment (demo kompetisi)

Satu perintah, dua container, tanpa CCTV live, tanpa kredensial, dan tanpa internet saat
runtime (internet hanya dibutuhkan ketika membangun image).

```bash
docker compose up -d --build          # bangun dan jalankan
docker compose ps                     # tunggu dua-duanya "healthy"
open http://localhost:8080            # login: admin / admin123
```

## Arsitektur

```text
browser ──► :8080  traffix-frontend:competition (nginx:1.27-alpine)
                    ├─ /            → SPA hasil `vite build`
                    ├─ /api/*       ┐
                    ├─ /health      ├─► http://backend:8000  (jaringan compose "traffix")
                    └─ /docs        ┘
            :8000  traffix-backend:competition (python:3.12-slim, uvicorn)
                    ├─ replay sintetis v4  ../data/data_synthetic/v4/live_replay_7d.csv.gz
                    ├─ LSTM D2             backend/ml/forecast/artifacts/models/*
                    ├─ classifier penyebab backend/ml/bottleneck/artifacts/*
                    └─ YOLO                ../yolo pipeline/model/yolov8m_coco.pt (demo) + best.pt (pembanding) + frame CCTV rekaman
```

Frontend dibangun dengan `VITE_API_URL=""`, sehingga browser memanggil `/api/v1/...` di
origin yang sama. Nginx meneruskan path apa adanya ke service `backend`; prefiks tidak
diubah. Nama host `backend` hanya bisa di-resolve di dalam jaringan compose, jadi nama itu
tidak pernah dikirim ke browser.

## Image

| Image | Dockerfile | Context | Isi |
|---|---|---|---|
| `traffix-backend:competition` | `Dockerfile` (root) | root repo | FastAPI; TensorFlow 2.21 (CPU); scikit-learn 1.9.1; artefak model dan evaluasi; data replay v4; frame CCTV; opsional ultralytics + torch CPU |
| `traffix-frontend:competition` | `frontend/Dockerfile` | `frontend/` | Node 22 untuk build (multi-stage) → Nginx statis + proxy |

Build arg `WITH_YOLO` (default `true`) memasang ultralytics dan torch CPU untuk inferensi
YOLO langsung (`POST /api/v1/cameras/frames/{id}/infer`). Dengan `WITH_YOLO=false`, image
lebih kecil; API tetap menyajikan deteksi tersimpan dan melaporkan
`live_inference_available: false`.

Image backend dibangun native untuk arsitektur host. Paket `tensorflow` (bukan
`tensorflow-cpu`) dipakai karena punya wheel ARM64 dan x86_64; di Linux paket ini CPU-only.

## Port dan konfigurasi

| Variabel | Default | Arti |
|---|---|---|
| `FRONTEND_PORT` | 8080 | port host untuk UI |
| `BACKEND_PORT` | 8000 | port host untuk API langsung (opsional, untuk debugging) |
| `WITH_YOLO` | true | sertakan inferensi YOLO langsung di image |
| `CORS_ORIGINS` | http://localhost:8080 | hanya dipakai bila API dipanggil lintas origin |
| `REPLAY_START_TICK` | 9000 | menit awal replay; 9000 = hari 7 (hari **uji**) pukul 06:00 |
| `TICK_INTERVAL_SECONDS` | 2 | kecepatan replay |

Salin `.env.docker.example` menjadi `.env.docker` untuk mengganti nilainya. File itu
di-gitignore, opsional, dan tidak berisi rahasia.

## Health check

- **backend:** `python -c urllib.request.urlopen('http://127.0.0.1:8000/health')`. Python
  sudah ada di image, jadi tidak perlu curl.
- **frontend:** `wget -q -O /dev/null http://127.0.0.1/`. BusyBox wget sudah ada di
  `nginx:alpine`.
- frontend `depends_on: backend: condition: service_healthy`.

## Data dan persistensi

- **Tidak ada volume.** Model, artefak evaluasi, replay, dan frame CCTV dibakukan di image
  saat build. `docker compose down` tidak menghapus apa pun yang dibutuhkan, dan restart
  memakai artefak yang sama persis.
- Metrik tidak pernah dihitung ulang saat container start, jadi angka di UI stabil.
- Untuk memperbarui angka: jalankan `python backend/scripts/run_d2_evaluation.py` di host,
  lalu `docker compose build backend && docker compose up -d`.
- `.dockerignore` mengecualikan `.git`, `.venv`, notebook, `LSTM Training/` (hanya untuk
  reproduksi angka lama), `Traffix.id-main/` (folder legacy), `docs/`, dan video mentah.

## Perintah

```bash
docker compose config                     # validasi file compose
docker compose build --no-cache           # bangun ulang dari nol
docker compose up -d                      # jalankan di latar belakang
docker compose ps                         # status + health
docker compose logs --tail=200 backend frontend
docker compose restart backend            # restart tanpa rebuild
docker compose down                       # hentikan & hapus container + network
docker image rm traffix-backend:competition traffix-frontend:competition   # bersihkan image
```

## Verifikasi dari host

```bash
curl -s localhost:8080/health
curl -s localhost:8080/api/v1/model/status | python3 -m json.tool        # mode: lstm, matches_evaluation: true
curl -s localhost:8080/api/v1/model/evaluation/forecast | head -c 400
curl -s localhost:8080/api/v1/predictions/INT-001 | python3 -m json.tool
curl -s -X POST localhost:8080/api/v1/cameras/frames/pagi_cctv_002_20260518_070954_frame_3s/infer
```

## Pemecahan masalah

| Gejala | Penyebab / tindakan |
|---|---|
| frontend tidak pernah start | backend belum `healthy` — lihat `docker compose logs backend`; TensorFlow butuh ±20 detik saat start pertama |
| UI: "Peramal: heuristik (fallback)" | file model tidak ada di image → jalankan evaluasi lalu rebuild backend |
| `matches_evaluation: false` | model yang dimuat bukan yang dievaluasi → jalankan ulang evaluasi lalu rebuild |
| Tombol "Jalankan YOLO" nonaktif | image dibangun dengan `WITH_YOLO=false` |
| Port 8000/8080 sudah dipakai | ubah `FRONTEND_PORT` / `BACKEND_PORT` di `.env.docker` |
| Build lambat di Mac M-series | normal pada build pertama (TensorFlow + torch); build berikutnya memakai cache layer |

## Batasan yang diketahui

- Image backend besar (TensorFlow + torch). Gunakan `WITH_YOLO=false` bila ruang disk sempit.
- Inferensi YOLO langsung (YOLOv8m @1280) berjalan di CPU container: ±4 detik per frame
  setelah model termuat, dan ±6–7 detik untuk panggilan pertama. Tekan tombol sekali
  sebelum demo.
- Replay berputar ulang ke hari 1 setelah hari 7 berakhir. Prakiraan pada hari 1–6
  diberi label "in-sample"/"validasi" di UI.
- Tidak ada TLS atau autentikasi server. Login hanya di sisi klien dan ditujukan untuk demo
  lokal, bukan deployment publik.
