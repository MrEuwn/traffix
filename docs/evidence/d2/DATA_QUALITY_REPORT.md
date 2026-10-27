# Laporan kualitas data — Traffix D2

Dihasilkan `2026-10-27T09:05:04+00:00` oleh `python backend/scripts/run_d2_evaluation.py`. JSON lengkap: `backend/ml/forecast/artifacts/data_quality_report.json`.

## hybrid_traffic_7d (mentah, per approach)

- Berkas: `data/data_synthetic/hybrid_traffic_7d.csv` (4,596,340 byte, sha256 `4688e910ff804289…`)
- Baris × kolom: 40,320 × 19
- Provenans: sintetis — simulator hybrid v3 (generate_data_hybrid.py, seed 42) yang dikalibrasi dengan distribusi hitungan YOLO; bukan pengukuran lapangan
- Rentang waktu: ['2026-05-01 00:00:00+07:00', '2026-05-07 23:59:00+07:00'] · zona: UTC+07:00 · urut per entitas: True
- Entitas: 4 unik (approach)
- Nilai hilang: tidak ada
- Baris duplikat: 0 · kunci duplikat ['intersectionId', 'tick', 'approach']: 0
- Nilai non-finit: 0
- Cek rentang: volume_veh_per_hour [0.00, 5220.87] pelanggaran 0, vehicle_count_1min [0.00, 87.00] pelanggaran 0, avg_speed_kmh [10.00, 60.00] pelanggaran 0, density_percent [0.00, 100.00] pelanggaran 0, queue_length_veh [0.00, 628.00] pelanggaran 0, green_seconds [20.00, 42.00] pelanggaran 0
- Asal target/label: target_volume_* di file mentah dihitung generator per approach; pipeline D2 menghitung ulang target dari volume agregat (shift -15/-120/-240 menit)
- Klaim yang didukung: Mendukung klaim kinerja peramalan PADA SIMULATOR ini saja.

## traffix_lstm_ready (fitur siap model, notebook Data team)

- Berkas: `data/data_process/traffix_lstm_ready.csv` (4,769,719 byte, sha256 `ff48bc8220af32fb…`)
- Baris × kolom: 10,980 × 52
- Provenans: turunan dari hybrid_traffic_7d + 1.500 menit 'low traffic' acak (np.random seed 42) yang ditambahkan di notebook sebagai seri JKT-TMG-SIM-01
- Rentang waktu: ['2026-05-01 01:00:00+07:00', '2026-05-08 20:59:00+07:00'] · zona: UTC+07:00 · urut per entitas: True
- Entitas: 2 unik (intersectionId)
- Nilai hilang: tidak ada
- Baris duplikat: 0 · kunci duplikat ['intersectionId', 'tick']: 0
- Nilai non-finit: 0
- Cek rentang: volume_veh_per_hour [0.00, 10344.70] pelanggaran 0, vehicle_count_1min [0.00, 172.00] pelanggaran 0, avg_speed_kmh [10.00, 78.92] pelanggaran 0, density_percent [0.00, 100.00] pelanggaran 0, queue_length_veh [0.00, 1414.00] pelanggaran 0, green_seconds [21.75, 38.00] pelanggaran 0
- Asal target/label: target_volume_{15m,2h,4h} = volume_veh_per_hour digeser -15/-120/-240 baris per intersection (diverifikasi selisih 0)
- Klaim yang didukung: Dipakai untuk mereproduksi angka notebook; tidak dipakai di protokol D2 karena split barisnya tidak kronologis.

## live_replay_7d v4 (input replay aplikasi)

- Berkas: `data/data_synthetic/v4/live_replay_7d.csv.gz` (1,861,358 byte, sha256 `417780f6249a7d21…`)
- Baris × kolom: 60,480 × 19
- Provenans: sintetis — simulator v4 (generate_data_v4.py, seed 42), 6 simpang, agregat semua lengan
- Rentang waktu: ['2026-05-01 00:00:00+07:00', '2026-05-07 23:59:00+07:00'] · zona: UTC+07:00 · urut per entitas: True
- Entitas: 6 unik (intersectionId)
- Nilai hilang: tidak ada
- Baris duplikat: 0 · kunci duplikat ['intersectionId', 'tick']: 0
- Nilai non-finit: 0
- Cek rentang: volume_veh_per_hour [756.80, 12874.63] pelanggaran 0, vehicle_count_1min [12.00, 214.00] pelanggaran 0, avg_speed_kmh [6.00, 59.17] pelanggaran 0, density_percent [0.00, 92.06] pelanggaran 0, queue_length_veh [0.00, 507.00] pelanggaran 0, green_seconds [0.00, 33.00] pelanggaran 0
- Asal target/label: target_volume_* di file ini = RATA-RATA volume per ruas, sedangkan volume_veh_per_hour = JUMLAH; skala berbeda, sehingga kolom target ini tidak dipakai sebagai label
- Klaim yang didukung: Input demo dan uji transfer antarsimulator; bukan bukti kinerja dunia nyata.

