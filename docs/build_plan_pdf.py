"""Build the Traffix.id v2 / D2 planning document as PDF.

Run:  python build_plan_pdf.py
Out:  RENCANA-TRAFFIX-v2-D2-ROBCOM2026.pdf (same folder)
"""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = "RENCANA-TRAFFIX-v2-D2-ROBCOM2026.pdf"
TITLE = "Traffix.id v2 — Rencana Pengembangan Kategori D2"
AUTHOR = "Tim Traffix.id"

MARGIN = 18 * mm
PAGE_W, PAGE_H = A4
AVAIL = PAGE_W - 2 * MARGIN

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13.5,
                      alignment=TA_JUSTIFY, spaceAfter=4)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.2, leading=11)
TITLE_S = ParagraphStyle("title", parent=ss["Title"], fontSize=17, leading=21, spaceAfter=4)
SUB_S = ParagraphStyle("sub", parent=ss["Normal"], fontSize=10.5, leading=14,
                       textColor=colors.HexColor("#444444"), spaceAfter=2)
META_S = ParagraphStyle("meta", parent=SMALL, textColor=colors.HexColor("#666666"))
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=13.5, leading=17, spaceBefore=10,
                    spaceAfter=5, textColor=colors.HexColor("#111111"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, leading=14, spaceBefore=8,
                    spaceAfter=3, textColor=colors.HexColor("#222222"))
H3 = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=9.8, leading=12.5, spaceBefore=6,
                    spaceAfter=2, textColor=colors.HexColor("#333333"))
CELL = ParagraphStyle("cell", parent=SMALL, fontSize=8.0, leading=10.2)
CELLH = ParagraphStyle("cellh", parent=CELL, fontName="Helvetica-Bold")
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=11, bulletIndent=2, spaceAfter=2)


def rich(text: str) -> str:
    """Escape XML then re-enable **bold** and __mono__ markers."""
    out = escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"__(.+?)__", r"<font face='Courier'>\1</font>", out)
    return out


def p(text: str, style=BODY):
    return Paragraph(rich(text), style)


def h1(t): return Paragraph(rich(t), H1)
def h2(t): return Paragraph(rich(t), H2)
def h3(t): return Paragraph(rich(t), H3)


def bullets(items):
    return [Paragraph(rich(t), BULLET, bulletText="•") for t in items]


def table(rows, widths, header=True, font_size=8.0):
    """rows: list of list of str. widths: list of relative weights."""
    total = sum(widths)
    cw = [AVAIL * w / total for w in widths]
    body = []
    for r_i, row in enumerate(rows):
        style = CELLH if (header and r_i == 0) else CELL
        body.append([Paragraph(rich(str(c)), style) for c in row])
    t = Table(body, colWidths=cw, repeatRows=1 if header else 0, hAlign="LEFT")
    cmd = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    if header:
        cmd += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#exclude".replace("exclude", "e8e8e8"))),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ]
    t.setStyle(TableStyle(cmd))
    return t


S = []  # story

# ---------------------------------------------------------------- cover
S += [
    Spacer(1, 26 * mm),
    Paragraph(rich(TITLE), TITLE_S),
    Paragraph(rich("Penambahan parameter penyebab bottleneck, analitik waktu lampu merah, "
                   "dan inventaris ruas jalan sebagai inti kategori D2"), SUB_S),
    Spacer(1, 4 * mm),
    table(
        [
            ["Item", "Keterangan"],
            ["Kompetisi", "International Robotics & Data Science Competition 2026 (ROBCOM 2026)"],
            ["Penyelenggara", "TRUST TECH (Trunojoyo Smart Technology) x INTI International University & Colleges"],
            ["Kategori", "D2 — AI & Machine Learning Challenge (klaster Data Science & AI)"],
            ["Tema", "Innovative Minds for a Sustainable Future"],
            ["Repo dasar", "github.com/dewiazizah968/Traffix.id (versi yang sudah dilombakan sebelumnya)"],
            ["Status dokumen", "RENCANA — belum dieksekusi. Tidak ada perubahan kode pada tahap ini."],
            ["Disusun", "Senin, 26 Oktober 2026, 22.00 WIB"],
            ["Hari lomba", "Rabu, 28 Oktober 2026 (presentasi 7 menit + tanya jawab 5 menit)"],
        ],
        [22, 78],
    ),
    Spacer(1, 3 * mm),
    p("**Catatan waktu kritis.** Guidebook halaman 17 menetapkan batas pengumpulan berkas "
      "**Senin, 26 Oktober 2026 pukul 12.10 WIB**, dan registrasi ditutup 25 Oktober 23.59 WIB. "
      "Pada saat dokumen ini disusun kedua tenggat tersebut sudah lewat. Konfirmasi ke narahubung "
      "panitia (Ibnu, wa.me/6281280717345) apakah masih tersedia jalur pengumpulan berkas ulang "
      "atau revisi. Jika tidak, rencana ini tetap berlaku untuk **materi presentasi dan demo hari lomba** "
      "28 Oktober, yang tidak butuh unggah berkas.", SMALL),
    PageBreak(),
]

