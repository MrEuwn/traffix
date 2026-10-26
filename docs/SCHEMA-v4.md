# SCHEMA v4 — Kontrak Trafik Traffix (BEKU)

Status: **FREEZE**. Semua agent (data, model, backend, frontend) mengikuti nama field di dokumen ini
persis. Jangan mengubah nama field tanpa memperbarui dokumen ini lebih dulu.

## 0. Prinsip

- Satu file, satu pemilik. Tidak ada dua agent menyentuh file yang sama.
- Dataset v4 adalah **satu-satunya** sumber data untuk parameter baru.
- Jalur lama (live metrics, prediksi LSTM, rekomendasi hijau) tetap hidup dan tidak boleh rusak.
- Label penyebab berasal dari **simulator** dengan aturan eksplisit — wajib dinyatakan terbuka di UI
  (badge "data sintetis, seed 42") dan di model card.

## 1. Kelas penyebab (9 kelas, urutan prioritas tinggi → rendah)

| # | `bottleneck_cause` | Arti | Aturan pemicu (dievaluasi berurutan) |
|---|---|---|---|
| 1 | `banjir` | genangan menutup sebagian badan jalan | `tinggi_genangan_cm >= 15` |
| 2 | `kecelakaan` | insiden mendadak satu lengan/ruas | `accident_count > 0` |
| 3 | `lampu_mati` | simpang kehilangan kendali lampu | `lampu_operasional == 0` (hanya ruas ber-lampu) |
| 4 | `perbaikan_jalan` | penutupan lajur karena pekerjaan jalan | `lane_closure == 1` |
| 5 | `keramaian_event` | acara mengubah pola permintaan | `event_flag == 1` |
| 6 | `hujan` | hujan menurunkan kecepatan/kapasitas | `curah_hujan_mm_jam >= 2.0` |
| 7 | `kendaraan_berat` | dominasi truk/bus | `proporsi_roda_6plus >= 0.14` dan `vc_ratio < 0.90` |
| 8 | `volume_puncak` | permintaan > kapasitas tanpa gangguan | `vc_ratio >= 0.70` |
| 9 | `normal` | tidak ada gangguan | selain di atas |

Urutan di atas = urutan evaluasi. Kelas pertama yang cocok menang. Kolom `bottleneck_rule` mencatat
nama aturan yang menang; `bottleneck_secondary` mencatat kandidat kedua (boleh kosong).

## 2. File data (output generator `data/data_synthetic/v4/generate_data_v4.py`)

Semua waktu WIB. Seed tetap `42`. Semua file deterministik.

### 2.1 `data/data_synthetic/v4/intersections.csv` — master, 6 baris

`intersection_id, intersection_name, tipe_persimpangan, jumlah_lengan, koridor, lat, lon, elevasi_m,
cycle_length_s, ada_lampu, kecepatan_bebas_kmh`

- `tipe_persimpangan` ∈ {`perempatan`, `pertigaan`} → 3 perempatan (4 lengan) + 3 pertigaan (3 lengan).
- `cycle_length_s`: perempatan 120, pertigaan 80.
- ID: `INT-001` … `INT-006` (dipakai langsung oleh live state store, tanpa mapping tambahan).

### 2.2 `data/data_synthetic/v4/sections.csv` — master, 30 baris

`section_id, intersection_id, nama_ruas, section_type, approach, arah, panjang_m, jumlah_lajur,
kecepatan_bebas_kmh, kapasitas_smp_per_jam, kapasitas_kendaraan, ruang_per_kendaraan_m`

- `section_type` ∈ {`approach`, `corridor`}: 21 `approach` (pendekat simpang, ber-lampu) + 9 `corridor`
  (ruas antar-simpang / mid-block, tanpa lampu).
- `approach` ∈ {N,E,S,W} untuk approach; kosong untuk corridor.
- `kapasitas_smp_per_jam` = `1900 × jumlah_lajur` (acuan MKJI, dinyatakan sebagai referensi).
- `kapasitas_kendaraan` (daya tampung ruas) = `floor(panjang_m × jumlah_lajur / ruang_per_kendaraan_m)`,
  `ruang_per_kendaraan_m = 7.0`.
