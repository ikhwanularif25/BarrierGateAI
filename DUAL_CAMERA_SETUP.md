# Dua CCTV

Jalankan `main.py` untuk pemantauan atau `functional_test.py` untuk pemantauan beserta integrasi functional test yang sudah ada.

- Kiri: 192.168.6.101
- Kanan: 192.168.6.100
- Username, password, port, nomor kamera/channel, dan substream memakai pengaturan lama di `.env` untuk kedua CCTV.
- Kedua stream dibaca pada thread terpisah dengan reconnect otomatis. Frame terputus atau berumur lebih dari 2 detik tidak ditampilkan sebagai LIVE.
- Setiap panel menampilkan deteksi, ROI dan statusnya sendiri. Rasio gambar dipertahankan.
- Tombol 1: simulasi validasi kiri, 2: simulasi validasi kanan, R: reset, F: fullscreen, Q/Esc: keluar. Tombol ini tetap simulasi; tidak mengirim perintah portal.

Pada `functional_test.py`, Node-RED dan snapshot/webhook tetap menggunakan kamera kanan dengan identitas CAM lama dan zone OUT. Kamera kiri untuk pemantauan dan status lokal; integrasi portal kamera kiri memerlukan penentuan zone dan identitas kamera terpisah.

Pengaturan opsional di `.env` (jangan masukkan tanda kutip):

```
DUAL_CAMERA_ENABLED=1
CCTV_LEFT_IP=192.168.6.101
CCTV_RIGHT_IP=192.168.6.100
```

Jika channel atau kredensial kemudian berbeda, tambahkan variabel sesuai sisi: `CCTV_LEFT_USERNAME`, `CCTV_LEFT_PASSWORD`, `CCTV_LEFT_PORT`, `CCTV_LEFT_CAMERA_NUMBER`, `CCTV_LEFT_STREAM_NUMBER`, atau versi `CCTV_RIGHT_...`. Variabel yang tidak diisi memakai pengaturan lama. `DUAL_CAMERA_ENABLED=0` mengembalikan mode satu kamera lama.

Verifikasi offline mencakup layout 1920x1080, 1366x768 dan 1280x720, kedua kondisi putus, validasi terpisah, dan penutupan stream. Akses langsung CCTV serta FPS model pada dua stream harus dicek saat aplikasi dijalankan di lokasi.

## Kinerja video dan AI

Video MASUK dan KELUAR diperbarui tanpa menunggu inferensi. Satu worker AI memproses frame terbaru dari masing-masing kamera secara bergantian; frame lama tidak mengantre. Header DISPLAY menunjukkan laju pembaruan tampilan, sedangkan AI pada tiap panel menunjukkan laju hasil deteksi kamera tersebut. Laju video asli tetap mengikuti pengaturan stream CCTV.

Hasil deteksi berumur lebih dari 1 detik dihapus dan panel menampilkan MENUNGGU AI, bukan menganggap area kosong. Integrasi Node-RED hanya menggunakan frame yang benar-benar telah diinferensi dan hasil baru tidak dikirim berulang karena refresh video.

Target pembaruan tampilan default 30 FPS, dapat diubah lewat `DISPLAY_TARGET_FPS=30` di `.env` (1–60). Ini target, bukan jaminan FPS. ONNX pada CPU memakai thread model terbatas tanpa busy spinning serta satu thread untuk pre/post-processing. Default `ONNX_CPU_THREADS` maksimal 8 atau setengah logical CPU, bisa diatur di `.env`. Backend GPU tetap memakai pengaturan sebelumnya. Model, input 416, threshold confidence, dan ROI tidak diturunkan untuk optimasi ini.
