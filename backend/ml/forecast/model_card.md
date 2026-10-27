# Model Card — Peramalan volume simpang (LSTM, tugas utama D2)

Semua angka di bawah dihasilkan oleh `python backend/scripts/run_d2_evaluation.py`
(run 2026-10-27T09:05:04Z, seed 42) dan berasal dari
`backend/ml/forecast/artifacts/forecast_evaluation.json`. Angka di kartu ini ditulis manual
dari artefak itu. Bila evaluasi dijalankan ulang, perbarui kartu ini atau rujuk
`docs/pitch/D2_METRICS_BRIEF.md`, yang dibuat otomatis.

## 1. Tugas

Meramalkan `volume_veh_per_hour` simpang pada t+15 menit, t+2 jam, dan t+4 jam (kend/jam,
laju arus 1 menit × 60, jumlah semua lengan) dari 41 fitur yang tersedia pada menit t.
Setiap horizon punya model sendiri.

## 2. Data

`data/data_synthetic/v4/live_replay_7d.csv.gz`: **sintetis**, simulator v4 seed 42, 6 simpang
× 10.080 menit (1–7 Mei 2026 WIB). Ini replay yang sama dengan yang diputar aplikasi.
Target dihitung ulang dari volume; kolom `target_volume_*` di file itu (rata-rata per ruas)
tidak dipakai.

## 3. Arsitektur dan pemilihan

- `lstm_light`: LSTM(64, seq) → Dropout 0,1 → LSTM(32) → Dense(64, ReLU) → Dropout 0,05
  → Dense(1); loss MAE; Adam.
- Seleksi pada MAE **validasi** (hari 6). Ruang pencarian: `seq_len ∈ {15, 60}`, lr 1e-3,
  batch 128, early stopping patience 8.

| Horizon | seq_len terpilih | MAE validasi | sha256 file |
|---|---|---|---|
| 15m | 60 | 332,3 | `68bea9df…` |
| 2h | 15 | 473,1 | `60c24647…` |
| 4h | 15 | 491,1 | `65714383…` |

Scaler fitur dan target (StandardScaler) di-fit hanya pada baris latih.

## 4. Hasil uji (hari 7, dinilai sekali)

MAE dalam kend/jam. n uji: 8.550 / 7.920 / 7.200.

| Model | 15m | 2h | 4h |
|---|---|---|---|
| **LSTM** | **364,9** | **577,8** | **703,7** |
| Persistence | 435,3 | 1.761,9 | 1.579,2 |
| Rata-rata 15 menit | 492,6 | 1.778,8 | 1.496,7 |
| Seasonal naive (kemarin, jam sama) | 369,4 | 372,6 | 379,4 |
| Ridge | 325,2 | 1.007,5 | 1.082,1 |
| HistGradientBoosting | 274,3 | 356,0 | 397,0 |

LSTM dibandingkan dengan baseline terkuat (seasonal naive, dipilih di validasi untuk ketiga
horizon), dengan CI 95% bootstrap blok 60 menit untuk selisih MAE:

| Horizon | Perbaikan MAE | Selisih MAE (CI 95%) | Signifikan |
|---|---|---|---|
| 15m | +1,2% | −4,5 [−32,8; +25,0] | tidak |
| 2h | −55,1% | +205,2 [+142,9; +275,0] | ya — LSTM **lebih buruk** |
| 4h | −85,5% | +324,3 [+226,1; +436,6] | ya — LSTM **lebih buruk** |

### Kesimpulan jujur

- LSTM mengalahkan persistence dan rata-rata 15 menit pada ketiga horizon (+16% sampai +67%).
- LSTM **tidak** terbukti lebih baik dari seasonal naive pada 15 menit, dan **lebih buruk**
  secara signifikan pada 2 jam dan 4 jam. Simulator v4 sangat periodik dari hari ke hari,
  sehingga "kemarin, jam yang sama" adalah prediktor yang sangat kuat.