# ---------------------------------------------------------------- 1
S += [
    h1("1. Ringkasan Eksekutif"),
    p("Traffix.id versi lama sudah memiliki dua model: **YOLOv8** untuk deteksi kendaraan dari CCTV dan "
      "**LSTM** untuk prakiraan volume lalu lintas pada tiga horizon (15 menit, 2 jam, 4 jam), disajikan "
      "lewat backend FastAPI dan dashboard React. Nilai jual versi lama ada pada **prediksi volume**."),
    p("Kategori D2 menilai sesuatu yang berbeda: apakah model menyelesaikan masalah terdefinisi **lebih baik "
      "daripada pembanding sederhana (baseline)**, dengan evaluasi ketat tanpa kebocoran data. Karena itu v2 "
      "menggeser inti klaim D2 dari prakiraan volume ke **klasifikasi penyebab bottleneck** — pertanyaan "
      "operasional yang langsung dipakai petugas lapangan: kemacetan ini karena apa?"),
    p("Tiga parameter baru ditambahkan, dan semuanya tersambung ke satu narasi:"),
]
S += bullets([
    "**Penyebab bottleneck (9 kelas)** — normal, volume puncak, perbaikan jalan, hujan, banjir, kecelakaan, "
    "keramaian/acara, lampu mati, kendaraan berat. Ini target klasifikasi D2 sekaligus variabel baru di dataset.",
    "**Rata-rata waktu lampu merah** — agregasi siklus, durasi hijau, dan waktu tunggu per tipe persimpangan "
    "(perempatan 4 lengan vs pertigaan 3 lengan), serta rata-rata gabungan semua lampu merah yang dipantau.",
    "**Inventaris ruas (section)** — berapa ruas per koridor, kapasitas ruas dalam satuan kendaraan, volume, "
    "rasio volume/kapasitas (VC-ratio), tingkat pelayanan (LOS), dan rincian komposisi kendaraan "
    "roda 2 / 3 / 4 / 6 ke atas beserta nilai smp (satuan mobil penumpang) ekivalennya.",
])
S += [
    p("Hasil akhir yang dijual ke juri: satu dashboard yang tidak hanya berkata \"volume akan naik 20%\", "
      "tetapi \"ruas ini bottleneck karena banjir setinggi 18 cm, model yakin 0,91, dan lampu hijau di "
      "pertigaan berikutnya rata-rata hanya 24 detik dari siklus 90 detik\"."),
    p("**Keputusan yang sudah ditetapkan:** kelas penyebab = 9 kelas (8 + kendaraan berat); eksekusi "
      "mencakup seluruh fase (data, model, backend, frontend, berkas lomba) dengan subagent paralel; "
      "target push = branch __feat/d2-bottleneck__ pada repo asli, **main tidak disentuh**."),
    PageBreak(),
]

# ---------------------------------------------------------------- 2
S += [
    h1("2. Apa yang Dinilai Kategori D2"),
    p("Sumber: guidebook halaman 11 (ruang lingkup D2) dan halaman 19 (rubrik 100 poin)."),
    p("**Pertanyaan inti:** apakah model menyelesaikan masalah yang terdefinisi lebih baik daripada pembanding?"),
    h2("2.1 Bukti yang diharapkan panitia"),
    table([
        ["Tahap konsep", "Tahap prototipe"],
        ["Perumusan masalah dan keluaran model", "Hasil latih, validasi, dan uji terpisah"],
        ["Rencana dataset dan pelabelan", "Perbandingan dengan baseline"],
        ["Pilihan baseline dan metrik", "Analisis kesalahan (error analysis)"],
        ["Risiko bias yang sudah diantisipasi", "Batasan dan kondisi gagal model"],
    ], [50, 50]),
    h2("2.2 Fokus penilaian juri dan jawaban v2"),
    table([
        ["Fokus juri (halaman 11)", "Bukti yang disiapkan Traffix.id v2"],
        ["Peningkatan terukur terhadap baseline",
         "Tabel macro-F1 model vs 2 baseline (majority class dan heuristik aturan lama), dihitung pada hari uji yang tidak pernah dilihat model"],
        ["Evaluasi ketat tanpa kebocoran data",
         "Split temporal hari 1-5 latih / hari 6 validasi / hari 7 uji; seluruh fitur hanya dari masa lalu (lag dan rolling); label penyebab tidak pernah masuk sebagai fitur"],
        ["Kompleksitas model sepadan dengan masalah",
         "Model diuji bertingkat (gradient boosting, MLP, CNN-LSTM); dipilih yang menang di validasi, bukan yang paling rumit"],
        ["Keterbukaan batasan dan AI yang bertanggung jawab",
         "Model card berisi batasan, kondisi gagal, bias kelas langka (banjir), dan pernyataan terbuka bahwa label berasal dari simulator"],
    ], [34, 66]),
    h2("2.3 Pemetaan rubrik 100 poin"),
    table([
        ["#", "Kriteria (poin)", "Bukti v2"],
        ["1", "Relevansi masalah & SDG (15)",
         "Bottleneck kota = SDG 11 (kota berkelanjutan) dan SDG 13 (aksi iklim: banjir dan hujan ekstrem)"],
        ["2", "Inovasi & pembeda (20)",
         "Diagnosis penyebab per ruas, bukan sekadar prediksi volume; digabung kapasitas ruas dan komposisi kendaraan"],
        ["3", "Kualitas teknis/analitis (20)",
         "Klasifikasi multi-kelas dengan baseline, split temporal, error analysis, dan evaluasi kalibrasi"],
        ["4", "Kelayakan & bukti TKT/TRL (15)",
         "Prototipe berjalan (API + dashboard) dengan angka metrik nyata; klaim TRL 4 (divalidasi di lingkungan terkendali)"],
        ["5", "Keberlanjutan & dampak (15)",
         "Rekomendasi prioritas perbaikan: ruas mana yang harus ditangani sebab apa; dapat dipakai Dinas Perhubungan"],
        ["6", "Kualitas presentasi & jawaban (15)",
         "Deck 15 slide, demo dashboard langsung, latihan 6 menit 30 detik, daftar pertanyaan sulit disiapkan"],
    ], [5, 30, 65]),
    PageBreak(),
]

