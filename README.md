# Traffix

Traffix is an operator console for urban traffic in Indonesia. It watches a set of
intersections and tries to answer one question per road section: what is holding
traffic up right now. Nine answers are possible, from a dead traffic light to
flooding, and the console shows which one the model picked, how sure it is, and
what a dispatcher could do about it.

The rest of the system is the older half: YOLOv8 reads vehicle traffic from camera
footage, and LSTM forecasts volume 15 minutes, 2 hours and 4 hours ahead. Those two
get top billing in the first version of this project. The work added since then is
the cause diagnosis sitting on top of them.

Everything runs offline from a replayed dataset, on purpose. A demo should not
depend on a live CCTV feed, a Google Drive credential, or the room's wifi.

## What is measured and what is simulated

Worth stating before any number, because a traffic project can look impressive
while being unfalsifiable.

Every training and test set behind the forecasting and cause models is **synthetic**.
The only observed data is 123 frames from public Bina Marga toll-road CCTV
recordings, used to demonstrate YOLO inference. Numbers below are benchmark results
on simulated traffic, not measurements of Jakarta traffic. All of them come from
`python backend/scripts/run_d2_evaluation.py`; the generated one-page summary is
`docs/pitch/D2_METRICS_BRIEF.md`.

The v4 dataset behind the cause classifier is generated (`data/data_synthetic/v4/`,
seed 42, 302,400 section-minutes over 7 days). Its cause labels come from the
simulator's own causal rules, not from somebody standing at a junction with a
clipboard. So the classifier result shows that the physical sensor state carries
enough information to recover the mechanism the simulator used. It does not show
that the model generalises to a real Jakarta rush hour, and the model card says so
in those words. Every panel that shows model output carries a
`data sintetis · seed 42` badge.

The 24-hour history strip is drawn from the 60 ticks the API keeps in memory, not
from a stored day of data. The panel says that instead of pretending otherwise.

## Model results

### Primary D2 task: volume forecasting (LSTM)

Six intersections of the v4 replay, days 1-5 train, day 6 validate, day 7 test
(scored once). Target: intersection volume at t+h in veh/hour. MAE on the test day,
in veh/hour:

| Model | 15 min (n=8,550) | 2 h (n=7,920) | 4 h (n=7,200) |
|---|---|---|---|
| **LSTM (served)** | **364.9** | **577.8** | **703.7** |
| persistence | 435.3 | 1,761.9 | 1,579.2 |
| mean of last 15 min | 492.6 | 1,778.8 | 1,496.7 |
| seasonal naive (yesterday, same time) | 369.4 | 372.6 | 379.4 |
| ridge | 325.2 | 1,007.5 | 1,082.1 |
| HistGradientBoosting | 274.3 | 356.0 | 397.0 |

The honest reading:
- LSTM beats persistence at every horizon.
- LSTM is level with the seasonal naive baseline at 15 minutes (+1.2%, 95% block
  bootstrap CI includes zero).
- LSTM is significantly worse than seasonal naive at 2 and 4 hours.
- HistGradientBoosting was already best on the validation day, so that conclusion
  does not lean on the test set.

The notebook's older figures (test MAPE 21.8 / 27.0 / 32.5%) reproduce exactly, but
their protocol had five problems (row-order split, 16/121/241-minute effective
horizons, a persistence baseline that read the future, baselines only for 15
minutes, no purging), so they are not used as a claim. Details are in
`backend/ml/forecast/model_card.md` and `docs/D2_RESEARCH_PROTOCOL.md`.

### Supporting: bottleneck cause classifier (simulator labels)

Trained by `backend/ml/bottleneck/train_bottleneck.py` on 46 features, temporal
split (days 1 to 5 train, day 6 validate, day 7 test). Retrained in the pinned
environment so the stored metrics match what the API runs:

| Model | macro-F1 | balanced accuracy | accuracy |
|---|---|---|---|
| hist_gradient_boosting (shipped) | 0.8475 | 0.8317 | 0.8928 |
| rule-based heuristic baseline | 0.1757 | 0.2237 | 0.5598 |
| majority class baseline | 0.0710 | 0.1111 | 0.4694 |