- `section_id` untuk corridor = `COR-001` … `COR-009`; `intersection_id` corridor = ID corridor itu
  sendiri (`COR-001` …), sehingga ruas corridor diabaikan oleh live state store (memang tanpa simpang).

### 2.3 `data/data_synthetic/v4/ticks_v4.csv.gz` — seri waktu utama, 302.400 baris (1 menit, 7 hari, 30 ruas)

Kolom (urutan tetap):

```
tick, timestamp_wib, intersection_id, tipe_persimpangan, jumlah_lengan, section_id, nama_ruas,
section_type, approach, jumlah_lajur, panjang_m, kapasitas_smp_per_jam, kapasitas_kendaraan,
vehicle_count_1min, volume_veh_per_hour, avg_speed_kmh, queue_length_veh, wait_time_min,
green_seconds, red_seconds, cycle_length_s, density_percent, vc_ratio, los,
roda_2, roda_3, roda_4, roda_6plus, smp_ekivalen, proporsi_roda_6plus,
weather_condition, weather_temp_c, curah_hujan_mm_jam, tinggi_genangan_cm, durasi_hujan_menit,
accident_count, roadwork_flag, lane_closure, pct_lajur_tertutup, durasi_kerja_jalan_menit,
event_flag, lampu_operasional,
bottleneck_cause, bottleneck_rule, bottleneck_secondary,
target_volume_15m, target_volume_2h, target_volume_4h
```

Keterangan penting:

- `volume_veh_per_hour` = arus jam-an hasil ekstrapolasi tick 1 menit.
- `vc_ratio` = volume dalam **smp/jam** dibanding kapasitas terkoreksi komposisi:
  `vc_ratio = (smp_ekivalen × 60) / (kapasitas_smp_per_jam × (1 − 0,35 × pangsa_roda_2))`.
  Faktor komposisi mencerminkan turunnya kapasitas efektif pada arus didominasi sepeda motor
  (berdasarkan pangsa motor aktual tiap baris).
- `los` ∈ A,B,C,D,E,F dari `vc_ratio`: A ≤ 0,35; B ≤ 0,55; C ≤ 0,75; D ≤ 0,85; E ≤ 1,00; F > 1,00.
- `roda_2/3/4/6plus` = jumlah kendaraan per jenis pada tick itu; `sum(roda_*) == vehicle_count_1min`.
- `smp_ekivalen` = `0,25·roda_2 + 0,50·roda_3 + 1,00·roda_4 + 1,30·roda_6plus` (acuan MKJI).
- `los`/`vc_ratio`/`smp_ekivalen` **turunan**, tidak boleh dipakai sebagai fitur model (lihat §4).
- `cycle_length_s`, `green_seconds`, `red_seconds` = 0 untuk `section_type == corridor` (tanpa sinyal).
- `target_volume_*` = volume 15 menit / 2 jam / 4 jam ke depan (kontrak lama dipertahankan).

### 2.4 `data/data_synthetic/v4/live_replay_7d.csv.gz` — file replay gaya lama, 60.480 baris

Satu baris per (tick, intersection) — agregat seluruh ruas pendekat simpang (sum count/queue,
mean speed/density). Kolom = kontrak lama + tambahan konteks:

```
timestamp_wib, tick, intersectionId, approach, vehicle_count_1min, volume_veh_per_hour, avg_speed_kmh,
queue_length_veh, wait_time_min, green_seconds, density_percent, weather_condition, weather_temp_c,
accident_count, roadwork_flag, event_flag, target_volume_15m, target_volume_2h, target_volume_4h
```

`approach` = `"ALL"`. File ini dipakai `HYBRID_TRAFFIC_DATASET_PATH` sehingga jalur lama
(live metrics + prediksi + rekomendasi hijau) tetap berjalan tanpa perubahan.

## 3. Lapisan backend

### 3.1 Berkas baru (pemilik: agent backend)