# ---------------------------------------------------------------- 3
S += [
    h1("3. Kondisi Sistem Saat Ini (Hasil Recon Repo)"),
    h2("3.1 Alur sistem versi lama"),
    p("__CCTV → YOLOv8 + ByteTrack → fitur lalu lintas (count, speed, density, queue) → pengayaan cuaca "
      "(Open-Meteo/BMKG) + kalender libur → LSTM 15m/2j/4j → mesin rekomendasi durasi hijau (rule-based) "
      "→ FastAPI → dashboard React__"),
    p("Saat ini backend **tidak memutar video**, melainkan memutar ulang (replay) dataset sintetis "
      "__data/data_synthetic/hybrid_traffic_7d.csv__ sebagai sumber data runtime, sambil tetap memuat model LSTM asli."),
    h2("3.2 Komponen yang sudah ada"),
    table([
        ["Path", "Fungsi", "Rencana v2"],
        ["yolo pipeline/model/best.pt", "YOLOv8, 1 kelas (__car__), mAP50 0,926", "Dipakai apa adanya; kelas kendaraan diturunkan di layer data, bukan di YOLO"],
        ["LSTM Training/artifacts/", "3 model .keras + scaler + best_config.json", "Tetap; jadi pembanding dan tidak diubah"],
        ["data/data_synthetic/generate_data_hybrid.py", "Generator 1 persimpangan, 4 approach, 7 hari, 1 menit", "Diperluas jadi v4: banyak persimpangan, ruas, komposisi kendaraan, label penyebab"],
        ["backend/sim/", "dataset_loader, adapter, tick_engine, congestion_engine, modifiers, incidents", "Skema baris ditambah field baru; tick_engine menyalurkan label penyebab ke state store"],
        ["backend/ml/", "model_loader, predictor, preprocess, registry (LSTM)", "Ditambah subpaket __ml/bottleneck/__ (classifier + registry sendiri)"],
        ["backend/rec/engine.py", "Rekomendasi durasi hijau berbasis aturan", "Ditambah konteks penyebab: rekomendasi berbeda untuk banjir vs perbaikan jalan"],
        ["backend/app/routes/", "intersections, predictions, recommendations, weather, simulation, cameras, system", "Tambah bottlenecks, segments, signals, model evaluation"],
        ["frontend/src/pages/", "Dashboard, LiveMap, Login, Settings", "Tambah panel Penyebab, tabel Ruas, kartu Waktu Lampu, halaman Evaluasi Model"],
        ["backend/tests/", "test_api_smoke, test_integration_units (pytest)", "Tambah tes endpoint baru + tes anti-kebocoran split"],
        [".github/workflows/backend-ci.yml", "CI pytest saat push/PR menyentuh backend/", "Tetap; CI jadi bukti reproducible di depan juri"],
    ], [30, 34, 36]),
    h2("3.3 Analisis celah: parameter yang diminta belum ada"),
    table([
        ["Parameter yang diminta", "Kondisi di repo sekarang", "Yang harus dibangun"],
        ["Penyebab bottleneck",
         "Hanya ada __roadwork_flag__, __accident_count__, __event_flag__; tidak ada banjir, tidak ada label penyebab, tidak ada kelas normal eksplisit",
         "Definisi 9 kelas + aturan kausal di generator + kolom label + fitur pendukung (curah hujan, tinggi genangan, penutupan lajur)"],
        ["Rata-rata waktu lampu merah (perempatan & pertigaan)",
         "Ada __green_seconds__ per approach, 1 persimpangan (semuanya 4 lengan); tidak ada tipe persimpangan, tidak ada agregasi",
         "Kolom tipe persimpangan (perempatan/pertigaan), jumlah lengan, durasi siklus, lalu agregasi rata-rata per tipe dan gabungan"],
        ["Ruas/section: jumlah, kapasitas, breakdown roda 2/3/4/6+",
         "Tidak ada konsep ruas sama sekali; YOLO hanya 1 kelas kendaraan; dataset tidak punya komposisi jenis kendaraan",
         "Tabel ruas (panjang, lajur, kapasitas smp dan kendaraan) + komposisi kendaraan per ruas + smp ekivalen + LOS"],
    ], [24, 38, 38]),
    PageBreak(),
]

