from ultralytics import YOLO

# 1. Load model yang sudah selesai di-training
model = YOLO("models/best.pt")  # ganti dengan lokasi file best.pt kamu

# 2. Export ke format ONNX
model.export(
    format="onnx",
    dynamic=True,  # memfasilitasi ukuran batch/resolusi dinamis jika diperlukan
    simplify=True,  # mengoptimalkan struktur graph ONNX agar lebih ringan
)