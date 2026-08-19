import cv2
import time

from config import (
    MODEL_PATH,
    CONFIDENCE,
    IMAGE_SIZE,
    WINDOW_NAME,
    CAMERA_MODE,
    WEBCAM_INDEX,
    RTSP_URL,
    CAMERA_NUMBER,
    CCTV_CHANNEL,
    VIDEO_PATH,
    FULLSCREEN,
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
    TOP_BAR_HEIGHT,
    BOTTOM_PANEL_HEIGHT,
    MAX_DISTANCE
)

from detector import Detector
from ui import BarrierGateUI


# =========================================================
# OPEN CAMERA
# =========================================================

def open_camera():

    mode = CAMERA_MODE.strip().lower()

    print("CAMERA_MODE:", mode)

    # =====================================================
    # WEBCAM
    # =====================================================

    if mode == "webcam":

        print("Opening Webcam...")

        cap = cv2.VideoCapture(
            WEBCAM_INDEX,
            cv2.CAP_DSHOW
        )

    # =====================================================
    # RTSP CCTV
    # =====================================================

    elif mode == "rtsp":

        print("Opening CCTV RTSP...")
        print(f"Camera : Cam{CAMERA_NUMBER:03d}")
        print(f"Channel: {CCTV_CHANNEL}")

        cap = cv2.VideoCapture(
            RTSP_URL,
            cv2.CAP_FFMPEG
        )

    # =====================================================
    # VIDEO FILE
    # =====================================================

    elif mode == "video":

        print("Opening recorded video...")
        print("Video:", VIDEO_PATH)

        if not VIDEO_PATH.exists():

            raise FileNotFoundError(
                f"Video tidak ditemukan: {VIDEO_PATH}"
            )

        cap = cv2.VideoCapture(
            str(VIDEO_PATH)
        )

    else:

        raise ValueError(
            f"CAMERA_MODE tidak valid: {CAMERA_MODE}. "
            "Gunakan 'webcam', 'rtsp', atau 'video'."
        )

    # Untuk webcam / RTSP
    if mode != "video":

        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

    return cap


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # MODEL
    # -----------------------------------------------------

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE
    )

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------

    ui = BarrierGateUI(
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        top_height=TOP_BAR_HEIGHT,
        bottom_height=BOTTOM_PANEL_HEIGHT,
        max_distance=MAX_DISTANCE
    )

    # -----------------------------------------------------
    # CAMERA
    # -----------------------------------------------------

    cap = open_camera()

    if not cap.isOpened():

        print(
            "ERROR: Kamera tidak dapat dibuka."
        )

        return

    print(
        "Camera connected successfully."
    )

    camera_fps = cap.get(
        cv2.CAP_PROP_FPS
    )

    print(
        f"Camera FPS: {camera_fps:.1f}"
    )

    # -----------------------------------------------------
    # WINDOW
    # -----------------------------------------------------

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL
    )

    if FULLSCREEN:

        cv2.setWindowProperty(
            WINDOW_NAME,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )

    # -----------------------------------------------------
    # FPS
    # -----------------------------------------------------

    previous_time = time.perf_counter()

    fps = 0.0

    # Smooth FPS
    fps_smooth = 0.0

    # =====================================================
    # LOOP
    # =====================================================

    while True:

        ret, frame = cap.read()

        if not ret:

            print(
                "Frame kamera gagal dibaca."
            )

            break

        # -------------------------------------------------
        # YOLO
        # -------------------------------------------------

        result = detector.detect(
            frame
        )

        # -------------------------------------------------
        # INFERENCE TIME
        # -------------------------------------------------

        inference_ms = 0.0

        if hasattr(
            result,
            "speed"
        ):

            inference_ms = result.speed.get(
                "inference",
                0.0
            )

        # -------------------------------------------------
        # DETECTION DATA
        # -------------------------------------------------

        detections = []

        for box in result.boxes:

            class_id = int(
                box.cls[0]
            )

            confidence = float(
                box.conf[0]
            )

            class_name = (
                detector
                .model
                .names[class_id]
            )

            x1, y1, x2, y2 = (
                box.xyxy[0]
                .cpu()
                .numpy()
                .astype(int)
            )

            detections.append(
                {
                    "class_id": class_id,
                    "name": class_name,
                    "confidence": confidence,

                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
            )

        # -------------------------------------------------
        # FPS
        # -------------------------------------------------

        current_time = (
            time.perf_counter()
        )

        delta = (
            current_time
            - previous_time
        )

        previous_time = (
            current_time
        )

        if delta > 0:

            fps = (
                1.0 / delta
            )

        # Smooth FPS supaya angka tidak loncat-loncat
        if fps_smooth == 0:

            fps_smooth = fps

        else:

            fps_smooth = (
                0.90
                * fps_smooth
                +
                0.10
                * fps
            )

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        display = ui.render(
            frame=frame,
            detections=detections,
            fps=fps_smooth,
            inference_ms=inference_ms
        )

        # -------------------------------------------------
        # SHOW
        # -------------------------------------------------

        cv2.imshow(
            WINDOW_NAME,
            display
        )

        # -------------------------------------------------
        # KEYBOARD
        # -------------------------------------------------

        key = (
            cv2.waitKey(1)
            & 0xFF
        )

        # Q / ESC
        if (
            key == ord("q")
            or
            key == 27
        ):

            break

    # =====================================================
    # CLEANUP
    # =====================================================

    cap.release()

    cv2.destroyAllWindows()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()