Validation-day macro-F1 is 0.7228, so performance varies a lot between days.

### Supporting: YOLOv8 (validation only)

YOLOv8 was evaluated on a 100-image Kaggle validation set (493 objects, one class:
`car`):

| Metric | Value |
|---|---|
| mAP50 | 0.926 |
| mAP50-95 | 0.532 |
| precision / recall at IoU ≥ 0.5, conf 0.25 | 0.867 / 0.884 |

There is no independent test set, and the validation set also picked the best epoch.
On toll-road CCTV the team model misses most small distant vehicles (1.3 boxes per
frame on average). The camera demo therefore runs the official Ultralytics YOLOv8m
COCO checkpoint (`yolo pipeline/model/yolov8m_coco.pt`, not trained by the team,
AGPL-3.0), restricted to car/motorcycle/bus/truck at 1280 px. It finds 7.6 boxes per
frame on the same 123 frames. Without reference labels these are detection counts, not
accuracy. See `backend/ml/detection/model_card.md`.

Class balance is ugly: `normal` is 20,280 of the 43,200 test rows while
`lampu_mati` is 989, which is why macro-F1 and balanced accuracy lead the table
and plain accuracy does not. Per-class precision/recall/F1, the 9x9 confusion
matrix, feature importances and the limitations list are in
`backend/ml/bottleneck/artifacts/metrics.json` and served live by
`GET /api/v1/model/evaluation`, rendered in the "Penyebab bottleneck" sub-tab of
Evaluasi Model. The competition claim rests on the "Peramalan volume · utama" sub-tab.

## The three parameters added in v4

Bottleneck cause. Every section-minute gets one of nine labels (`normal`,
`volume_puncak`, `perbaikan_jalan`, `hujan`, `banjir`, `kecelakaan`,
`keramaian_event`, `lampu_mati`, `kendaraan_berat`) resolved through an explicit
priority order, then predicted from physical traffic state only. Labels, trigger
rules and the forbidden-feature list are frozen in `docs/SCHEMA-v4.md`.

Red light timing. Cycle length, average green, average red, average wait, queue and
delay, reported per intersection type (`perempatan` runs a 120 s cycle,
`pertigaan` an 80 s one) plus the combined average across every monitored signal,
which is the number asked for first: average wait across all six intersections.

Road sections. 30 sections, 21 signalised approaches and 9 mid-block corridors,
each with geometry, capacity in `smp/jam`, storage capacity in vehicles, volume,
V/C ratio, level of service A to F, and the vehicle mix split into roda 2, 3, 4 and
6+ with SMP equivalents. Total storage across the network is 3,982 vehicles. Units
stay apart deliberately: flow and capacity in `smp/jam`, vehicle counts in `kend`,
queues in `kend` with metres in brackets, speed in `km/jam`.

## Where things live

```text
backend/
  app/            FastAPI app, routes, services, replay state
  core/           config, constants, schemas
  ml/bottleneck/  v4 cause classifier: features, trainer, model card, artifacts
  ml/             LSTM loader and predictor
  sim/            tick engine and dataset replay
  rec/            rule-based green light recommendations
  tests/          pytest suite
  scripts/run_dev.py
frontend/
  src/pages/                 Dashboard, Livemap, ModelEvaluation, Settings, Login
  src/components/ui/         shared primitives (buttons, badges, modal, toast, charts)
  src/components/dashboard/  diagnosis panel, signal timing, segment table, audit trail
  src/lib/                   api client, auth, theme, formatting, cause metadata
  design/                    design tokens, DESIGN.md, UI-CONTRACT.md
  scripts/                   render-check.mjs, ui_audit.py
data/data_synthetic/v4/      generator plus the four v4 files
data/data_synthetic/         legacy hybrid dataset used by the replay fallback
yolo pipeline/               YOLOv8 notebook, config, best.pt
LSTM Training/               LSTM notebook and artifacts (keras, scalers, config, metrics)
inference/                   inference notebooks and their outputs
inference_data/data_video/   camera video preprocessing scripts
docs/                        schema, audit notes, planning handout
```