| Berkas | Isi |
|---|---|
| `backend/sim/analytics_loader.py` | Loader pandas untuk `ticks_v4.csv.gz` + master CSV, cache, agregasi tick-aware |
| `backend/app/routes/bottlenecks.py` | `GET /api/v1/bottlenecks`, `GET /api/v1/bottlenecks/{intersection_id}` |
| `backend/app/routes/segments.py` | `GET /api/v1/segments`, `GET /api/v1/segments/summary` |
| `backend/app/routes/signals.py` | `GET /api/v1/signals/summary` |
| `backend/app/routes/model_eval.py` | `GET /api/v1/model/evaluation` |
| `backend/tests/test_v4_analytics.py` | Tes skema + anti-kebocoran + endpoint baru |

### 3.2 Berkas lama yang boleh disentuh agent backend

- `backend/app/routes/__init__.py` → daftarkan router baru (tambahan saja).
- `backend/app/state_store.py` → **hanya** `DEFAULT_INTERSECTIONS` (6 simpang v4, nama dari master).
- `backend/sim/intersection_mapping.py` → tambahkan `INT-005`, `INT-006` pada `DEMO_INTERSECTION_SCALE`.
- `backend/core/constants.py` → `DEFAULT_INTERSECTION_COUNT = 6`, tambah daftar 9 kelas penyebab.
- `backend/core/schemas.py` → tambahkan model respons baru (jangan ubah model lama).
- `backend/.env` (lokal) → `HYBRID_TRAFFIC_DATASET_PATH=../data/data_synthetic/v4/live_replay_7d.csv.gz`.

### 3.3 Bentuk respons API (dipakai frontend, jangan diubah tanpa memperbarui dokumen ini)

