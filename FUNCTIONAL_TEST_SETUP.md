# Barrier Gate AI - Functional Test Logger

Fitur ini dibuat dari branch `UI2` dan dijalankan terpisah dari `main.py` production.

## Fungsi

Saat AI membaca salah satu class berikut:

- `forklift_loaded`
- `forklift_empty`
- `troli_loaded`
- `troli_empty`

sistem akan:

1. Menentukan zone berdasarkan posisi object (`IN` = sisi kiri, `OUT` = sisi kanan).
2. Membuat snapshot JPEG dengan bounding box, class, confidence, zone, dan timestamp.
3. Menyimpan snapshot lokal ke folder `functional_test_snapshots/`.
4. Mengirim event + gambar ke Google Apps Script secara asynchronous.
5. Apps Script menyimpan gambar ke Google Drive dan menambahkan satu row ke Google Spreadsheet.
6. Cooldown mencegah satu object ditulis setiap frame.

## 1. Google Spreadsheet

Buat Google Spreadsheet baru. Ambil Spreadsheet ID dari URL:

`https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`

Tidak perlu membuat sheet manual. Sheet `FUNCTIONAL_TEST` akan dibuat otomatis bila belum ada.

## 2. Google Drive Folder

Buat folder untuk snapshot functional test. Ambil Folder ID dari URL folder Drive.

## 3. Google Apps Script

Buka Apps Script dan copy isi:

`google_apps_script/Code.gs`

Isi:

```javascript
SPREADSHEET_ID: 'PASTE_SPREADSHEET_ID_HERE',
DRIVE_FOLDER_ID: 'PASTE_DRIVE_FOLDER_ID_HERE'
```

Jalankan `testSetup()` satu kali dan approve akses Spreadsheet + Drive.

Lalu Deploy > New deployment > Web app.

Setting yang disarankan untuk jaringan internal test:

- Execute as: Me
- Who has access: Anyone yang diizinkan oleh kebijakan Google Workspace perusahaan

Copy Web App URL hasil deployment.

## 4. Tambahkan ke `.env`

```env
FUNCTION_TEST_WEBHOOK_URL=https://script.google.com/macros/s/DEPLOYMENT_ID/exec
FUNCTION_TEST_COOLDOWN=10
```

`FUNCTION_TEST_COOLDOWN=10` berarti class yang sama pada zone yang sama baru boleh dicatat lagi setelah 10 detik.

## 5. Jalankan

Aktifkan environment project lalu:

```bash
python functional_test.py
```

Keluar dengan `Q` atau `ESC`.

## Data Spreadsheet

Kolom yang dibuat otomatis:

| Timestamp | Event ID | Camera | Zone | Detection | Load Status | Confidence | Source | Snapshot File | Image URL |
|---|---|---|---|---|---|---:|---|---|---|

Contoh:

| 2026-09-01 08:25:10 | a1b2c3d4e5f6 | CAM014 | IN | forklift_loaded | LOADED | 0.9123 | FUNCTIONAL_TEST | ...jpg | Drive URL |

## Catatan performa

Request HTTP tidak dijalankan di thread inference. Event dimasukkan ke queue dan dikirim oleh worker thread agar koneksi internet atau Apps Script yang lambat tidak menghentikan YOLO.

Snapshot lokal tetap dibuat walaupun `FUNCTION_TEST_WEBHOOK_URL` belum diisi atau Spreadsheet sedang tidak dapat diakses.