## Running it

Python 3.11 or newer. Node 20.19 or newer, which is what Vite 8 wants.

```bash
git clone https://github.com/MrEuwn/traffix.git
cd traffix

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # or backend/requirements.txt for the API only

cd backend
cp .env.example .env             # defaults already fit this folder layout
python scripts/run_dev.py        # http://localhost:8000, docs at /docs
```

On startup the backend loads the v4 replay file, builds the forecast feature windows,
loads the LSTM artifacts from `backend/ml/forecast/artifacts/models/`, and starts its
tick engine. Without the model files or TensorFlow, `ML_ALLOW_FALLBACK=true` keeps
the API answering with a moving-average heuristic labelled `heuristic` rather than
failing. `REPLAY_START_TICK` (default 9000) decides where the replay begins; 9000 is
day 7 at 06:00 WIB, the held-out test day, in the morning peak.

For live YOLO inference on the recorded CCTV frames, also install
`backend/requirements-yolo.txt` (CPU torch first:
`pip install torch --index-url https://download.pytorch.org/whl/cpu`).

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Log in with `admin` / `admin123`. That login is client-side only, there is no auth
endpoint on the backend. The header holds the four tabs, a status pill, the clock
in WIB and the theme switch. If the API lives somewhere else, put
`VITE_API_URL=http://host:port` in `frontend/.env`.

## Running it with Docker (competition demo)

```bash
docker compose up -d --build        # images: traffix-backend:competition, traffix-frontend:competition
docker compose ps                   # wait until both are "healthy"
# UI   http://localhost:8080   (Nginx serves the SPA and proxies /api, /health, /docs)
# API  http://localhost:8000   (direct, for debugging)
docker compose logs --tail=200 backend frontend
docker compose down                 # no volumes: models and data are baked into the image
```

After the images are built, nothing needs internet, CCTV or credentials. The replay
starts on day 7 at 06:00 (`REPLAY_START_TICK=9000`), the held-out test day, so the
forecasts on screen are not in-sample. Build with `WITH_YOLO=false` for a smaller
backend that serves only the stored detections. Details are in
`docs/DOCKER_DEPLOYMENT.md`.

## Checks

```bash
cd backend  && pytest -q                 # unit and integration tests
cd frontend && npm run build             # tsc -b plus production bundle
cd frontend && npm run lint
cd frontend && npm run check:render      # renders the panels against the running API
cd frontend && npm run check:ui          # Playwright audit of the running app
```

`check:ui` needs both servers up, then drives a real browser: logs in, visits all
four tabs, and fails if an error state is visible, if the UI font is not Inter, if
the numeric utility is not JetBrains Mono, if any text sits below 11 px, if an
emoji is used as an icon, if a button is smaller than a usable touch target, if the
change-phase confirmation modal or its undo toast stops working, or if a page
overflows horizontally at 1600, 1440 or 1280 px. Screenshots land in
`frontend/screenshots/`.

GitHub Actions runs the backend suite on every push that touches `backend/`.

## API

