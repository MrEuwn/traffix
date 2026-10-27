# Traffix backend image (FastAPI + LSTM inference + optional live YOLO).
# Build context is the repo root: the API reads ../data, ../inference*,
# ../yolo pipeline and backend/ml/*/artifacts at runtime.
#
#   docker build -t traffix-backend:competition .
#   docker build --build-arg WITH_YOLO=false -t traffix-backend:competition .   # smaller, stored detections only
FROM python:3.12-slim

ARG WITH_YOLO=true
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    MPLCONFIGDIR=/tmp/matplotlib \
    PORT=8000

# libgl/libglib: ultralytics pulls full opencv-python, which needs them to import.
RUN if [ "$WITH_YOLO" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
      && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app/backend
COPY backend/requirements.txt backend/requirements-yolo.txt ./
RUN pip install -r requirements.txt \
    && if [ "$WITH_YOLO" = "true" ]; then \
         pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
         && pip install -r requirements-yolo.txt; \
       fi

WORKDIR /app
COPY . .

# Non-root runtime; only the cache folders the API may write to are owned by it.
RUN useradd --create-home --uid 10001 traffix \
    && mkdir -p /app/backend/artifacts /app/backend/data /app/backend/logs \
    && chown -R traffix:traffix /app/backend/artifacts /app/backend/data /app/backend/logs
USER traffix
WORKDIR /app/backend

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health', timeout=4)" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