# ---------------------------------------------------------------- 4
S += [
    h1("4. Tiga Parameter Baru — Definisi Operasional"),
    h2("4.1 Parameter 1: Penyebab bottleneck (target D2, 9 kelas)"),
    p("Label diberikan per (ruas, menit). Kelas ditetapkan bila ambangnya terpenuhi; bila beberapa kondisi "
      "tumpang tindih, dipakai urutan prioritas: banjir > kecelakaan > lampu mati > perbaikan jalan > "
      "keramaian > hujan > kendaraan berat > volume puncak > normal."),
    table([
        ["Kelas", "Definisi operasional", "Sinyal pembeda di data"],
        ["normal", "Tidak ada gangguan; arus lancar", "VC-ratio < 0,7; kecepatan > 0,8 x kecepatan bebas; tanpa kejadian"],
        ["volume_puncak", "Permintaan melebihi kapasitas tanpa gangguan eksternal", "Volume tinggi pada jam sibuk; VC-ratio > 0,9; cuaca cerah; tanpa penutupan lajur"],
        ["perbaikan_jalan", "Penutupan lajur karena pekerjaan jalan", "lane_closure > 0; durasi panjang (jam sampai hari); penurunan kecepatan bertahap; antrean naik perlahan"],
        ["hujan", "Hujan menurunkan kecepatan dan kapasitas", "Curah hujan 2-20 mm/jam; kecepatan turun 15-25%; permintaan turun sedikit; tanpa genangan"],
        ["banjir", "Genangan menutup sebagian badan jalan", "Tinggi genangan >= 15 cm; kapasitas turun > 50%; kecepatan < 15 km/jam; durasi bertahan lama"],
        ["kecelakaan", "Insiden mendadak pada satu lengan/ruas", "Lonjakan antrean mendadak; durasi pendek-menengah (10-60 menit); terlokalisasi satu lengan"],
        ["keramaian_event", "Acara mengubah pola permintaan", "event_flag aktif; volume sisi tertentu naik; tanpa penutupan lajur permanen; sering akhir pekan"],
        ["lampu_mati", "Simpang kehilangan kendali lampu", "green_seconds = 0 / tak terkontrol; kapasitas simpang turun tajam; antrean merata di semua lengan"],
        ["kendaraan_berat", "Dominasi truk/bus memperlambat arus", "Proporsi roda 6+ dan nilai smp naik; headway besar; kecepatan turun; tanpa kejadian eksternal"],
    ], [17, 40, 43]),
    h2("4.2 Parameter 2: Rata-rata waktu lampu merah (perempatan & pertigaan)"),
    p("\"Waktu lampu merah\" diterjemahkan menjadi satu set metrik yang bisa diukur dan dirata-ratakan, "
      "bukan satu angka tunggal, supaya bisa dipertahankan saat tanya jawab:"),
    table([
        ["Metrik", "Definisi", "Satuan"],
        ["tipe_persimpangan", "perempatan (4 lengan) atau pertigaan (3 lengan)", "kategori"],
        ["jumlah_lengan", "Banyak lengan yang dikendalikan lampu", "lengan"],
        ["cycle_length_s", "Panjang satu siklus lampu (hijau + kuning + merah semua lengan)", "detik"],
        ["avg_green_s", "Rata-rata durasi hijau per lengan", "detik"],
        ["avg_red_s", "Rata-rata durasi merah per lengan per siklus", "detik"],
        ["avg_wait_time_min", "Rata-rata waktu tunggu kendaraan di simpang", "menit"],
        ["avg_delay_s", "Selisih waktu tempuh nyata vs waktu tempuh bebas", "detik"],
        ["avg_queue_veh", "Rata-rata panjang antrean", "kendaraan"],
        ["rata_rata_semua", "Rata-rata gabungan seluruh lampu merah yang dipantau", "detik/menit"],
    ], [26, 58, 16]),
    p("Agregasi disajikan tiga lapis: **per persimpangan**, **per tipe (perempatan vs pertigaan)**, dan "
      "**gabungan semua lampu merah**. Filter wajib ada supaya bisa menjawab \"rata-rata dari semua atau "
      "beberapa lampu merah\" secara langsung di dashboard."),
    h2("4.3 Parameter 3: Inventaris ruas (section)"),
    table([
        ["Field", "Arti", "Contoh"],
        ["section_id / nama_ruas", "Identitas ruas antar-simpang", "SEC-014 / Jl. Tomang Raya arah utara"],
        ["panjang_m, jumlah_lajur", "Geometri ruas", "420 m, 3 lajur"],
        ["kapasitas_smp_per_jam", "Kapasitas arus (smp/jam), acuan MKJI", "5.700 smp/jam"],
        ["kapasitas_kendaraan", "Berapa kendaraan yang bisa termuat ruas pada kondisi macet penuh "
                                "(= panjang ruas / ruang per kendaraan)", "224 kendaraan"],
        ["volume_kendaraan_per_jam", "Arus nyata yang melintas", "3.910 kendaraan/jam"],
        ["vc_ratio", "volume / kapasitas — indikator utama jenuh atau tidak", "0,69"],
        ["los", "Tingkat pelayanan A-F (A lancar, F macet total)", "C"],
        ["jumlah_roda_2 / 3 / 4 / 6plus", "Rincian jenis kendaraan: motor, bajaj/kendaraan tiga roda, mobil, truk/bus", "2.310 / 120 / 1.280 / 200"],
        ["persen_roda_*", "Pangsa tiap jenis terhadap total", "59% / 3% / 33% / 5%"],
        ["smp_ekivalen", "Konversi ke satuan mobil penumpang (motor 0,25 / roda 3 0,50 / roda 4 1,00 / roda 6+ 1,30, acuan MKJI, dapat dikalibrasi)", "3.055 smp/jam"],
        ["penyebab_dominan", "Kelas penyebab bottleneck tersering di ruas itu", "banjir (31% waktu)"],
        ["rata_rata_waktu_tunggu_menit", "Rata-rata waktu tunggu di ruas", "2,7 menit"],
    ], [26, 52, 22]),
    p("Breakdown roda 2/3/4/6+ dihitung sampai jumlah dan persen, lalu dikonversi ke smp supaya volume "
      "dan kapasitas bisa dibandingkan apel-ke-apel. Ini juga yang membuat kelas **kendaraan_berat** bisa "
      "dibedakan dari **volume_puncak**."),
    PageBreak(),
]