| Endpoint | What it returns |
|---|---|
| `GET /health` | service health |
| `GET /api/v1/system/status` | ML, simulation, dataset and camera readiness |
| `GET /api/v1/intersections` | live status for the six intersections |
| `GET /api/v1/predictions/{intersection_id}` | 15m, 2h and 4h forecast for one intersection |
| `POST /api/v1/predictions` | forecast for a single named horizon |
| `GET /api/v1/recommendations` | green light duration recommendations |
| `GET /api/v1/bottlenecks` | dominant cause, per-class shares, confidence, top three, drivers |
| `GET /api/v1/bottlenecks/{intersection_id}` | probabilities, 60-tick history, sections |
| `GET /api/v1/segments` | the 30 sections with capacity, V/C, LOS and vehicle mix |
| `GET /api/v1/segments/summary` | section counts, total capacity, fleet split, LOS spread |
| `GET /api/v1/signals/summary?scope=all\|perempatan\|pertigaan` | red light timing averages |
| `GET /api/v1/model/evaluation` | cause classifier against both baselines, per-class metrics, confusion matrix, leakage guard, limitations, reproduction check |
| `GET /api/v1/model/evaluation/forecast` | D2 primary task: LSTM vs five comparators per horizon, bootstrap CI, error analysis, transfer test, notebook reproduction, runtime status |
| `GET /api/v1/model/evaluation/forecast/{h}/series?intersection=` | saved per-sample test predictions (actual, LSTM, baseline) |
| `GET /api/v1/model/evaluation/detection` | YOLO validation metrics (recorded, labelled validation) and frame-inference summary |
| `GET /api/v1/model/status` | which forecaster is serving (`lstm` / `heuristic_fallback` / `disabled`) and whether its sha256 matches the evaluated files |
| `GET /api/v1/weather/current` | current weather context |
| `GET /api/v1/simulation/status`, `POST /api/v1/simulation/start\|stop` | replay controls |
| `GET /api/v1/cameras` | camera slots per intersection |
| `GET /api/v1/cameras/frames` | recorded public CCTV frames with stored YOLO detections |
| `GET /api/v1/cameras/frames/{id}/image?annotated=` | the frame JPEG, with or without boxes |
| `POST /api/v1/cameras/frames/{id}/infer` | runs YOLO now on that frame (503 when the image was built without YOLO) |

Every analytics endpoint takes `?tick=`. Without it they follow the live replay
cursor, so all panels show the same instant.

## Interface notes

Dark by default, with a light theme behind the same switch. One accent colour
carries interaction, text comes in three greys at 5:1 contrast or better on every
surface, and status is never colour alone: each of the nine causes has its own
glyph, each vehicle class its own fill pattern.

Inter handles UI text. JetBrains Mono handles numbers through a single `.num`
utility with `tabular-nums`, so columns do not jitter while the replay advances a
second at a time. Nothing renders below 11 px. Panels animate nothing that updates
every tick.

Colours and type live in `frontend/tailwind.config.js` as
`rgb(var(--c-*) / <alpha-value>)`, with the values set per theme in
`lib/ThemeContext.tsx`. Shared pieces (card, panel header, state block, cause
badge, status pill, modal with a focus trap, toast with undo) sit in
`frontend/src/components/ui/`. Rules new screens have to follow are written down in
`frontend/design/UI-CONTRACT.md`.

## Regenerating data

```bash
python data/data_synthetic/v4/generate_data_v4.py      # v4: ticks, replay, intersections, sections
python data/data_synthetic/generate_data_hybrid.py     # legacy replay dataset
```

The v4 generator writes `ticks_v4.csv.gz` (302,400 rows, 51 columns),
`live_replay_7d.csv.gz` (60,480 rows), `intersections.csv` (6) and `sections.csv`
(30). Capacities, SMP values and LOS thresholds follow MKJI 1997; weather follows
the shape of the Open-Meteo model. It is deterministic and takes a couple of
minutes.

## Training pipelines

YOLOv8: open `yolo pipeline/code/traffix_yolo_pipeline_revised.ipynb` in Colab on a
GPU runtime. The Kaggle dataset downloads itself through `kagglehub`. It writes
`best.pt` and `traffic_features.csv`. Inference runs in
`inference/inference_yolo/traffix_yolo_inference.ipynb` and needs the CCTV video
folder mounted in a `pagi` / `siang` / `malam` structure.

LSTM (served model): `python backend/scripts/run_d2_evaluation.py`. It trains and
selects the LSTM on days 1-5 / 6 of the v4 replay, scores day 7 once against five
comparators, and writes the served models to `backend/ml/forecast/artifacts/models/`.
The original notebook `LSTM Training/traffix_lstm_final.ipynb` and its artifacts in
`LSTM Training/artifacts/` are kept for the reproduction check only; the pipeline
re-scores them and lists the protocol issues it found.

