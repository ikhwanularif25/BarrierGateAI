# Smart Barrier Gate AI

Smart Barrier Gate AI adalah aplikasi Python untuk mendeteksi kendaraan/logistik di area gudang menggunakan model YOLO.

Model saat ini memiliki 4 class:

```text
forklift_empty
forklift_loaded
troli_empty
troli_loaded
```

Aplikasi dapat menggunakan beberapa sumber video:

```text
1. Webcam
2. CCTV melalui RTSP
3. File video hasil recording
```

Aplikasi juga menampilkan UI Smart Barrier Gate yang terdiri dari:

```text
- Zona Kiri
- Zona Kanan
- Status object
- Status loaded / empty
- Bounding box detection
- Confidence
- FPS
- YOLO inference time
- Validate Kiri
- Validate Kanan
```

---

## 1. Struktur Project

Struktur project yang direkomendasikan:

```text
BarrierGateAI/
│
├── main.py
├── config.py
├── detector.py
├── ui.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── models/
│   └── best.pt
│
└── videos/
    └── record_cctv.mp4
```

> File `best.pt` dan file video sebaiknya tidak disimpan langsung di GitHub apabila ukurannya besar.

---

## 2. Requirement

Direkomendasikan menggunakan:

```text
Python 3.11 atau Python 3.12
```

Dependency utama:

```text
ultralytics==8.4.121
opencv-python==5.0.0.93
numpy==2.5.2
python-dotenv==1.2.2
```

---

## 3. Clone Repository

Buka Terminal, PowerShell, Git Bash, atau terminal PyCharm.

Clone repository:

```bash
git clone <URL_REPOSITORY>
```

Contoh:

```bash
git clone https://github.com/username/BarrierGateAI.git
```

Masuk ke folder project:

```bash
cd BarrierGateAI
```

---

## 4. Membuat Virtual Environment

Windows:

```bash
python -m venv .venv
```

Aktifkan virtual environment:

```bash
.venv\Scripts\activate
```

Jika berhasil, terminal akan menampilkan:

```text
(.venv)
```

Contoh:

```text
(.venv) D:\BarrierGateAI>
```

---

## 5. Install Dependency

Pastikan virtual environment sudah aktif.

Jalankan:

```bash
python -m pip install --upgrade pip
```

Kemudian:

```bash
pip install -r requirements.txt
```

Tunggu sampai instalasi selesai.

Untuk memastikan Ultralytics dan OpenCV berhasil:

```bash
python -c "import ultralytics; import cv2; print('Ultralytics OK'); print('OpenCV:', cv2.__version__)"
```

---

## 6. Memasang Model YOLO

Model hasil training tidak harus disimpan di GitHub.

Copy file:

```text
best.pt
```

ke folder:

```text
BarrierGateAI/models/
```

Sehingga menjadi:

```text
BarrierGateAI/
└── models/
    └── best.pt
```

Pastikan `config.py` menunjuk ke:

```python
MODEL_PATH = BASE_DIR / "models" / "best.pt"
```

---

## 7. Class Model

Model hasil training awal memiliki class:

```text
0 = forklift_empety
1 = forklift_loaded
2 = troli_empety
3 = troli_loaded
```

Karena terdapat typo `empety`, aplikasi memperbaikinya saat model dijalankan menjadi:

```text
0 = forklift_empty
1 = forklift_loaded
2 = troli_empty
3 = troli_loaded
```

Tidak perlu melakukan training ulang hanya untuk memperbaiki nama class tersebut.

---

# 8. Memilih Sumber Video

Sumber video diatur melalui:

```text
config.py
```

Terdapat 3 mode:

```text
webcam
rtsp
video
```

---

## 9. Menggunakan Webcam

Pada `config.py`:

```python
CAMERA_MODE = "webcam"
```

Kemudian tentukan index webcam:

```python
WEBCAM_INDEX = 0
```

Jika webcam USB berada pada index lain:

```python
WEBCAM_INDEX = 1
```

atau:

```python
WEBCAM_INDEX = 2
```

---

# 10. Menggunakan CCTV RTSP