# ---------------------------------------------------------------- 5
S += [
    h1("5. Rencana Data v4"),
    h2("5.1 Cakupan"),
    table([
        ["Aspek", "Nilai lama (v3)", "Nilai v4 (rencana)"],
        ["Persimpangan", "1 (4 lengan)", "6 — 3 perempatan + 3 pertigaan"],
        ["Ruas (section)", "Tidak ada", "30 ruas (tiap simpang 4-5 ruas pendekat + koridor antar-simpang)"],
        ["Durasi & resolusi", "7 hari, 1 menit", "7 hari, 1 menit (dipertahankan agar sebanding dengan model lama)"],
        ["Jumlah baris tick", "40.320", "Sekitar 220.000 (6 simpang x 3,67 lengan x 10.080 menit)"],
        ["Kolom baru", "-", "9 kelas penyebab + 12 kolom konteks penyebab + tipe simpang + 15 kolom komposisi kendaraan & kapasitas"],
        ["File keluaran", "hybrid_traffic_7d.csv", "hybrid_traffic_v4.csv, intersections.csv (master), sections.csv (master), bottleneck_labels.csv"],
    ], [18, 26, 56]),
    h2("5.2 Skema keluaran"),
    table([
        ["Tabel", "Kunci", "Isi pokok", "Perkiraan baris"],
        ["intersections.csv", "intersection_id", "nama, tipe (perempatan/pertigaan), jumlah lengan, koordinat, cycle_length_s, jumlah_lajur per lengan, ada lampu atau tidak", "6"],
        ["sections.csv", "section_id", "intersection_id, ruas_dari/ke, panjang_m, jumlah_lajur, kapasitas_smp_per_jam, kapasitas_kendaraan, kecepatan_bebas_kmh, arah", "30"],
        ["ticks.csv (utama)", "tick + intersection_id + approach/section_id", "Seluruh metrik lama (volume, speed, queue, density, green, wait) + konteks penyebab (curah_hujan_mm_jam, tinggi_genangan_cm, durasi_hujan_menit, lane_closure, pct_lajur_tertutup, durasi_kerja_jalan_menit, event_flag, lampu_operasional, accident_count, proporsi_roda_6plus) + kolom label bottleneck_cause", "±220.000"],
        ["bottleneck_labels.csv", "tick + intersection_id + section_id", "Tabel label terpisah (bottleneck_cause, penjelasan_aturan_aktif, kelas_alternatif) supaya jelas mana fitur dan mana target", "±220.000"],
    ], [18, 20, 52, 10]),
    h2("5.3 Kalibrasi dan kejujuran sumber data"),
    p("Aturan yang wajib dipegang (konsisten dengan klausul 20.2 dan halaman 15 guidebook — \"sebut sumber "
      "untuk setiap data, gambar, dan kode yang bukan karya tim\"):"),
]
S += bullets([
    "Fitur **real-calibrated**: bentuk sebaran kecepatan, kepadatan, dan antrean tetap memakai kalibrasi "
    "YOLO (traffic_features.csv) seperti generator lama.",
    "Konteks cuaca mengikuti model hujan **Open-Meteo** yang sudah dipakai pipeline (data/data_process dan "
    "inference_data/data_video/07_fetch_weather_openmeteo.py).",
    "Kapasitas, nilai smp, dan LOS memakai acuan **MKJI 1997** (kapasitas jalan perkotaan Indonesia) dan "
    "dinyatakan sebagai referensi, bukan pengukuran lapangan.",
    "Label penyebab **dibangkitkan oleh simulator** dengan aturan kausal eksplisit. Ini data sintetis dan "
    "harus dinyatakan terbuka di deck pada slide keterbatasan. Justifikasinya: label penyebab sebenarnya "
    "(berapa jam banjir menutup ruas, kapan ada perbaikan jalan) tidak tersedia terbuka untuk umum.",
    "Semua skrip generator bersifat deterministik dengan seed tetap (DEFAULT_SEED = 42) sehingga hasil bisa "
    "direproduksi juri dari repo, tanpa dataset eksternal.",
])
S += [
    PageBreak(),
]

