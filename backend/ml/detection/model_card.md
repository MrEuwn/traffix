# Model Card — Deteksi kendaraan YOLOv8 (modul pendukung)

## Ringkasan

| Item | Nilai |
|---|---|
| Bobot model tim | `yolo pipeline/model/best.pt` (YOLOv8n, ±3,0 juta parameter) |
| Bobot detektor demo kamera | `yolo pipeline/model/yolov8m_coco.pt` (YOLOv8m pretrained COCO, ±25,9 juta parameter, bukan dilatih tim, AGPL-3.0) — lihat bagian "Inferensi nyata" |
| Kelas | 1 — `car` |
| Data latih/validasi | Kaggle `boukraailyesali/traffic-road-object-detection-dataset-using-yolo`: 399 latih / 100 validasi, 493 objek validasi |
| Pelatihan | `yolo pipeline/code/traffix_yolo_pipeline_revised.ipynb`, Colab Tesla T4, 30 epoch maks, early stopping patience 10 (berhenti di epoch 15, terbaik epoch 5) |
| Peran di Traffix | Demo alur inferensi pada rekaman CCTV publik; **bukan** input model peramalan |

## Metrik yang tercatat — VALIDASI, bukan uji

Diambil dari output sel notebook yang tersimpan dan diparse otomatis oleh
`backend/scripts/run_d2_evaluation.py`. Hasilnya ada di
`backend/ml/detection/artifacts/yolo_evidence.json`.

| Metrik | Nilai | Catatan |
|---|---|---|
| mAP50 | 0,926 | Ultralytics `val()` |
| mAP50-95 | 0,532 | Ultralytics `val()` |
| Precision / Recall | 0,955 / 0,813 | Ultralytics `val()` |
| Precision / Recall / F1 | 0,867 / 0,884 / 0,876 | Pencocokan IoU ≥ 0,5 pada conf 0,25 (dihitung notebook) |

- **Tidak ada set uji independen.** Set validasi juga dipakai untuk memilih epoch terbaik,
  sehingga angka di atas cenderung optimistis.
- **Tidak direproduksi di sesi ini.** Dataset Kaggle (380 MB) tidak ada di repo, dan
  evaluasi ulang membutuhkan unduhan dengan kredensial Kaggle.

## Inferensi nyata pada CCTV rekaman — detektor demo diganti

`python backend/scripts/run_yolo_frames.py` menjalankan detektor pada 123 frame dari
rekaman CCTV publik Bina Marga, ruas tol Jakarta–Tangerang (pagi/siang/malam). Hasilnya
disimpan di `backend/ml/detection/artifacts/detections.json`. UI menampilkannya di panel
Kamera pada Dashboard. Tombol "Jalankan YOLO sekarang" menjalankan detektor yang sama di
backend dengan setelan yang sama.

**Model tim (`best.pt`) tidak dipakai untuk demo kamera.** Pada CCTV tol, model ini hanya
menandai 1–2 mobil terdekat, melewatkan antrean kendaraan kecil di kejauhan, dan sempat
menandai papan "JAKARTA" sebagai mobil. Penyebabnya pergeseran domain: data latih Kaggle
berisi mobil besar dari dekat, sedangkan kamera tol memotret dari ketinggian dengan sudut
lebar.

**Detektor demo:** `yolo pipeline/model/yolov8m_coco.pt` (sha256 `5d4a90cd…`).
- Checkpoint resmi Ultralytics YOLOv8m, pretrained COCO, **tidak dilatih ulang oleh tim**.
- Lisensi AGPL-3.0.
- Dibatasi ke kelas car, motorcycle, bus, dan truck.
- imgsz 1280 (frame 640×480 diperbesar supaya objek kecil terbaca), conf 0,25.

Opsi yang dicoba secara visual di frame pagi, siang, dan malam yang sama:

| Opsi | Hasil |
|---|---|
| `best.pt` @640 | 1 / 4 / 0 kotak |
| `best.pt` @1280 | 1 / 7 / 0 kotak |
| YOLOv8s COCO @1280 | 6 / 12 / 0 kotak |
| **YOLOv8m COCO @1280** | **11 / 19 / 3 kotak**; kotak pas pada mobil, truk, dan bus |
| YOLOv8m + tiling 2×2 | Sedikit lebih banyak kotak, tetapi papan petunjuk malam terbaca sebagai bus. Ditolak |

Ringkasan pada 123 frame, rata-rata kotak per frame:

| Periode | YOLOv8m COCO | `best.pt` |
|---|---|---|
| Pagi | 6,04 | 0,94 |
| Siang | 20,08 | 3,38 |
| Malam | 3,29 | 0,76 |
| Semua | 7,64 | 1,34 |

Kelas yang terdeteksi: mobil 800, truk 122, bus 18, motor 0. Motor memang tidak boleh
masuk jalan tol.

**Tidak ada label acuan untuk frame ini.** Angka di atas adalah jumlah keluaran model,
bukan akurasi. "Lebih banyak kotak" berarti lebih banyak deteksi, bukan otomatis lebih
benar. Pemilihan dibuat dengan inspeksi visual beberapa frame.

Waktu inferensi: sekitar 0,4 detik per frame di CPU Mac. Di container Docker sekitar
4 detik per frame setelah model dimuat; panggilan pertama sekitar 6–7 detik.

## Batasan dan bias

- Model tim hanya mengenal `car`. Detektor demo mengenal mobil, motor, bus, dan truk,
  tetapi motor kecil di kejauhan paling sulit, dan data tol tidak menguji motor sama sekali.
- Malam hari, silau lampu, hujan, dan pantulan menurunkan deteksi untuk kedua model.
  Papan petunjuk terang kadang terbaca sebagai bus.
- Sudut kamera tinggi dan objek kecil berada di luar distribusi latih.
- Kecepatan, densitas, dan antrean di `inference/inference_yolo/vehicle_count.csv` adalah
  **estimasi berbasis aturan** dari notebook, bukan pengukuran.

## Privasi

Frame berasal dari CCTV publik pemerintah. Resolusinya rendah (640×480), plat nomor dan
wajah tidak terbaca, dan tidak ada identifikasi individu. URL stream m3u8 tidak disajikan
oleh aplikasi.

## Langkah berikutnya yang jujur

1. Melabeli 50–100 frame CCTV tol secara manual, lalu mengukur precision dan recall
   **kedua** model sebagai set uji independen pertama. Itu satu-satunya cara mengklaim
   bahwa detektor demo lebih akurat.
2. Fine-tune YOLOv8m pada frame CCTV berlabel (sudut tinggi, malam, motor untuk jalan
   non-tol).