```
GET /api/v1/bottlenecks?tick=
{
  "tick": 1234, "timestamp_wib": "2026-05-01T20:34:00+07:00",
  "section_count": 30, "affected_section_count": 11,
  "dominant_cause": "hujan",
  "causes": [
    {"cause": "hujan", "sections": 8, "share": 0.267, "avg_vc_ratio": 0.71,
     "avg_queue_veh": 14.2, "avg_wait_time_min": 2.4}
  ],
  "per_intersection": [
    {"intersection_id": "INT-001", "intersection_name": "...", "tipe_persimpangan": "perempatan",
     "dominant_cause": "volume_puncak", "confidence": 0.87,
     "probabilities": {"normal": 0.02, ...},           // 9 kelas, jumlah ≈ 1
     "top3": [{"cause": "volume_puncak", "probability": 0.87}, ...],
     "drivers": ["vc_ratio 0,94", "green 42 s dari siklus 120 s", "hujan 0 mm/jam"]}
  ]
}

GET /api/v1/bottlenecks/{intersection_id}
  → objek per_intersection yang sama + "history": [{tick, timestamp_wib, dominant_cause, confidence,
    vc_ratio, queue_length_veh, avg_speed_kmh}] (60 tick terakhir) + "sections": [...]

GET /api/v1/segments?tick=&tipe=&section_type=
{
  "tick": 1234, "count": 30, "total_capacity_vehicles": 4820,
  "items": [
    {"section_id": "SEC-001-N", "nama_ruas": "...", "section_type": "approach",
     "intersection_id": "INT-001", "tipe_persimpangan": "perempatan", "approach": "N",
     "panjang_m": 420, "jumlah_lajur": 3, "kapasitas_smp_per_jam": 5700, "kapasitas_kendaraan": 180,
     "volume_veh_per_hour": 3910, "vc_ratio": 0.686, "los": "C",
     "avg_speed_kmh": 32.4, "queue_length_veh": 46, "wait_time_min": 2.7,
     "kendaraan": {"roda_2": 2310, "roda_3": 120, "roda_4": 1280, "roda_6plus": 200, "total": 3910,
                   "smp_ekivalen": 3055.0,
                   "persen": {"roda_2": 0.591, "roda_3": 0.031, "roda_4": 0.327, "roda_6plus": 0.051}},
     "bottleneck_cause": "volume_puncak", "penyebab_dominan": "perbaikan_jalan"}
  ]
}

GET /api/v1/segments/summary
{
  "tick": 1234, "section_count": 30, "approach_count": 21, "corridor_count": 9,
  "total_capacity_vehicles": 4820, "total_capacity_smp_per_jam": 142500,
  "total_kendaraan": {"roda_2": ..., "roda_3": ..., "roda_4": ..., "roda_6plus": ..., "total": ...,
                      "persen": {...}, "smp_ekivalen": ...},
  "avg_vc_ratio": 0.61, "avg_speed_kmh": 34.1,
  "los_distribution": {"A": 4, "B": 7, "C": 9, "D": 5, "E": 3, "F": 2},
  "per_intersection": [{"intersection_id": "INT-001", "section_count": 5, ...}]
}

GET /api/v1/signals/summary?scope=all|perempatan|pertigaan
{
  "scope": "all", "timestamp_wib": "...", "intersection_count": 6, "section_count": 21,
  "cycle_length_s": 100.0, "avg_green_s": 26.4, "avg_red_s": 73.6, "avg_wait_time_min": 2.31,
  "avg_queue_veh": 21.7, "avg_delay_s": 78.5,
  "items": [{"scope": "perempatan", "intersection_count": 3, "section_count": 12,
             "cycle_length_s": 120.0, "avg_green_s": 30.0, "avg_red_s": 90.0, ...}],
  "per_intersection": [{"intersection_id": "INT-001", "intersection_name": "...",
                        "tipe_persimpangan": "perempatan", "jumlah_lengan": 4,
                        "cycle_length_s": 120, "avg_green_s": 30.0, "avg_red_s": 90.0,
                        "avg_wait_time_min": 2.4, "avg_queue_veh": 24.0, "avg_delay_s": 71.0}]
}

GET /api/v1/model/evaluation
{
  "available": true, "model_name": "hist_gradient_boosting", "trained_at": "...", "classes": [9 nama],
  "split": {"train": "hari 1-5", "validation": "hari 6", "test": "hari 7",
            "protocol": "temporal, tanpa pengacakan"},
  "metrics": {"macro_f1": ..., "balanced_accuracy": ..., "accuracy": ...},
  "baselines": {
    "majority_class": {"model": "...", "macro_f1": ..., "balanced_accuracy": ..., "accuracy": ...},
    "rule_based":    {"model": "...", "macro_f1": ..., "balanced_accuracy": ..., "accuracy": ...}},
  "per_class": [{"cause": "banjir", "precision": ..., "recall": ..., "f1": ..., "support": ...}],
  "confusion_matrix": {"labels": [9 nama], "matrix": [[...]]},
  "feature_importance": [{"feature": "...", "importance": ...}],
  "leakage_guard": ["..."], "limitations": ["..."], "artifacts": {"model": "...", "metrics": "..."}
}
```

Default `tick` kosong = tick terakhir yang diputar replay. `confidence` = probabilitas kelas teratas
dari classifier; bila artefak model belum ada, backend memakai fallback aturan dan mengirim
`"model_available": false` + confidence 0.

## 4. Kontrak model (pemilik: agent model)

- Berkas: `backend/ml/bottleneck/train_bottleneck.py`, artefak
  `backend/ml/bottleneck/artifacts/bottleneck_classifier.joblib`, `metrics.json`, `model_card.md`.
- Fitur **boleh** dipakai: `vehicle_count_1min`, `volume_veh_per_hour`, `avg_speed_kmh`,
  `queue_length_veh`, `wait_time_min`, `green_seconds`, `cycle_length_s`, `density_percent`,
  `jumlah_lajur`, `panjang_m`, `kapasitas_smp_per_jam`, `proporsi_roda_6plus`, `hour`, `minute`,
  `day_of_week`, `is_weekend`, `weather_temp_c`, `section_type_is_corridor`, `tipe_is_perempatan`,
  plus lag/rolling (1, 5, 15, 30, 60) dari volume, queue, dan kecepatan.