# ---------------------------------------------------------------- 6
S += [
    h1("6. Model D2 — Klasifikasi Penyebab Bottleneck"),
    h2("6.1 Perumusan masalah"),
    p("**Masukan:** jendela fitur 30 menit terakhir pada satu ruas (volume, kecepatan, antrean, kepadatan, "
      "durasi hijau, curah hujan, genangan, penutupan lajur, jam, hari) — semuanya berasal dari masa lalu. "
      "**Keluaran:** satu dari 9 kelas penyebab + skor keyakinan + 3 kandidat teratas dengan penjelasan fitur "
      "pemicu. **Kegunaan:** petugas tahu harus berbuat apa (rekayasa lalu lintas, pompa air, perbaikan "
      "lampu) bukan sekadar tahu akan macet."),
    h2("6.2 Baseline dan model pembanding"),
    table([
        ["Peran", "Model", "Alasan dipilih"],
        ["Baseline 1 — naif", "Majority class (selalu tebak kelas tersering)", "Batas bawah yang harus dilewati; memperlihatkan kelas timpang"],
        ["Baseline 2 — aturan lama", "Heuristik aturan yang sudah ada di sistem (roadwork_flag, accident_count, hujan)", "Mewakili produk v1; juri suka perbandingan terhadap apa yang sudah ada"],
        ["Kandidat A", "Gradient boosting (HistGradientBoosting / LightGBM) pada fitur tabular", "Kuat untuk data tabular, cepat, mudah dijelaskan (feature importance)"],
        ["Kandidat B", "MLP multi-kelas (mirip LSTM ringan) pada fitur tabular ternormalisasi", "Pembanding neural yang kompleksitasnya sepadan"],
        ["Kandidat C (opsional)", "CNN-LSTM 1 dimensi pada barisan 30 menit x n fitur", "Menjaga kesinambungan dengan model LSTM v1; dipakai bila menang di validasi"],
    ], [18, 40, 42]),
    h2("6.3 Protokol evaluasi (bagian yang paling diawasi juri)"),
    table([
        ["Aspek", "Ketentuan"],
        ["Split", "Temporal, bukan acak: hari 1-5 latih, hari 6 validasi, hari 7 uji. Acak dilarang karena akan membocorkan masa depan."],
        ["Anti-kebocoran", "Fitur hanya lag dan rolling dari masa lalu; tidak ada kolom konteks penyebab mentah (lane_closure, tinggi_genangan) pada saat uji; normalisasi di-fit hanya pada data latih."],
        ["Ketidakseimbangan kelas", "Dilaporkan apa adanya; penanganan lewat class_weight atau oversampling **hanya di data latih**; kelas minoritas tetap dilaporkan per-kelas."],
        ["Metrik utama", "Macro-F1 (adil untuk kelas langka seperti banjir), dilengkapi balanced accuracy."],
        ["Metrik pendukung", "Recall per kelas, confusion matrix, kalibrasi (Brier score / ECE), latensi inferensi per sampel."],
        ["Analisis kesalahan", "Pasangan kelas yang paling sering tertukar (dugaan: hujan vs banjir, volume_puncak vs kendaraan_berat), dipecah per jam dan per tipe persimpangan."],
        ["Kondisi gagal", "Dinyatakan terbuka: ruas tanpa riwayat banjir, kejadian yang belum pernah ada di data latih, dan sensor hujan mati."],
        ["Artefak", "model + scaler + metrics.json + model_card.md + notebook latih yang bisa dijalankan ulang + hash data."],
    ], [22, 78]),
    h2("6.4 Analitik pendukung (bukan ML, tapi wajib untuk pertanyaan juri)"),
]
S += bullets([
    "**Tabel perbandingan baseline vs model** ditampilkan hidup di halaman evaluasi dashboard, jadi bukti "
    "bukan sekadar angka di slide.",
    "**Analitik ruas:** jumlah ruas, kapasitas kendaraan, VC-ratio, LOS, dan komposisi roda 2/3/4/6+.",
    "**Analitik lampu merah:** rata-rata waktu per tipe persimpangan dan gabungan seluruh lampu merah.",
    "**Peta prioritas:** ruas diurutkan menurut dampak (waktu tunggu total x jumlah kendaraan) sehingga "
    "rekomendasi bisa ditindaklanjuti, sesuai kriteria rubrik nomor 5.",
])
S += [PageBreak()]

# ---------------------------------------------------------------- 7
S += [
    h1("7. Rencana Backend API"),
    p("Semua endpoint baru memakai konvensi lama: prefix __/api/v1__, skema Pydantic di core/schemas.py, "
      "respons dibungkus seperti endpoint yang sudah ada, dan ikut teruji di pytest + CI."),
    table([
        ["Endpoint", "Isi respons", "Dipakai untuk"],
        ["GET /api/v1/bottlenecks", "Penyebab dominan seluruh persimpangan/ruas + confidence + 3 kandidat + fitur pemicu", "Panel penyebab di dashboard"],
        ["GET /api/v1/bottlenecks/{intersection_id}", "Rincian penyebab satu simpang, riwayat 24 jam, per lengan", "Drill-down per simpang"],
        ["GET /api/v1/segments", "Daftar ruas: panjang, lajur, kapasitas smp & kendaraan, volume, VC-ratio, LOS, komposisi roda", "Tabel ruas"],
        ["GET /api/v1/segments/summary", "Agregat: jumlah ruas, total kapasitas kendaraan, komposisi kendaraan keseluruhan", "Kartu ringkasan & jawaban cepat saat tanya jawab"],
        ["GET /api/v1/signals/summary", "Rata-rata cycle/green/red/wait per tipe (perempatan, pertigaan) + gabungan; mendukung filter himpunan simpang", "Kartu waktu lampu merah"],
        ["GET /api/v1/model/evaluation", "metrics.json + tabel baseline vs model + confusion matrix + daftar batasan", "Bukti D2 yang bisa dibuka juri kapan saja"],
        ["GET /api/v1/weather/current", "Tidak berubah, tetapi respons ditambah curah hujan dan indikator genangan", "Korelasi cuaca-penyebab"],
    ], [30, 46, 24]),
    h2("7.1 Perubahan pada komponen lama"),
    table([
        ["Berkas", "Perubahan"],
        ["backend/sim/dataset_models.py", "DatasetRow ditambah field konteks penyebab, tipe simpang, komposisi kendaraan"],
        ["backend/sim/dataset_loader.py & dataset_adapter.py", "Memuat master intersections/sections + ticks v4, tetap kompatibel dengan CSV lama"],
        ["backend/app/state_store.py", "LiveIntersectionUpdate ditambah bottleneck_cause, bottleneck_confidence, vc_ratio, los, komposisi kendaraan"],
        ["backend/sim/tick_engine.py", "Menyalurkan label penyebab ke state store dan memicu refresh prediksi penyebab"],
        ["backend/rec/engine.py", "Rekomendasi durasi hijau sadar-penyebab (banjir: prioritaskan pengurasan, perbaikan jalan: penyesuaian offset)"],
        ["backend/ml/registry.py", "Mendaftarkan artefak classifier penyebab di samping tiga model LSTM"],
        ["backend/app/routes/__init__.py", "Mendaftarkan router baru; endpoint lama tidak berubah (tidak ada breaking change)"],
    ], [34, 66]),
]