Cause classifier: `python backend/ml/bottleneck/train_bottleneck.py` (seed 42).

YOLO on the recorded CCTV frames: `python backend/scripts/run_yolo_frames.py`.

## Camera data collection

Ten scripts in sequence, documented in `inference_data/data_video/video_data.md`:

```bash
python data/cctv_stage1_collect_links.py
python data/cctv_stage2_record_videos.py
python inference_data/data_video/01_create_video_inventory.py
python inference_data/data_video/02_extract_frames.py
python inference_data/data_video/03_select_best_frame.py
python inference_data/data_video/03b_validate_location_input.py
python inference_data/data_video/04_create_unique_camera_locations.py
python inference_data/data_video/05_validate_camera_coordinates.py
python inference_data/data_video/06_join_video_with_coordinates.py
python inference_data/data_video/07_fetch_weather_openmeteo.py
```

They hit public endpoints only (Open-Meteo and the public Bina Marga PUPR camera
list), so no API keys are involved. The first two need ffmpeg, and the link
scraper needs Playwright browsers.

## Documentation

- `docs/PETA-PROYEK-END-TO-END.md`: orientation doc. How the pieces connect, what is
  finished, how to demo it, and what is still open.
- `docs/PEMBELAJARAN-PR1.md`: twelve lessons from replaying the D2 pull request, each one
  tied to a file or a number in this repo.
- `docs/SCHEMA-v4.md`: frozen contract. Nine causes, priority rules, forbidden
  features, API shapes.
- `backend/ml/bottleneck/model_card.md`: split protocol, metrics, error analysis,
  limitations.
- `backend/ARCHITECTURE.md`: backend structure, and how ML, weather and simulation
  fit together.
- `backend/CONTRIBUTING.md`: branch and commit conventions.
- `data/data_process/data_dictionary.md`, `aggregation_rules.md` and
  `dataset_validation.md`: column definitions, and how the synthetic data was put
  together and checked.
- `docs/STITCH-AUDIT-A.md` and `docs/STITCH-AUDIT-A-rerun.md`: design audit before
  and after the interface rebuild.
- `docs/RENCANA-TRAFFIX-v2-D2-ROBCOM2026.pdf`: the D2 development plan.
- `docs/D2_RESEARCH_PROTOCOL.md`: the frozen research question, split, baselines,
  metrics and claim boundary.
- `docs/D2_REPO_AUDIT.md`, `docs/D2_VERIFICATION_REPORT.md`,
  `docs/D2_REQUIREMENTS_TRACEABILITY.md`: what was found, what was run, and where each
  competition requirement is evidenced.
- `docs/evidence/d2/`: generated evaluation summary, data quality report and figures.
- `docs/pitch/`: generated metrics brief, demo runbook, Q&A brief.
- `docs/DOCKER_DEPLOYMENT.md`: container topology, ports, health checks,
  troubleshooting.
- `backend/ml/forecast/model_card.md`, `backend/ml/detection/model_card.md`.

## Known limits

Every training and test set is synthetic, so every model number is a benchmark
result, not a measurement of Jakarta traffic. Cause labels come from simulator rules,
so the classifier demonstrates mechanism recovery rather than field accuracy. Without
the model files the API serves a labelled moving-average heuristic, and
`/api/v1/model/status` says so. The camera panel replays recorded public CCTV frames,
not a live feed. The team's YOLO recognises only `car`, has validation metrics but no
independent test set, and fails on toll-road cameras. The demo detector is a COCO
checkpoint that has no reference labels on these frames either. Green time is reported as
one number per intersection rather than per approach, because the simulator does
not expose per-phase splits; the confirmation modal says so where it matters. And
the legacy replay file still describes four intersections while the v4 dataset has
six, so the older recommendations view and the v4 analytics do not line up section
by section yet.