- Fitur **dilarang** (kebocoran label): `bottleneck_cause`, `bottleneck_rule`, `bottleneck_secondary`,
  `weather_condition`, `curah_hujan_mm_jam`, `tinggi_genangan_cm`, `durasi_hujan_menit`, `lane_closure`,
  `pct_lajur_tertutup`, `durasi_kerja_jalan_menit`, `event_flag`, `lampu_operasional`,
  `accident_count`, `roadwork_flag`, `vc_ratio`, `los`, `smp_ekivalen`.
  (`weather_condition` dilarang karena nilainya menentukan kelas `hujan`; daftar ini ditegakkan
  otomatis oleh `backend/ml/bottleneck/features.py::assert_no_leakage`.)
- Fitur wajib diambil dari `backend/ml/bottleneck/features.py` (`FEATURE_COLUMNS`, 46 kolom) sehingga
  pelatihan dan inferensi tidak pernah berbeda urutan/nama kolom.
- Split: hari 1-5 latih, hari 6 validasi, hari 7 uji (berdasarkan `timestamp_wib`, tanpa acak).
- Metrik utama `macro_f1`; wajib ada per kelas, confusion matrix, dan 2 baseline:
  `majority_class` (DummyClassifier) dan `rule_based` (heuristik ambang tanpa model).
- Skema `metrics.json`:

```
{"model_name": "...", "trained_at": "...", "n_train": 0, "n_validation": 0, "n_test": 0,
 "classes": ["banjir", "hujan", "kecelakaan", "kendaraan_berat", "keramaian_event", "lampu_mati",
             "normal", "perbaikan_jalan", "volume_puncak"],
 "feature_columns": [...], "forbidden_columns": [...],
 "metrics": {"macro_f1": 0.0, "balanced_accuracy": 0.0, "accuracy": 0.0},
 "baselines": {"majority_class": {...}, "rule_based": {...}},
 "per_class": [{"cause": "banjir", "precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}],
 "confusion_matrix": {"labels": [...], "matrix": [[...]]},
 "feature_importance": [{"feature": "...", "importance": 0.0}],
 "leakage_guard": [...], "limitations": [...]}
```

### 4.1 Antarmuka runtime (pemilik: jalur utama, jangan diedit agent)

`backend/ml/bottleneck/classifier.py` menyediakan:

```python
class BottleneckClassifier:
    available: bool                     # artefak termuat atau tidak
    model_name: str
    def predict_proba(self, frame: "pandas.DataFrame") -> "numpy.ndarray"  # kolom = self.classes
    @property
    def classes(self) -> list[str]
bottleneck_classifier = BottleneckClassifier()
```

Agent backend mengimpor objek itu; agent model hanya menghasilkan artefak + `metrics.json`.
Agent backend **tidak** mengedit classifier.py, agent model **tidak** mengedit route apa pun.
```

## 5. Kontrak frontend (pemilik: agent frontend)

Tipe TypeScript di `frontend/src/types/index.ts` (tambahan, jangan ubah tipe lama):
`BottleneckResponse`, `BottleneckCause`, `BottleneckPerIntersection`, `SegmentItem`, `SegmentVehicleMix`,
`SegmentsResponse`, `SegmentsSummaryResponse`, `SignalsSummaryResponse`, `SignalPerIntersection`,
`ModelEvaluationResponse`, `ModelBaselineScore`, `ModelPerClassScore` — bentuknya persis respons §3.3.

Komponen baru:
`frontend/src/components/dashboard/BottleneckPanel.tsx`,
`frontend/src/components/dashboard/SignalTimingCard.tsx`,
`frontend/src/components/dashboard/SegmentTable.tsx`,
`frontend/src/pages/ModelEvaluation.tsx`.

Hook baru di `frontend/src/hooks/useTraffixData.ts`: `useBottlenecks`, `useSegments`,
`useSegmentsSummary`, `useSignalsSummary`, `useModelEvaluation` (React Query, polling 5 detik).

Wajib tampil di UI: badge **"data sintetis · seed 42"** pada panel penyebab dan halaman evaluasi.