# ---------------------------------------------------------------- 8
S += [
    h1("8. Rencana Frontend"),
    table([
        ["Komponen / halaman", "Isi", "Menjawab"],
        ["BottleneckPanel.tsx (Dashboard)", "Kelas penyebab dominan per simpang + confidence + batang probabilitas 9 kelas + ikon penyebab + teks rekomendasi tindakan", "Parameter 1"],
        ["SignalTimingCard.tsx (Dashboard)", "Rata-rata cycle, hijau, merah, waktu tunggu per tipe simpang; badge perempatan vs pertigaan; angka gabungan semua lampu merah", "Parameter 2"],
        ["SegmentTable.tsx (Dashboard/LiveMap)", "Tabel ruas: kapasitas kendaraan, volume, VC-ratio, LOS, dan stacked bar komposisi roda 2/3/4/6+, plus filter koridor", "Parameter 3"],
        ["ModelEvaluation.tsx (halaman baru)", "Tabel baseline vs model, confusion matrix, kurva kalibrasi, daftar batasan, tautan model card dan notebook", "Rubrik D2 nomor 3 dan 4"],
        ["Peta (LiveMap)", "Warna ruas menurut penyebab dominan, bukan hanya merah-kuning-hijau tingkat kepadatan", "Keseluruhan narasi"],
        ["Settings", "Kontrol replay simulasi tetap; ditambah pemilih mode data (v3 lama / v4 baru)", "Demo dan tanya jawab"],
    ], [26, 52, 22]),
    p("Batasan teknis yang dijaga: warna dan gaya tetap mengikuti tema dashboard yang ada, komponen baru "
      "mengikuti pola __useTraffixData.ts__ (React Query, polling 1 detik), dan tidak menambah library baru "
      "kecuali benar-benar perlu — grafik memakai recharts yang sudah terpasang."),
    h1("9. Berkas Lomba dan Pemetaannya"),
    table([
        ["Berkas", "Status", "Format (guidebook hlm. 17)", "Isi untuk v2"],
        ["Ringkasan Proyek", "Wajib", "PDF maks 2 halaman", "Kanvas 8 pertanyaan (masalah, pengguna, solusi, kebaruan, kelayakan, bukti, batasan, hasil) diisi angka v2"],
        ["Pitch Deck", "Wajib", "PDF 16:9, maks 15 slide", "Alur: masalah - celah - solusi v2 - data - model vs baseline - hasil - batasan - dampak SDG 11 & 13 - rencana lanjut"],
        ["Pernyataan Orisinalitas", "Wajib", "PDF bertanda tangan", "Termasuk pengungkapan penggunaan alat AI dan penghargaan sebelumnya (proyek ini pernah dilombakan)"],
        ["Tautan video demo", "Opsional", "maks 3 menit, publik", "Rekaman layar dashboard: penyebab berubah karena hujan, tabel ruas, evaluasi model"],
        ["Lampiran bukti", "Opsional", "PDF atau tautan publik", "Repo GitHub, notebook latih, metrics.json, model card"],
    ], [22, 10, 26, 42]),
    p("Semua berkas dinamai pola **Team-Tag_NamaTim_JenisBerkas** (contoh __R1-007_TeamName_PitchDeck.pdf__), "
      "maksimum 20 MB per berkas, dan tautan wajib bisa dibuka tanpa permintaan izin akses."),
]
S += [PageBreak()]

