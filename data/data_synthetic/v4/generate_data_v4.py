"""Traffix v4 dataset generator — multi-intersection, sections, bottleneck-cause labels.

Deterministic (seed 42). Produces, under ``data/data_synthetic/v4/``:

- ``intersections.csv``    master, 6 intersections (3 perempatan + 3 pertigaan)
- ``sections.csv``         master, 30 sections (21 approach + 9 corridor)
- ``ticks_v4.csv.gz``      section-level 1-minute series, 302.400 rows
- ``live_replay_7d.csv.gz`` intersection-level replay file (legacy shape), 60.480 rows

Contract: ``docs/SCHEMA-v4.md`` — do not rename columns without updating it.

Usage:
    python generate_data_v4.py [--days 7] [--seed 42] [--out DIR]
"""
from __future__ import annotations

import argparse
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

log = logging.getLogger("generate_v4")

WIB = ZoneInfo("Asia/Jakarta")
DEFAULT_SEED = 42
START_DATE = datetime(2026, 5, 1, 0, 0, 0, tzinfo=WIB)
DEFAULT_DAYS = 7
DEFAULT_OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- kalibrasi
SAT_FLOW_VPH = 1900          # smp/jam/lajur pada kondisi jenuh (acuan MKJI, untuk kolom kapasitas)
SAT_FLOW_VEH_PER_LANE = 3300  # kendaraan/jam/lajur (setara 1900 smp/jam pada komposisi ±0,57 smp/kendaraan)
FREE_FLOW_SPEED = 60.0
SPACE_PER_VEHICLE_M = 7.0    # ruang rata-rata per kendaraan saat macet penuh
LANE_WIDTH_M = 3.5

# Bobot smp per jenis kendaraan (acuan MKJI 1997, dapat dikalibrasi)
SMP_WEIGHT = {"roda_2": 0.25, "roda_3": 0.50, "roda_4": 1.00, "roda_6plus": 1.30}

CYCLE_SECONDS = {"perempatan": 120, "pertigaan": 80}
GREEN_BOUNDS = {"perempatan": (20, 50), "pertigaan": (18, 45)}
YELLOW_SECONDS = 3

MORNING_PEAK = (6.0, 7.5, 9.0)
EVENING_PEAK = (16.0, 17.5, 19.0)
WEEKEND_FACTOR = 0.65
OFF_PEAK_FACTOR = 0.32
FLOW_NOISE = 0.15

WEATHER_TYPES = ["Clear", "Cloudy", "Hot", "Rain"]
WEATHER_PROBS = [0.35, 0.30, 0.20, 0.15]
WEATHER_TEMP_RANGE = {
    "Clear": (28.0, 33.0), "Cloudy": (26.0, 31.0), "Hot": (32.0, 36.0), "Rain": (23.0, 29.0),
}
WEATHER_SPEED_REDUCTION = {"Clear": 0.0, "Cloudy": 2.0, "Hot": 0.0, "Rain": 9.0}
WEATHER_DEMAND_MULTIPLIER = {"Clear": 1.0, "Cloudy": 0.95, "Hot": 1.05, "Rain": 0.85}
WEATHER_DENSITY_MULTIPLIER = {"Clear": 1.0, "Cloudy": 1.0, "Hot": 1.0, "Rain": 1.25}

# Peluang kejadian per tick (1 menit) per simpang
ACCIDENT_PROB, ACCIDENT_MIN, ACCIDENT_MAX = 0.0008, 10, 45
ROADWORK_PROB, ROADWORK_MIN, ROADWORK_MAX = 0.00016, 120, 360
EVENT_PROB, EVENT_MIN, EVENT_MAX = 0.00030, 60, 180
OUTAGE_PROB, OUTAGE_MIN, OUTAGE_MAX = 0.00060, 20, 90
FLOOD_PROB, FLOOD_MIN, FLOOD_MAX = 0.006, 45, 200

ACCIDENT_CAPACITY_MULT = 0.55
ROADWORK_CAPACITY_MULT = 0.70
FLOOD_CAPACITY_MULT = 0.35
OUTAGE_CAPACITY_MULT = 0.45
EVENT_DEMAND_MULTIPLIER = 1.3

FLOOD_MIN_RAIN_MM_H = 8.0     # genangan hanya mungkin saat hujan deras
FLOOD_MAX_ELEVATION_M = 3.5   # simpang dengan elevasi rendah rawan genangan

# Jadwal kejadian minimum per hari — menjamin semua kelas hadir di setiap hari
# (termasuk hari validasi dan hari uji, sehingga evaluasi tidak kosong kelas).
SCHEDULED_MIN_PER_DAY: dict[str, tuple[int, str]] = {
    "accident": (8, "accident"),
    "roadwork": (2, "roadwork"),
    "event": (3, "event"),
    "outage": (3, "outage"),
    "flood": (1, "flood"),      # per simpang rawan genangan
}
SCHEDULED_DURATION: dict[str, tuple[int, int]] = {
    "accident": (ACCIDENT_MIN, ACCIDENT_MAX),
    "roadwork": (ROADWORK_MIN, ROADWORK_MAX),
    "event": (EVENT_MIN, EVENT_MAX),
    "outage": (OUTAGE_MIN, OUTAGE_MAX),
    "flood": (FLOOD_MIN, FLOOD_MAX),
}

