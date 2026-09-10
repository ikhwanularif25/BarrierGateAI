from ultralytics import YOLO


class Detector:
    """Thin Ultralytics wrapper for the best4 ONNX model."""

    def __init__(
        self,
        model_path,
        confidence=0.35,
        image_size=640,
    ):
        self.model = YOLO(str(model_path))
        self.confidence = float(confidence)
        self.image_size = int(image_size)

        print("Model loaded successfully.")
        print("Model classes:", self.model.names)

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            verbose=False,
        )
        return results[0]
