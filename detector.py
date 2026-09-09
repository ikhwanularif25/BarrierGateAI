# detector.py
from ultralytics import YOLO

class Detector:

    def __init__(
        self,
        model_path,
        confidence=0.35,
        image_size=640
    ):
        self.model = YOLO(str(model_path), task="detect")
        self.confidence = confidence
        self.image_size = image_size

        print("Model ONNX loaded successfully.")

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            # device="0",
            verbose=False
        )

        return results[0]