# ---------------------------------------------------------------- master data
INTERSECTIONS = [
    # id, nama, tipe, koridor, lat, lon, elevasi_m, demand per lengan (veh/min pada puncak)
    ("INT-001", "Simpang Meruya Utara", "perempatan", "Jakarta Barat", -6.1870, 106.7350, 2.4,
     {"N": 31.0, "E": 17.0, "S": 28.0, "W": 15.0}),
    ("INT-002", "Simpang Tomang", "perempatan", "Jakarta Barat", -6.1760, 106.7900, 3.1,
     {"N": 27.0, "E": 21.0, "S": 25.0, "W": 19.0}),
    ("INT-003", "Pertigaan Cawang", "pertigaan", "Jakarta Timur", -6.2400, 106.8700, 5.2,
     {"N": 26.0, "E": 20.0, "W": 22.0}),
    ("INT-004", "Pertigaan Grogol", "pertigaan", "Jakarta Barat", -6.1660, 106.7890, 2.8,
     {"N": 24.0, "E": 18.0, "W": 20.0}),
    ("INT-005", "Simpang Kebayoran", "perempatan", "Jakarta Selatan", -6.2440, 106.7990, 4.4,
     {"N": 29.0, "E": 16.0, "S": 26.0, "W": 14.0}),
    ("INT-006", "Pertigaan Bekasi Barat", "pertigaan", "Bekasi", -6.2180, 106.9890, 2.1,
     {"N": 22.0, "E": 17.0, "W": 19.0}),
]

# Koridor antar-simpang (mid-block, tanpa lampu)
CORRIDORS = [
    ("COR-001", "Jl. Meruya - Tomang", "INT-001", "INT-002", 620, 3),
    ("COR-002", "Jl. Meruya - Kebayoran", "INT-001", "INT-005", 540, 2),
    ("COR-003", "Jl. Tomang - Cawang", "INT-002", "INT-003", 780, 3),
    ("COR-004", "Jl. Cawang - Bekasi Barat", "INT-003", "INT-006", 700, 2),
    ("COR-005", "Jl. Grogol - Kebayoran", "INT-004", "INT-005", 460, 2),
    ("COR-006", "Jl. Kebayoran - Bekasi Barat", "INT-005", "INT-006", 660, 2),
    ("COR-007", "Jl. Tomang - Grogol", "INT-002", "INT-004", 380, 2),
    ("COR-008", "Jl. Meruya - Grogol", "INT-001", "INT-004", 510, 3),
    ("COR-009", "Jl. Cawang - Grogol", "INT-003", "INT-004", 590, 2),
]

VEHICLE_SHARE = {
    # section_type: (roda_2, roda_3, roda_4, roda_6plus)
    "approach": (0.560, 0.030, 0.345, 0.065),
    "corridor": (0.490, 0.025, 0.375, 0.110),
}

# Skala permintaan global (1,0 = puncak mendekati kapasitas simpang ber-lampu)
DEMAND_SCALE = 1.55
# Bagian lalu lintas kedua ujung simpang yang memakai satu tautan koridor
CORRIDOR_LINK_FACTOR = 0.55


def raised_cosine(x: float, start: float, peak: float, end: float) -> float:
    """Smooth 0→1→0 peak curve."""
    if x <= start or x >= end:
        return 0.0
    if x <= peak:
        half = peak - start
        return 0.5 * (1 - math.cos(math.pi * (x - start) / half)) if half else 1.0
    half = end - peak
    return 0.5 * (1 + math.cos(math.pi * (x - peak) / half)) if half else 1.0


def time_factor(hour_value: float, is_weekend: bool) -> float:
    """Demand factor by time of day and weekend."""
    morning = raised_cosine(hour_value, *MORNING_PEAK)
    evening = raised_cosine(hour_value, *EVENING_PEAK)
    midday = raised_cosine(hour_value, 10.5, 12.5, 14.5) * 0.55
    result = OFF_PEAK_FACTOR + (1.0 - OFF_PEAK_FACTOR) * max(morning, evening, midday)
    return result * (WEEKEND_FACTOR if is_weekend else 1.0)


