#!/usr/bin/env bash
# Jalankan Traffix untuk sesi demo: SPA + API satu origin, lalu buka tunnel publik.
#
#   bash scripts/demo_up.sh              # pakai dist yang sudah ada
#   REBUILD=1 bash scripts/demo_up.sh    # bangun ulang frontend dulu
#   PORT=8011 bash scripts/demo_up.sh    # ganti port
#
# Ctrl-C mematikan backend dan tunnel sekaligus.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8010}"
CF="${CLOUDFLARED:-$LOCALAPPDATA/hermes/cache/scratch/cloudflared.exe}"
LOG_DIR="${DEMO_LOG_DIR:-$LOCALAPPDATA/hermes/cache/scratch}"
mkdir -p "$LOG_DIR"
BE_LOG="$LOG_DIR/demo-backend.log"
CF_LOG="$LOG_DIR/demo-tunnel.log"
cd "$ROOT"

[ -x "$CF" ] || { echo "cloudflared tidak ada di $CF (set CLOUDFLARED=/path/ke/cloudflared)"; exit 1; }

if [ "${REBUILD:-0}" = "1" ] || [ ! -f frontend/dist/index.html ]; then
  echo "[1/3] build frontend dengan API relatif"
  ( cd frontend && VITE_API_URL="" npm run build >/dev/null )
else
  echo "[1/3] dist dipakai apa adanya (REBUILD=1 untuk bangun ulang)"
fi

if curl -sf "http://localhost:$PORT/health" >/dev/null; then
  echo "port $PORT sudah dipakai proses lain. Set PORT= lain atau hentikan dulu."; exit 1
fi

echo "[2/3] backend di :$PORT"
( cd backend && \
  FRONTEND_DIST_PATH=../frontend/dist \
  REPLAY_START_TICK=9000 \
  SIM_INTERSECTIONS=6 \
  ML_ALLOW_FALLBACK=true \
  ../.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
  >"$BE_LOG" 2>&1 ) &
BE=$!
trap 'kill $BE ${CFPID:-0} 2>/dev/null || true; wait 2>/dev/null || true; echo; echo "demo dihentikan"' INT TERM

for _ in $(seq 1 90); do curl -sf "http://localhost:$PORT/health" >/dev/null && break; sleep 1; done
curl -sf "http://localhost:$PORT/health" >/dev/null || {
  echo "backend gagal siap. 20 baris terakhir:"; tail -20 "$BE_LOG"; kill "$BE" 2>/dev/null; exit 1; }
echo "      /health OK"

echo "[3/3] tunnel publik"
"$CF" tunnel --url "http://localhost:$PORT" --no-autoupdate >"$CF_LOG" 2>&1 &
CFPID=$!

URL=""
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$CF_LOG" | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -n "$URL" ] || { echo "tunnel gagal, lihat $CF_LOG"; tail -20 "$CF_LOG"; kill "$BE" "$CFPID" 2>/dev/null; exit 1; }

sleep 4
if curl -sf -m 25 "$URL/health" >/dev/null; then echo "      tunnel OK"; else echo "      tunnel terbentuk tapi /health belum menjawab, coba buka di browser"; fi

cat <<EOF

  Bagikan tautan ini: $URL

  catatan
    laptop harus tetap menyala dan tidak tidur
    URL mati kalau cloudflared dihentikan, dan berubah saat dijalankan ulang
    batas quick tunnel: 200 permintaan bersamaan, tanpa jaminan uptime
    log: $BE_LOG  |  $CF_LOG
    berhenti: Ctrl-C
EOF

wait