## ticks_v4 (per ruas per menit, label penyebab)

- Berkas: `data/data_synthetic/v4/ticks_v4.csv.gz` (11,747,324 byte, sha256 `96246bbcf90b6297…`)
- Baris × kolom: 302,400 × 51
- Provenans: sintetis — simulator v4 seed 42; label bottleneck_cause dari aturan prioritas simulator
- Rentang waktu: ['2026-05-01 00:00:00+07:00', '2026-05-07 23:59:00+07:00'] · zona: UTC+07:00 · urut per entitas: True
- Entitas: 30 unik (section_id)
- Nilai hilang: {'approach': 90720, 'bottleneck_secondary': 254872}
- Baris duplikat: 0 · kunci duplikat ['section_id', 'tick']: 0
- Nilai non-finit: 0
- Cek rentang: —
- Asal target/label: bottleneck_cause ditetapkan aturan simulator (docs/SCHEMA-v4.md §1), bukan anotasi manusia
- Klaim yang didukung: Mendukung klaim 'model memulihkan mekanisme simulator', bukan diagnosis penyebab nyata.

- Distribusi label: normal 49.3%, hujan 11.2%, kendaraan_berat 10.8%, banjir 7.6%, perbaikan_jalan 6.4%, keramaian_event 4.5%, volume_puncak 4.2%, kecelakaan 3.6%, lampu_mati 2.4%

## vehicle_count (keluaran inferensi YOLO notebook)

- Berkas: `inference/inference_yolo/vehicle_count.csv` (21,314 byte, sha256 `44307e813b6ad123…`)
- Baris × kolom: 100 × 17
- Provenans: turunan — keluaran YOLO notebook atas video CCTV publik Bina Marga; kecepatan, densitas, antrean adalah estimasi berbasis aturan
- Rentang waktu: — · zona: — · urut per entitas: —
- Entitas: 12 unik (camera_id)
- Nilai hilang: tidak ada
- Baris duplikat: 0 · kunci duplikat ['source_video']: 0
- Nilai non-finit: 0
- Cek rentang: vehicle_count [0.00, 922.00] pelanggaran 0, avg_speed_kmh [2.46, 96.51] pelanggaran 0, density_percent [0.00, 57.54] pelanggaran 0
- Asal target/label: tidak ada label acuan; angka adalah keluaran model
- Klaim yang didukung: Bukti alur inferensi, bukan bukti akurasi hitung.

## video_weather_data (metadata CCTV)

- Berkas: `inference_data/data_video/metadata/video_weather_data.csv` (44,289 byte, sha256 `54e7f7cc7d1e7f5b…`)
- Baris × kolom: 100 × 40
- Provenans: observasi publik — overlay CCTV Bina Marga dibaca manual; koordinat manual (Google Maps); cuaca Open-Meteo per jam
- Rentang waktu: — · zona: — · urut per entitas: —
- Entitas: 3 unik (period)
- Nilai hilang: {'km_text': 10, 'km_decimal': 10, 'notes': 21, 'coordinate_notes': 100, 'coordinate_issues': 100, 'weather_error': 100}
- Baris duplikat: 0 · kunci duplikat ['video_file']: 0
- Nilai non-finit: 0
- Cek rentang: —
- Asal target/label: tidak ada target
- Klaim yang didukung: Konteks lokasi/cuaca untuk frame demo.

## Aturan pembersihan

- Agregasi approach -> simpang per menit: volume/jumlah kendaraan/antrean/waktu tunggu dijumlah, kecepatan/hijau/kepadatan/suhu dirata-rata, cuaca = modus, flag kejadian = maksimum (data/data_process/aggregation_rules.md).
- Seri harus kontinu 1 menit per simpang; celah atau duplikat menggagalkan pipeline (assert_contiguous).
- Baris dengan riwayat < 60 menit (lag_60/roll_60 kosong) dan baris yang targetnya melewati akhir seri dibuang, bukan diimputasi.
- Tidak ada outlier yang dibuang; nilai di luar rentang fisik dicatat di range_checks.
- Seri augmentasi JKT-TMG-SIM-01 (8 Mei) tidak dipakai di protokol D2 karena dibuat acak di notebook dan tanggalnya sesudah periode uji.