# ---------------------------------------------------------------- 10
S += [
    h1("10. Rencana Eksekusi Paralel"),
    p("Aturan main supaya paralel tidak bentrok: **(1)** bekukan kontrak skema dulu — satu berkas "
      "__docs/SCHEMA-v4.md__ dan satu berkas tipe TypeScript — sebelum subagent lain mulai; **(2)** setiap "
      "subagent menyentuh berkas yang berbeda (tidak ada dua agent pada satu berkas); **(3)** debugging "
      "berurutan (jalankan → perbaiki → jalankan) dikerjakan di thread utama, bukan dilempar ke subagent."),
    table([
        ["Gelombang", "Subagent", "Deliverable", "Dependensi"],
        ["G0 (serial, thread utama)", "Kontrak skema & struktur branch",
         "docs/SCHEMA-v4.md, branch feat/d2-bottleneck, rencana tes", "—"],
        ["G1 (paralel)", "A1 Data v4", "generate_data_v4.py + 4 CSV + skrip validasi lulus", "G0"],
        ["G1 (paralel)", "A2 Antarmuka & tipe", "core/schemas.py, frontend/src/types/index.ts, kontrak API tertulis", "G0"],
        ["G2 (paralel)", "A3 Model D2", "notebook latih + artefak + metrics.json + model_card.md", "G1 (CSV)"],
        ["G2 (paralel)", "A4 Backend API", "route bottlenecks/segments/signals/evaluation + tes pytest hijau", "G0, G1"],
        ["G3 (paralel)", "A5 Frontend", "BottleneckPanel, SignalTimingCard, SegmentTable, ModelEvaluation", "G2 (kontrak API)"],
        ["G3 (paralel)", "A6 Dokumen lomba", "ringkasan 2 hlm, deck 15 slide, pernyataan orisinalitas, narasi video", "G2 (angka metrik)"],
        ["G4 (thread utama)", "Integrasi & uji end-to-end", "backend + frontend jalan bersama, bukti tangkapan layar, pelatihan presentasi", "semua"],
    ], [16, 18, 46, 20]),
    h2("10.1 Timeline (WIB)"),
    table([
        ["Waktu", "Kegiatan", "Pemicu selesai"],
        ["Sen 26 Okt, 22.00-23.30", "G0 + G1: kontrak skema, generator v4, verifikasi CSV", "4 CSV terbentuk, validasi lulus"],
        ["Sen 26 Okt, 23.30 - Sel 27 Okt, 04.00", "G2: latih model + backend API (paralel)", "metrics.json ada, pytest hijau"],
        ["Sel 27 Okt, 04.00-08.00", "G3: frontend + dokumen lomba (paralel)", "UI tampil dengan data nyata, draft deck siap"],
        ["Sel 27 Okt, 08.00-09.30", "Uji end-to-end, perbaikan, latihan presentasi 6 menit 30 detik", "demo mulus"],
        ["Sel 27 Okt, 10.00", "Technical Meeting (wajib hadir, daring via Zoom)", "urutan tampil diketahui"],
        ["Sel 27 Okt, 10.00-22.00", "Poles deck, rekam video demo (opsional), siapkan jawaban pertanyaan sulit", "semua berkas final"],
        ["Rab 28 Okt", "Hari lomba: presentasi 7 menit + tanya jawab 5 menit", "-"],
    ], [26, 44, 30]),
    h1("11. Risiko dan Mitigasi"),
    table([
        ["Risiko", "Dampak", "Mitigasi"],
        ["Tenggat berkas 26 Okt 12.10 WIB sudah lewat", "Berkas wajib tidak terkirim", "Konfirmasi ke panitia hari ini; siapkan paket berkas lengkap apa pun hasilnya, karena panitia menayangkan deck yang dikumpulkan bila koneksi daring putus"],
        ["Label penyebab sintetis", "Kredibilitas model dipertanyakan juri", "Nyatakan terbuka di slide batasan; tunjukkan aturan kausal eksplisit dan reproduktif; tekankan klaim TRL 4, bukan TRL 7"],
        ["Kelas banjir langka", "Macro-F1 jatuh, kelas minoritas tak terpelajari", "class_weight hanya di latih, laporkan per-kelas apa adanya, jangan sembunyikan"],
        ["Kebocoran data tanpa sadar", "Skor tampak tinggi tapi tidak sah", "Tes otomatis anti-kebocoran: pastikan kolom konteks mentah tidak masuk fitur dan split berbasis waktu"],
        ["Waktu tersisa sekitar 2 hari", "Fase 4-5 tidak selesai", "Frontend dan dokumen dikerjakan paralel; prioritas jika terpaksa memangkas: panel penyebab + tabel ruas + halaman evaluasi"],
        ["Repo milik anggota lain", "Perubahan tidak sengaja menimpa main", "Semua pekerjaan di branch feat/d2-bottleneck, main tidak disentuh, merge lewat PR"],
    ], [24, 24, 52]),
    h1("12. Checklist Sebelum Presentasi"),
]
S += bullets([
    "Backend jalan: __python scripts/run_dev.py__ di dalam folder backend, endpoint /docs terbuka.",
    "Frontend jalan: __npm run dev__ di folder frontend, login admin/admin123, semua panel terisi data v4.",
    "pytest hijau di folder backend, CI GitHub Actions lulus di branch.",
    "metrics.json dan model card bisa ditunjukkan langsung dari halaman Evaluasi Model.",
    "Deck 15 slide dan ringkasan 2 halaman tersimpan sebagai PDF di perangkat dan di penyimpanan daring.",
    "Pernyataan orisinalitas ditandatangani semua anggota, pengungkapan AI dan penghargaan sebelumnya ada.",
    "Latihan presentasi selesai di bawah 6 menit 30 detik; jawaban untuk pertanyaan data, biaya, risiko, dan langkah berikutnya sudah disiapkan.",
    "Screenshot dashboard disiapkan sebagai cadangan bila koneksi daring terputus.",
])
S += [
    Spacer(1, 6 * mm),
    p("Dokumen ini adalah rencana. Tidak ada kode, dataset, atau berkas lomba yang diubah pada tahap ini; "
      "eksekusi dimulai setelah pemilik repo menyetujui kontrak skema di bagian 5.2.", SMALL),
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(MARGIN, 10 * mm, "Traffix.id v2 — Rencana Pengembangan · Kategori D2 · ROBCOM 2026")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Halaman {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#dddddd"))
    canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canvas.restoreState()


def main() -> int:
    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        title=TITLE,
        author=AUTHOR,
        subject="Rencana pengembangan Traffix.id v2 untuk kategori D2 ROBCOM 2026",
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    doc.build(S, onFirstPage=footer, onLaterPages=footer)
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