def build_master_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the intersection and section master tables."""
    intersection_rows = []
    section_rows = []
    for idx, (iid, name, tipe, corridor, lat, lon, elev, demand) in enumerate(INTERSECTIONS, start=1):
        lanes = {"perempatan": 3, "pertigaan": 2}
        intersection_rows.append({
            "intersection_id": iid,
            "intersection_name": name,
            "tipe_persimpangan": tipe,
            "jumlah_lengan": len(demand),
            "koridor": corridor,
            "lat": lat,
            "lon": lon,
            "elevasi_m": elev,
            "cycle_length_s": CYCLE_SECONDS[tipe],
            "ada_lampu": 1,
            "kecepatan_bebas_kmh": FREE_FLOW_SPEED,
        })
        for approach in demand:
            lanes_n = lanes[tipe] if approach in ("N", "S") else max(2, lanes[tipe] - 1)
            length_m = 150 + (idx * 37 + ord(approach) * 11) % 450
            cap_smp = SAT_FLOW_VPH * lanes_n
            section_rows.append({
                "section_id": f"SEC-{idx:03d}-{approach}",
                "intersection_id": iid,
                "nama_ruas": f"Pendekat {approach} {name}",
                "section_type": "approach",
                "approach": approach,
                "arah": approach,
                "panjang_m": int(length_m),
                "jumlah_lajur": lanes_n,
                "kecepatan_bebas_kmh": FREE_FLOW_SPEED,
                "kapasitas_smp_per_jam": cap_smp,
                "kapasitas_kendaraan": int(length_m * lanes_n / SPACE_PER_VEHICLE_M),
                "ruang_per_kendaraan_m": SPACE_PER_VEHICLE_M,
            })
    for sid, nama, a, b, panjang, lajur in CORRIDORS:
        cap_smp = SAT_FLOW_VPH * lajur
        section_rows.append({
            "section_id": sid,
            "intersection_id": sid,          # ruas mid-block tidak terikat simpang
            "nama_ruas": nama,
            "section_type": "corridor",
            "approach": "",
            "arah": f"{a}->{b}",
            "panjang_m": int(panjang),
            "jumlah_lajur": lajur,
            "kecepatan_bebas_kmh": FREE_FLOW_SPEED,
            "kapasitas_smp_per_jam": cap_smp,
            "kapasitas_kendaraan": int(panjang * lajur / SPACE_PER_VEHICLE_M),
            "ruang_per_kendaraan_m": SPACE_PER_VEHICLE_M,
        })
    return pd.DataFrame(intersection_rows), pd.DataFrame(section_rows)


def simulate(days: int, seed: int) -> pd.DataFrame:
    """Run the deterministic multi-intersection simulation."""
    rng = np.random.default_rng(seed)
    ticks = days * 24 * 60

    # per-intersection incident state sementara (dict id -> dict)
    state = {}
    for iid, name, tipe, _corr, _lat, _lon, elev, demand in INTERSECTIONS:
        state[iid] = {
            "tipe": tipe,
            "elevasi": elev,
            "demand": demand,
            "cycle": CYCLE_SECONDS[tipe],
            "accident": 0, "roadwork": 0, "event": 0, "outage": 0, "flood": 0,
            "lane_closure": 0, "durasi_kerja": 0,
        }

    weather = "Clear"
    weather_left = 0
    temp = 30.0
    rain_mm = 0.0
    rain_left = 0
    daily_events: dict[int, dict[str, int]] = {}
    rain_minutes_today: dict[int, int] = {}

    queues: dict[str, float] = {}
    sections: dict[str, dict] = {}
    for idx, (iid, name, tipe, _corr, _lat, _lon, _elev, demand) in enumerate(INTERSECTIONS, start=1):
        lanes = 3 if tipe == "perempatan" else 2
        for approach in demand:
            lanes_n = lanes if approach in ("N", "S") else max(2, lanes - 1)
            sid = f"SEC-{idx:03d}-{approach}"
            queues[sid] = 0.0
            sections[sid] = {
                "section_id": sid, "section_type": "approach", "intersection_id": iid,
                "approach": approach, "tipe": tipe, "lanes": lanes_n, "cycle": CYCLE_SECONDS[tipe],
                "length_m": 150 + (idx * 37 + ord(approach) * 11) % 450,
                "cap_smp": SAT_FLOW_VPH * lanes_n,
                "peak": demand[approach],
            }
    for sid, nama, a, b, panjang, lajur in CORRIDORS:
        queues[sid] = 0.0
        sections[sid] = {
            "section_id": sid, "section_type": "corridor", "intersection_id": sid,
            "approach": "", "tipe": "corridor", "lanes": lajur, "cycle": 0,
            "length_m": panjang, "cap_smp": SAT_FLOW_VPH * lajur,
            "peak": None, "ends": (a, b),
        }

    section_ids = list(sections)
    records: list[dict] = []

    for tick in range(ticks):
        now = START_DATE + timedelta(minutes=tick)
        hour_value = now.hour + now.minute / 60.0
        is_weekend = now.weekday() >= 5
        tf = time_factor(hour_value, is_weekend)
        day_index = tick // 1440
        day_counts = daily_events.setdefault(day_index, {})
        rain_minutes_today.setdefault(day_index, 0)

        # ---- cuaca
        if weather_left <= 0:
            weather = str(rng.choice(WEATHER_TYPES, p=WEATHER_PROBS))
            weather_left = int(rng.integers(30, 210))
            lo, hi = WEATHER_TEMP_RANGE[weather]
            temp = float(rng.uniform(lo, hi))
        else:
            weather_left -= 1
            lo, hi = WEATHER_TEMP_RANGE[weather]
            temp = float(min(hi, max(lo, temp + rng.normal(0, 0.12))))

        # ---- jaminan hujan harian (minimal satu episode hujan deras per hari)
        if (
            now.minute == 0
            and now.hour >= 14
            and rain_minutes_today[day_index] == 0
        ):
            weather = "Rain"
            weather_left = 240
            rain_left = 0

        if weather == "Rain":
            if rain_left <= 0:
                rain_left = int(rng.integers(25, 160))
                rain_mm = float(rng.uniform(2.0, 24.0))
            rain_left -= 1
        else:
            rain_left = 0
            rain_mm = 0.0
        rain_active = rain_mm >= 2.0
        if rain_active:
            rain_minutes_today[day_index] += 1

        # ---- kejadian per simpang
        for iid, st in state.items():
            for key, prob, lo, hi in (
                ("accident", ACCIDENT_PROB, ACCIDENT_MIN, ACCIDENT_MAX),
                ("roadwork", ROADWORK_PROB, ROADWORK_MIN, ROADWORK_MAX),
                ("event", EVENT_PROB, EVENT_MIN, EVENT_MAX),
                ("outage", OUTAGE_PROB, OUTAGE_MIN, OUTAGE_MAX),
            ):
                if st[key] > 0:
                    st[key] -= 1
                elif rng.random() < prob:
                    st[key] = int(rng.integers(lo, hi)) + 1
                    day_counts[key] = day_counts.get(key, 0) + 1
            if st["roadwork"] > 0:
                st["lane_closure"] = 1
                st["durasi_kerja"] = st["roadwork"]
            else:
                st["lane_closure"] = 0
                st["durasi_kerja"] = 0
            if st["flood"] > 0:
                st["flood"] -= 1
            elif rain_mm >= FLOOD_MIN_RAIN_MM_H and st["elevasi"] <= FLOOD_MAX_ELEVATION_M:
                if rng.random() < FLOOD_PROB:
                    st["flood"] = int(rng.integers(FLOOD_MIN, FLOOD_MAX)) + 1
                    day_counts["flood"] = day_counts.get("flood", 0) + 1

        # ---- jadwal minimum kejadian harian (rotasi simpang)
        if now.minute == 0:
            for cls, (target_per_day, key) in SCHEDULED_MIN_PER_DAY.items():
                expected = math.ceil(target_per_day * max(1, now.hour) / 24.0)
                if day_counts.get(cls, 0) >= expected:
                    continue
                if cls == "flood":
                    eligible = [
                        idx for idx, item in enumerate(INTERSECTIONS)
                        if item[6] <= FLOOD_MAX_ELEVATION_M
                    ]
                    idx = eligible[(day_index + now.hour) % len(eligible)]
                else:
                    idx = (day_index + now.hour + len(cls)) % len(INTERSECTIONS)
                st = state[INTERSECTIONS[idx][0]]
                if st[key] > 0:
                    continue
                lo, hi = SCHEDULED_DURATION[key]
                st[key] = int(rng.integers(lo, hi)) + 1
                day_counts[cls] = day_counts.get(cls, 0) + 1

        # ---- permintaan per ruas approach
        approach_demand: dict[str, float] = {}
        for iid, st in state.items():
            event_f = EVENT_DEMAND_MULTIPLIER if st["event"] > 0 else 1.0
            hot_boost = 1.12 if weather == "Hot" and 11.0 <= hour_value <= 15.0 else 1.0
            for approach, peak in st["demand"].items():
                base = (peak * DEMAND_SCALE * tf * WEATHER_DEMAND_MULTIPLIER[weather]
                        * event_f * hot_boost)
                sigma = max(base * FLOW_NOISE, 0.5)
                approach_demand[f"{iid}:{approach}"] = max(0.0, float(rng.normal(base, sigma)))

        # ---- alokasi hijau per simpang
        green_by_section: dict[str, float] = {}
        for iid, st in state.items():
            cycle = st["cycle"]
            lo_g, hi_g = GREEN_BOUNDS[st["tipe"]]
            demand_vals = {ap: approach_demand[f"{iid}:{ap}"] for ap in st["demand"]}
            total = sum(demand_vals.values()) or 1.0
            for ap, val in demand_vals.items():
                if st["outage"] > 0:
                    green_by_section[f"{iid}:{ap}"] = 0.0
                else:
                    secs = cycle * val / total
                    green_by_section[f"{iid}:{ap}"] = float(min(hi_g, max(lo_g, secs)))
            # corridor di sekitar simpang mengikuti siklus simpang (tanpa kendali)
            for sid, sec in sections.items():
                if sec["section_type"] == "corridor" and iid in sec["ends"]:
                    green_by_section.setdefault(sid, float(cycle))

        # ---- simulasi antrean + metrik per ruas
        for sid, sec in sections.items():
            is_corridor = sec["section_type"] == "corridor"
            iid = sec["intersection_id"]
            st = state.get(iid)

            if is_corridor:
                ends = sec["ends"]
                pair = []
                for end in ends:
                    end_state = state[end]
                    pair.append(sum(
                        approach_demand[f"{end}:{ap}"] for ap in end_state["demand"]
                    ))
                arrivals = max(0.0, (sum(pair) / 2.0) * CORRIDOR_LINK_FACTOR * (sec["lanes"] / 2.0))
                green = float(sec["cycle"]) if sec["cycle"] else 0.0
                cycle = 0.0
                accident = roadwork = event_f = outage = flood = 0
                for end in ends:
                    end_state = state[end]
                    accident = max(accident, end_state["accident"])
                    roadwork = max(roadwork, end_state["roadwork"])
                    event_f = max(event_f, end_state["event"])
                    outage = max(outage, end_state["outage"])
                    flood = max(flood, end_state["flood"])
                cap_mult = 1.0
                if accident:
                    cap_mult *= ACCIDENT_CAPACITY_MULT
                if roadwork:
                    cap_mult *= ROADWORK_CAPACITY_MULT
                if flood:
                    cap_mult *= FLOOD_CAPACITY_MULT
                if weather == "Rain":
                    cap_mult *= 0.92
                cap_per_min = SAT_FLOW_VEH_PER_LANE * sec["lanes"] / 60.0 * cap_mult
                green_ratio_cap = 1.0
                lane_closure = 1 if roadwork else 0
                pct_lajur = 0.35 if roadwork else 0.0
                durasi_kerja = max(state[e]["durasi_kerja"] for e in ends)
                lampu_ok = 1
            else:
                arrivals = approach_demand[f"{iid}:{sec['approach']}"]
                cycle = float(sec["cycle"])
                green = green_by_section.get(f"{iid}:{sec['approach']}", 0.0)
                accident = st["accident"]
                roadwork = st["roadwork"]
                event_f = st["event"]
                outage = st["outage"]
                flood = st["flood"]
                lane_closure = st["lane_closure"]
                pct_lajur = 0.35 if lane_closure else 0.0
                durasi_kerja = st["durasi_kerja"]
                lampu_ok = 0 if outage > 0 else 1
                cap_mult = 1.0
                if accident:
                    cap_mult *= ACCIDENT_CAPACITY_MULT
                if roadwork:
                    cap_mult *= ROADWORK_CAPACITY_MULT
                if flood:
                    cap_mult *= FLOOD_CAPACITY_MULT
                if outage:
                    cap_mult *= OUTAGE_CAPACITY_MULT
                if weather == "Rain":
                    cap_mult *= 0.92
                effective_green = green if green > 0 else cycle  # lampu mati -> arus tanpa kendali
                green_ratio_cap = (effective_green / cycle) if cycle else 1.0
                # kapasitas nyata (kendaraan/menit): arus jenuh lajur x pangsa hijau x faktor kejadian
                cap_per_min = (
                    SAT_FLOW_VEH_PER_LANE * sec["lanes"] / 60.0 * green_ratio_cap * cap_mult
                )

            # antrean dibatasi daya tampung ruas (storage): kelebihan permintaan terdorong keluar (diversi)
            storage = max(1, int(sec["length_m"] * sec["lanes"] / SPACE_PER_VEHICLE_M))
            queues[sid] = min(float(storage), queues[sid] + arrivals * (1.0 + (0.04 if flood else 0.0)))
            departures = min(queues[sid], cap_per_min)
            queues[sid] = max(0.0, queues[sid] - departures)
            queue = queues[sid]

            density = 100.0 * queue / storage
            density = float(max(0.0, min(100.0, density + rng.normal(0, 1.5))))

            # kecepatan: turun mengikuti rasio volume/kapasitas (bukan hanya kepadatan ruas),
            # ditambah penalti cuaca dan kejadian. Jenuh -> 20-25 km/jam, lengang -> 50-55.
            vc_pre = float(arrivals / max(cap_per_min, 0.1))
            speed = FREE_FLOW_SPEED * (1.0 - 0.75 * min(1.0, vc_pre) ** 1.5)
            speed -= WEATHER_SPEED_REDUCTION[weather]
            if flood:
                speed -= 15.0
            if accident:
                speed -= 10.0
            if roadwork:
                speed -= 4.0
            if outage:
                speed -= 6.0
            speed = float(max(6.0, min(FREE_FLOW_SPEED, speed + rng.normal(0, 1.2))))

            # komposisi kendaraan
            total = int(round(arrivals))
            share = VEHICLE_SHARE[sec["section_type"]]
            night_boost = 0.05 if (now.hour >= 21 or now.hour < 5) else 0.0
            s = np.array([
                share[0] + rng.normal(0, 0.02),
                share[1] + rng.normal(0, 0.004),
                share[2] + rng.normal(0, 0.015),
                max(0.005, share[3] + night_boost + rng.normal(0, 0.010)),
            ])
            s = np.clip(s, 0.001, None)
            s = s / s.sum()
            counts = [int(round(total * x)) for x in s]
            diff = total - sum(counts)
            counts[2] = max(0, counts[2] + diff)  # selisih masuk ke roda 4
            roda_2, roda_3, roda_4, roda_6plus = counts
            smp = round(roda_2 * SMP_WEIGHT["roda_2"] + roda_3 * SMP_WEIGHT["roda_3"]
                        + roda_4 * SMP_WEIGHT["roda_4"] + roda_6plus * SMP_WEIGHT["roda_6plus"], 2)
            proporsi_6 = round(roda_6plus / total, 4) if total else 0.0

            # volume terhadap kapasitas nyata (kendaraan/jam); kejadian ikut menurunkan kapasitas
            volume_vph = float(round(arrivals * 60.0, 2))
            vc_ratio = float(min(3.0, volume_vph / max(cap_per_min * 60.0, 1.0)))
            los = _los(vc_ratio)

            # waktu tunggu: tundaan sinyal (uniform delay Webster/HCM) untuk ruas ber-lampu,
            # tundaan perjalanan untuk ruas antar-simpang (mid-block), keduanya ditambah
            # penalti kejadian. Nilai dalam menit.
            incident_penalty_s = 0.0
            if flood:
                incident_penalty_s += 90.0
            if accident:
                incident_penalty_s += 75.0
            if roadwork:
                incident_penalty_s += 30.0
            if outage:
                incident_penalty_s += 45.0

            if is_corridor:
                travel_actual_s = (sec["length_m"] / 1000.0) / max(speed, 5.0) * 3600.0
                travel_free_s = (sec["length_m"] / 1000.0) / FREE_FLOW_SPEED * 3600.0
                wait_time = (max(0.0, travel_actual_s - travel_free_s) + incident_penalty_s) / 60.0
            else:
                green_ratio = green / cycle if cycle else 1.0
                saturation = min(1.0, vc_ratio)
                uniform_s = (
                    0.5 * cycle * (1.0 - green_ratio) ** 2
                    / max(0.15, 1.0 - saturation * green_ratio)
                )
                overflow_s = max(0.0, vc_ratio - 1.0) * cycle * 1.5
                wait_time = (uniform_s + overflow_s + incident_penalty_s) / 60.0
            wait_time = float(round(min(15.0, max(0.0, wait_time)), 3))

            genangan = 0.0
            if flood:
                genangan = float(round(rng.uniform(15.0, 45.0), 1))

            records.append({
                "tick": tick,
                "timestamp_wib": now.isoformat(),
                "intersection_id": iid if not is_corridor else sec["intersection_id"],
                "tipe_persimpangan": "corridor" if is_corridor else sec["tipe"],
                "jumlah_lengan": 0 if is_corridor else len(state[iid]["demand"]) if not is_corridor else 0,
                "section_id": sid,
                "nama_ruas": f"Pendekat {sec['approach']} {iid}" if not is_corridor else _corridor_name(sid),
                "section_type": sec["section_type"],
                "approach": sec["approach"],
                "jumlah_lajur": sec["lanes"],
                "panjang_m": sec["length_m"],
                "kapasitas_smp_per_jam": sec["cap_smp"],
                "kapasitas_kendaraan": int(sec["length_m"] * sec["lanes"] / SPACE_PER_VEHICLE_M),
                "vehicle_count_1min": total,
                "volume_veh_per_hour": volume_vph,
                "avg_speed_kmh": round(speed, 2),
                "queue_length_veh": int(math.ceil(queue)),
                "wait_time_min": round(wait_time, 3),
                "green_seconds": int(round(green)),
                "red_seconds": int(max(0, (cycle or 0) - green - (YELLOW_SECONDS if cycle else 0))),
                "cycle_length_s": int(cycle),
                "density_percent": round(density, 2),
                "vc_ratio": round(vc_ratio, 3),
                "los": los,
                "roda_2": roda_2, "roda_3": roda_3, "roda_4": roda_4, "roda_6plus": roda_6plus,
                "smp_ekivalen": smp,
                "proporsi_roda_6plus": proporsi_6,
                "weather_condition": weather,
                "weather_temp_c": round(temp, 1),
                "curah_hujan_mm_jam": round(rain_mm if rain_active else 0.0, 2),
                "tinggi_genangan_cm": genangan,
                "durasi_hujan_menit": int(rain_left if rain_active else 0),
                "accident_count": int(accident > 0),
                "roadwork_flag": int(roadwork > 0),
                "lane_closure": int(lane_closure),
                "pct_lajur_tertutup": pct_lajur,
                "durasi_kerja_jalan_menit": int(durasi_kerja),
                "event_flag": int(event_f > 0),
                "lampu_operasional": int(lampu_ok),
                "bottleneck_cause": "",
                "bottleneck_rule": "",
                "bottleneck_secondary": "",
                "target_volume_15m": None,
                "target_volume_2h": None,
                "target_volume_4h": None,
                "_hour": now.hour,
                "_dow": now.weekday(),
                "_is_weekend": int(is_weekend),
            })

        if (tick + 1) % 1440 == 0:
            log.info("hari %d/%d selesai (%d baris)", (tick + 1) // 1440, days, len(records))

    df = pd.DataFrame.from_records(records)
    return df


_CORRIDOR_NAMES = {sid: nama for sid, nama, *_rest in CORRIDORS}


def _corridor_name(sid: str) -> str:
    """Return the corridor display name for a section id."""
    return _CORRIDOR_NAMES.get(sid, sid)


def _los(vc_ratio: float) -> str:
    """Level of service from volume/capacity ratio (MKJI thresholds)."""
    if vc_ratio <= 0.35:
        return "A"
    if vc_ratio <= 0.55:
        return "B"
    if vc_ratio <= 0.75:
        return "C"
    if vc_ratio <= 0.85:
        return "D"
    if vc_ratio <= 1.00:
        return "E"
    return "F"


def label_bottlenecks(df: pd.DataFrame) -> pd.DataFrame:
    """Assign the 9-class bottleneck cause with the frozen priority order."""
    cond_banjir = df["tinggi_genangan_cm"] >= 15
    cond_kecelakaan = df["accident_count"] > 0
    cond_lampu = df["lampu_operasional"] == 0
    cond_roadwork = df["lane_closure"] == 1
    cond_event = df["event_flag"] == 1
    cond_hujan = df["curah_hujan_mm_jam"] >= 2.0
    cond_berat = (df["proporsi_roda_6plus"] >= 0.14) & (df["vc_ratio"] < 0.90)
    cond_puncak = df["vc_ratio"] >= 0.70

    rules = [
        ("banjir", cond_banjir),
        ("kecelakaan", cond_kecelakaan),
        ("lampu_mati", cond_lampu),
        ("perbaikan_jalan", cond_roadwork),
        ("keramaian_event", cond_event),
        ("hujan", cond_hujan),
        ("kendaraan_berat", cond_berat),
        ("volume_puncak", cond_puncak),
    ]
    # Aturan lampu mati hanya berlaku untuk ruas ber-lampu (approach)
    rules[2] = ("lampu_mati", cond_lampu & (df["section_type"] == "approach"))

    cause = np.select([c for _n, c in rules], [n for n, _c in rules], default="normal")
    df["bottleneck_cause"] = cause
    df["bottleneck_rule"] = np.select(
        [c for _n, c in rules],
        [f"{n} (prioritas {i + 1})" for i, (n, _c) in enumerate(rules)],
        default="normal (tidak ada gangguan)",
    )

    # kandidat kedua: aturan pertama setelah kelas terpilih yang juga aktif
    flags = np.column_stack([c.to_numpy() for _n, c in rules])
    order = np.array([
        next((i for i, (n, _c) in enumerate(rules) if n == v), len(rules))
        for v in cause
    ])
    secondary = np.full(len(df), "", dtype=object)
    for i, (name, _c) in enumerate(rules):
        mask = order == i
        if not mask.any():
            continue
        later = flags[mask][:, i + 1:]
        if later.size == 0:
            continue
        has = later.any(axis=1)
        first = later.argmax(axis=1) + i + 1
        names = np.array([rules[k][0] for k in first], dtype=object)
        secondary[mask] = np.where(has, names, "")
    df["bottleneck_secondary"] = secondary
    return df


def build_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Forward volume targets per section (15m / 2h / 4h)."""
    vol = df["volume_veh_per_hour"].astype(float)
    grouper = df["section_id"]
    df["target_volume_15m"] = vol.groupby(grouper).shift(-15).ffill().bfill().round(2)
    df["target_volume_2h"] = vol.groupby(grouper).shift(-120).ffill().bfill().round(2)
    df["target_volume_4h"] = vol.groupby(grouper).shift(-240).ffill().bfill().round(2)
    return df