Pada `config.py`:

```python
CAMERA_MODE = "rtsp"
```

Isi konfigurasi CCTV melalui konfigurasi lokal atau `.env`.

Contoh:

```python
CCTV_IP = "192.168.x.x"
CCTV_USERNAME = "admin"
```

Jangan menyimpan password CCTV langsung di repository GitHub.

Direkomendasikan menggunakan file:

```text
.env
```

Contoh `.env`:

```text
CCTV_IP=192.168.x.x
CCTV_USERNAME=admin
CCTV_PASSWORD=your_password
```

Pastikan `.env` sudah berada di `.gitignore`.

---

## 11. Channel CCTV

Jika menggunakan Hikvision/NVR, camera channel dapat diatur melalui:

```python
CAMERA_NUMBER = 14
```

Contoh:

```text
CAMERA_NUMBER = 14
```

digunakan untuk:

```text
Cam014
```

Stream:

```python
STREAM_NUMBER = "02"
```

Keterangan:

```text
01 = Main Stream
02 = Sub Stream
```

Contoh:

```text
1401 = Camera 14 Main Stream
1402 = Camera 14 Sub Stream
```

Untuk AI realtime, disarankan mencoba:

```python
STREAM_NUMBER = "02"
```

terlebih dahulu karena lebih ringan.

---

# 12. Menggunakan Video Recording

Copy video ke:

```text
videos/
```

Contoh:

```text
videos/record_cctv.mp4
```

Kemudian pada `config.py`:

```python
CAMERA_MODE = "video"
```

Dan:

```python
VIDEO_PATH = BASE_DIR / "videos" / "record_cctv.mp4"
```

Mode video cocok digunakan untuk:

```text
- testing model
- debugging detection
- tuning confidence
- membandingkan loaded / empty
- testing UI
```

---

# 13. Menjalankan Program

Pastikan virtual environment aktif:

```text
(.venv)
```

Kemudian:

```bash
python main.py
```

Jika menggunakan PyCharm:

```text
1. Open project BarrierGateAI
2. File → Settings
3. Project → Python Interpreter
4. Pilih .venv
5. Buka main.py
6. Klik Run
```

---

# 14. Output Normal

Ketika aplikasi berhasil berjalan, terminal akan menampilkan kira-kira:

```text
Original classes:
{0: 'forklift_empety',
 1: 'forklift_loaded',
 2: 'troli_empety',
 3: 'troli_loaded'}

Fixed classes:
{0: 'forklift_empty',
 1: 'forklift_loaded',
 2: 'troli_empty',
 3: 'troli_loaded'}

Model loaded successfully.

CAMERA_MODE: rtsp

Opening CCTV RTSP...

Camera connected successfully.
```

Jika menggunakan video:

```text
CAMERA_MODE: video

Opening recorded video...
Video: .../videos/record_cctv.mp4
```

---

# 15. Tampilan Aplikasi

UI terdiri dari:

```text
Smart Barrier Gate AI v1.0.0
```

Header menampilkan:

```text
MAX DISTANCE
YOLO inference time
FPS
```

Area kamera dibagi:

```text
ZONA KIRI
ZONA KANAN
```

Status yang dapat muncul:

```text
FORKLIFT KOSONG
FORKLIFT BAWA BARANG

TROLI KOSONG
TROLI BAWA BARANG

OBJECT TIDAK ADA
```

Panel bawah:

```text
VALIDATE KIRI
VALIDATE KANAN
```

---

# 16. Keyboard Control

Saat aplikasi berjalan:

```text
Q     = Keluar
ESC   = Keluar
SPACE = Pause / Resume video
```

Fitur `SPACE` terutama digunakan ketika:

```python
CAMERA_MODE = "video"
```

---

# 17. Confidence Detection

Confidence YOLO dapat diubah pada:

```python
CONFIDENCE = 0.35
```

Contoh:

```python
CONFIDENCE = 0.25
```

lebih sensitif tetapi berpotensi lebih banyak false detection.

```python
CONFIDENCE = 0.50
```

lebih ketat tetapi object dengan confidence rendah dapat tidak terdeteksi.

