from ultralytics import YOLO


class Detector:

    def __init__(
        self,
        model_path,
        confidence=0.35,
        image_size=640
    ):

        self.model = YOLO(str(model_path))

        # =====================================================
        # FIX TYPO CLASS NAME
        # =====================================================

        print("Original classes:")
        print(self.model.names)

        fixed_names = {}

        for class_id, class_name in self.model.names.items():

            # Perbaiki typo empety -> empty
            fixed_name = class_name.replace("empety", "empty")

            fixed_names[class_id] = fixed_name

        # Ubah names pada model internal Ultralytics
        self.model.model.names = fixed_names

        print("Fixed classes:")
        print(self.model.names)

        # =====================================================
        # CONFIG
        # =====================================================

        self.confidence = confidence
        self.image_size = image_size

        print("Model loaded successfully.")

    def detect(self, frame):

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            verbose=False
        )

        return results[0]