- HistGradientBoosting punya MAE terendah pada 15 menit dan 2 jam, dan sudah peringkat
  pertama di **validasi** untuk ketiga horizon. Jadi temuan ini tidak bergantung pada data uji.
- Model yang dilayani tetap LSTM karena dideklarasikan sebagai model utama sebelum hari uji
  dibuka. Mengganti model atas dasar skor uji akan melanggar protokol. Langkah berikut yang
  sah ada di §8.

## 5. Analisis galat

- **Bias negatif:** LSTM cenderung meramal terlalu rendah (bias −158 / −345 / −153 kend/jam).
- **Jam terburuk:** puncak pagi. MAE LSTM pada jam target 06:00–07:00 mencapai 860 (15m),
  1.852 (2h), dan 2.787 (4h). Pada 2h dan 4h, waktu terbitnya dini hari, ketika riwayat
  60 menit tidak memuat sinyal naiknya puncak.
- **Kejadian aktif saat waktu terbit** (kecelakaan/perbaikan jalan/event):
  - 15m: MAE 386,7 dengan kejadian (n=1.297) dibanding 361,0 tanpa kejadian;
  - 2h: 670,1 dibanding 560,9;
  - 4h: sebaliknya, 565,3 dibanding 731,5, karena kejadian di sampel uji jatuh di luar
    puncak pagi.
- Grafik pendukung: `docs/evidence/d2/figures/forecast_vs_actual_*.png`, `residuals_*.png`,
  `lstm_error_by_hour.png`, dan `model_vs_baseline_mae.png`.

## 6. Eksperimen pembanding

- **Data notebook asli** (hybrid TMG-1012, protokol identik). MAE LSTM 517,6 / 698,6 / 764,8;
  dibanding baseline terkuat: +11,2% / −7,2% / −15,6%.
- **Transfer LSTM hybrid → replay v4 tanpa latih ulang.** MAE 827,7 dibanding persistence
  435,3 pada 15 menit (−90,1%). Alasan inilah model aplikasi dilatih pada data yang ia layani.
- **Model notebook lama** direproduksi persis (MAPE 21,806 / 27,034 / 32,492%), tetapi
  protokolnya punya lima masalah (lihat `docs/D2_RESEARCH_PROTOCOL.md` §8). Angka itu
  tidak dipakai sebagai klaim.

## 7. Penggunaan di aplikasi

- `ml/forecast/runtime.py` membangun jendela fitur dari replay dengan fungsi yang sama.
  Jendela berakhir di menit replay saat ini dan tidak pernah membaca menit sesudahnya.
- API mengembalikan `source: "lstm"`, waktu terbit dan target, `expected_mae` (MAE uji
  transfer pada replay v4, bukan selang keyakinan), dan `replay_split` (latih/validasi/uji).
- `GET /api/v1/model/status` membandingkan sha256 file yang dimuat dengan file yang dievaluasi.
- Tanpa model: rata-rata 15 menit terakhir dengan label `heuristic`.

## 8. Batasan dan langkah berikutnya yang sah

1. Data sintetis dari satu simulator dan satu seed; tidak ada validasi lapangan.
2. Hanya satu hari uji (Kamis); akhir pekan dan hari libur tidak diuji terpisah.
3. Flag kejadian diasumsikan diketahui pada waktu terbit.
4. Kandidat perbaikan: pilih model per horizon dari **validasi** (HGB atau seasonal naive),
   bekukan, lalu uji sekali pada data **baru** yang belum pernah dilihat
   (`generate_data_v4.py --seed 43`). Ini cara sah untuk mengganti model yang dilayani.
5. Tambahkan fitur musiman harian (volume t+h−1440) ke LSTM. Seasonal naive membuktikan
   sinyal itu kuat, sementara 41 fitur sekarang tidak memuatnya untuk horizon panjang.