Starting point:

```python
CONFIDENCE = 0.35
```

---

# 18. Image Size

Default:

```python
IMAGE_SIZE = 640
```

Jika komputer kurang kuat, dapat mencoba:

```python
IMAGE_SIZE = 416
```

atau:

```python
IMAGE_SIZE = 320
```

Semakin kecil image size:

```text
+ inference lebih cepat
+ FPS meningkat
- object kecil lebih sulit terdeteksi
```

---

# 19. FPS

Aplikasi menampilkan FPS realtime.

Contoh:

```text
FPS 7.2
```

FPS tersebut menunjukkan kecepatan keseluruhan proses:

```text
Camera
↓
YOLO
↓
Detection
↓
UI
↓
Display
```

Aplikasi juga menampilkan inference YOLO:

```text
YOLO 42 ms
```

---

# 20. Troubleshooting

## Model Tidak Ditemukan

Error:

```text
FileNotFoundError
```

Pastikan:

```text
models/best.pt
```

tersedia.

---

## Kamera RTSP Tidak Tersambung

Pastikan PC berada di jaringan CCTV.

Test:

```bash
ping <IP_CCTV>
```

Pastikan juga:

```text
IP benar
Username benar
Password benar
RTSP aktif
Port 554 dapat diakses
Channel benar
```

---

## Kamera yang Muncul Salah

Periksa:

```python
CAMERA_NUMBER
```

Contoh:

```python
CAMERA_NUMBER = 14
```

dan:

```python
STREAM_NUMBER = "02"
```

---

## Webcam Tidak Muncul

Coba:

```python
WEBCAM_INDEX = 0
```

kemudian:

```python
WEBCAM_INDEX = 1
```

atau:

```python
WEBCAM_INDEX = 2
```

---

## FPS Rendah

Coba turunkan:

```python
IMAGE_SIZE = 640
```

menjadi:

```python
IMAGE_SIZE = 416
```

atau:

```python
IMAGE_SIZE = 320
```

Gunakan CCTV sub-stream:

```python
STREAM_NUMBER = "02"
```

Pastikan juga aplikasi tidak menjalankan beberapa inference YOLO secara bersamaan.

---

# 21. File yang Tidak Boleh Di-push ke Git

Gunakan `.gitignore`.

Minimal:

```gitignore
# Python
.venv/
venv/
__pycache__/
*.pyc

# PyCharm
.idea/

# Secrets
.env

# AI Models
models/*.pt
models/*.onnx
models/*.xml
models/*.bin

# Videos
videos/*.mp4
videos/*.avi
videos/*.mkv
videos/*.mov

# Training output
runs/
weights/
results/

# OS
Thumbs.db
.DS_Store
```

Jangan commit:

```text
Password CCTV
.env
best.pt
recording CCTV
virtual environment
```

---

# 22. Setelah Clone di Device Baru

Ringkasnya:

```bash
git clone <URL_REPOSITORY>

cd BarrierGateAI

python -m venv .venv

.venv\Scripts\activate

python -m pip install --upgrade pip

pip install -r requirements.txt
```

Kemudian copy:

```text
best.pt
```

ke:

```text
models/best.pt
```

Jika testing video, copy video ke:

```text
videos/
```

Atur:

```python
CAMERA_MODE = "webcam"
```

atau:

```python
CAMERA_MODE = "rtsp"
```

atau:

```python
CAMERA_MODE = "video"
```

Terakhir:

```bash
python main.py
```

---

# 23. Current Detection Scope

Versi saat ini difokuskan untuk mendeteksi:

```text
forklift_empty
forklift_loaded

troli_empty
troli_loaded
```

Pengembangan berikutnya dapat mencakup:

```text
- object tracking
- towing detection
- ROI Gate Kiri / Kanan
- distance validation
- auto gate untuk empty vehicle
- Odoo validation untuk loaded vehicle
- MQTT
- Node-RED
- ESP32
- Boom Barrier
- event logging
- RTSP auto reconnect
```

---

## Project

```text
Smart Barrier Gate AI
Version 1.0.0
```