def build_replay_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Intersection-level replay file in the legacy column contract."""
    approaches = df[df["section_type"] == "approach"]
    grouped = approaches.groupby(["tick", "timestamp_wib", "intersection_id"], as_index=False).agg(
        vehicle_count_1min=("vehicle_count_1min", "sum"),
        volume_veh_per_hour=("volume_veh_per_hour", "sum"),
        avg_speed_kmh=("avg_speed_kmh", "mean"),
        queue_length_veh=("queue_length_veh", "sum"),
        wait_time_min=("wait_time_min", "mean"),
        green_seconds=("green_seconds", "mean"),
        density_percent=("density_percent", "mean"),
        weather_condition=("weather_condition", "first"),
        weather_temp_c=("weather_temp_c", "first"),
        accident_count=("accident_count", "max"),
        roadwork_flag=("roadwork_flag", "max"),
        event_flag=("event_flag", "max"),
        target_volume_15m=("target_volume_15m", "mean"),
        target_volume_2h=("target_volume_2h", "mean"),
        target_volume_4h=("target_volume_4h", "mean"),
    )
    grouped["approach"] = "ALL"
    grouped["avg_speed_kmh"] = grouped["avg_speed_kmh"].round(2)
    grouped["wait_time_min"] = grouped["wait_time_min"].round(3)
    grouped["green_seconds"] = grouped["green_seconds"].round().astype(int)
    grouped["density_percent"] = grouped["density_percent"].round(2)
    grouped["volume_veh_per_hour"] = grouped["volume_veh_per_hour"].round(2)
    cols = [
        "timestamp_wib", "tick", "intersectionId", "approach", "vehicle_count_1min",
        "volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh", "wait_time_min",
        "green_seconds", "density_percent", "weather_condition", "weather_temp_c",
        "accident_count", "roadwork_flag", "event_flag",
        "target_volume_15m", "target_volume_2h", "target_volume_4h",
    ]
    grouped = grouped.rename(columns={"intersection_id": "intersectionId"})
    return grouped[cols].sort_values(["tick", "intersectionId"]).reset_index(drop=True)


def validate(df: pd.DataFrame, days: int, intersections: pd.DataFrame, sections: pd.DataFrame) -> dict:
    """Run structural checks; returns a summary dict (also logged)."""
    expected_sections = len(sections)
    checks = {
        "row_count": len(df) == expected_sections * days * 1440,
        "section_master_30": len(sections) == 30,
        "approach_21_corridor_9": (
            (sections["section_type"] == "approach").sum() == 21
            and (sections["section_type"] == "corridor").sum() == 9
        ),
        "intersections_6": len(intersections) == 6,
        "tipe_3_3": (
            (intersections["tipe_persimpangan"] == "perempatan").sum() == 3
            and (intersections["tipe_persimpangan"] == "pertigaan").sum() == 3
        ),
        "roda_sum_matches": bool((df[["roda_2", "roda_3", "roda_4", "roda_6plus"]].sum(axis=1)
                                  == df["vehicle_count_1min"]).all()),
        "no_nan_core": bool(df[["volume_veh_per_hour", "avg_speed_kmh", "queue_length_veh",
                                "vc_ratio", "los", "bottleneck_cause"]].notna().all().all()),
        "density_range": bool(df["density_percent"].between(0, 100).all()),
        "speed_positive": bool((df["avg_speed_kmh"] > 0).all()),
        "targets_filled": bool(df[["target_volume_15m", "target_volume_2h", "target_volume_4h"]]
                               .notna().all().all()),
        "all_9_classes_present": df["bottleneck_cause"].nunique() == 9,
        "kelas_lengkap_hari_validasi_dan_uji": bool(
            all(
                df.loc[df["tick"] // 1440 == day, "bottleneck_cause"].nunique() == 9
                for day in (days - 2, days - 1)
            )
        ),
        "corridor_no_signal": bool((df.loc[df["section_type"] == "corridor", "cycle_length_s"] == 0).all()),
    }
    dist = (df["bottleneck_cause"].value_counts(normalize=True).mul(100).round(2)).to_dict()
    report = {"checks": checks, "class_distribution_pct": dist}
    for name, ok in checks.items():
        log.info("[%s] %s", "PASS" if ok else "FAIL", name)
    log.info("distribusi kelas (%%): %s", dist)
    if not all(checks.values()):
        raise SystemExit("validasi gagal")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Traffix v4 dataset.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    intersections, sections = build_master_frames()
    log.info("simulasi %d hari, %d simpang, %d ruas", args.days, len(intersections), len(sections))
    df = simulate(args.days, args.seed)
    df = label_bottlenecks(df)
    df = build_targets(df)

    report = validate(df, args.days, intersections, sections)

    intersections.to_csv(out / "intersections.csv", index=False)
    sections.to_csv(out / "sections.csv", index=False)
    df.to_csv(out / "ticks_v4.csv.gz", index=False, compression="gzip")
    build_replay_frame(df).to_csv(out / "live_replay_7d.csv.gz", index=False, compression="gzip")

    log.info("baris: %d | kelas: %d | ruas: %d", len(df), df["bottleneck_cause"].nunique(), len(sections))
    log.info("ditulis ke %s", out)
    (out / "validation_report.json").write_text(
        pd.Series(report).to_json(indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
