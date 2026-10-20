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
        self.model_path = str(model_path)
        self._cpu_session_configured = False
        if self.model_path.lower().endswith(".onnx"):
            self.model.add_callback("on_predict_start", self._configure_cpu_session)

        print("Model loaded successfully.")
        print("Model classes:", self.model.names)

    def _configure_cpu_session(self, predictor):
        """Avoid CPU thread pools spinning while the UI needs to render video."""
        if self._cpu_session_configured:
            return
        self._cpu_session_configured = True
        backend = getattr(predictor.model, "backend", predictor.model)
        session = getattr(backend, "session", None)
        if session is None or session.get_providers() != ["CPUExecutionProvider"]:
            return
        try:
            import onnxruntime as ort
            import torch
            from config import ONNX_CPU_THREADS
            options = ort.SessionOptions()
            options.intra_op_num_threads = ONNX_CPU_THREADS
            options.inter_op_num_threads = 1
            options.add_session_config_entry("session.intra_op.allow_spinning", "0")
            options.add_session_config_entry("session.inter_op.allow_spinning", "0")
            tuned = ort.InferenceSession(self.model_path, sess_options=options,
                                         providers=["CPUExecutionProvider"])
            backend.session = tuned
            # ONNX performs model math; Torch is only used for pre/post-processing.
            torch.set_num_threads(1)
            print(f"ONNX CPU optimized: {ONNX_CPU_THREADS} model threads, 1 preprocessing thread")
        except Exception as exc:
            # Keep the existing working backend if optional tuning is unavailable.
            print(f"ONNX CPU tuning skipped ({type(exc).__name__})")

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            verbose=False,
        )
        return results[0]
