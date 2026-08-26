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
from camera import LatestFrameCamera


# =========================================================
# OPEN CAMERA
# =========================================================

def open_camera():

    mode = (
        CAMERA_MODE
        .strip()
        .lower()
    )

    print(
        "CAMERA_MODE:",
        mode
    )

    # =====================================================
    # WEBCAM
    # =====================================================

    if mode == "webcam":

        print(
            "Opening Webcam..."
        )

        cap = cv2.VideoCapture(
            WEBCAM_INDEX
        )

        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        return cap

    # =====================================================
    # RTSP CCTV
    # =====================================================

    elif mode == "rtsp":

        print(
            "Opening CCTV RTSP..."
        )

        print(
            f"Camera : "
            f"Cam{CAMERA_NUMBER:03d}"
        )

        print(
            f"Channel: "
            f"{CCTV_CHANNEL}"
        )

        camera = LatestFrameCamera(
            source=RTSP_URL,
            backend=cv2.CAP_FFMPEG,
            reconnect=True,
            reconnect_delay=1.0
        )

        camera.start()

        # -------------------------------------------------
        # WAIT FOR FIRST FRAME
        # -------------------------------------------------

        print(
            "Waiting first RTSP frame..."
        )

        start_wait = (
            time.perf_counter()
        )

        while (
            time.perf_counter()
            - start_wait
            < 8
        ):

            (
                ret,
                frame,
                frame_timestamp,
                frame_id
            ) = camera.read()

            if ret:

                print(
                    "RTSP camera connected successfully."
                )

                print(
                    "Resolution:",
                    f"{frame.shape[1]}"
                    f"x"
                    f"{frame.shape[0]}"
                )

                return camera

            time.sleep(
                0.05
            )

        camera.release()

        raise RuntimeError(
            "RTSP tidak menghasilkan "
            "frame dalam 8 detik."
        )

    # =====================================================
    # VIDEO FILE
    # =====================================================

    elif mode == "video":

        print(
            "Opening recorded video..."
        )

        print(
            "Video:",
            VIDEO_PATH
        )

        if not VIDEO_PATH.exists():

            raise FileNotFoundError(
                f"Video tidak ditemukan: "
                f"{VIDEO_PATH}"
            )

        cap = cv2.VideoCapture(
            str(VIDEO_PATH)
        )

        return cap

    # =====================================================
    # INVALID
    # =====================================================

    else:

        raise ValueError(
            f"CAMERA_MODE tidak valid: "
            f"{CAMERA_MODE}. "
            f"Gunakan 'webcam', "
            f"'rtsp', atau 'video'."
        )


# =========================================================
# MAIN
# =========================================================

def main():

    mode = (
        CAMERA_MODE
        .strip()
        .lower()
    )

    # =====================================================
    # MODEL
    # =====================================================

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE
    )

    # =====================================================
    # UI
    # =====================================================

    ui = BarrierGateUI(
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        top_height=TOP_BAR_HEIGHT,
        bottom_height=BOTTOM_PANEL_HEIGHT,
        max_distance=MAX_DISTANCE
    )

    # =====================================================
    # CAMERA
    # =====================================================

    camera = open_camera()

    if not camera.isOpened():

        print(
            "ERROR: Kamera tidak dapat dibuka."
        )

        return

    # =====================================================
    # WINDOW
    # =====================================================

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

    # =====================================================
    # FPS
    # =====================================================

    previous_time = (
        time.perf_counter()
    )

    fps = 0.0
    fps_smooth = 0.0

    # =====================================================
    # FRAME TRACKING
    # =====================================================

    last_frame_id = -1

    # =====================================================
    # MAIN LOOP
    # =====================================================

    while True:

        # =================================================
        # GET FRAME
        # =================================================

        if mode == "rtsp":

            (
                ret,
                frame,
                frame_timestamp,
                frame_id
            ) = camera.read()

            if not ret:

                time.sleep(
                    0.005
                )

                continue

            # ---------------------------------------------
            # Jangan process frame yang sama dua kali
            # ---------------------------------------------

            if frame_id == last_frame_id:

                time.sleep(
                    0.001
                )

                continue

            last_frame_id = frame_id

            # ---------------------------------------------
            # Umur frame sebelum inference
            # ---------------------------------------------

            frame_age_before_ms = (
                time.perf_counter()
                - frame_timestamp
            ) * 1000

        else:

            ret, frame = (
                camera.read()
            )

            if not ret:

                # =========================================
                # VIDEO LOOP
                # =========================================

                if mode == "video":

                    print(
                        "Video selesai. Restart..."
                    )

                    camera.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        0
                    )

                    continue

                print(
                    "Frame kamera gagal dibaca."
                )

                break

            frame_age_before_ms = 0.0

        # =================================================
        # YOLO
        # =================================================

        result = detector.detect(
            frame
        )

        # =================================================
        # INFERENCE TIME
        # =================================================

        inference_ms = 0.0

        if hasattr(
            result,
            "speed"
        ):

            inference_ms = (
                result.speed.get(
                    "inference",
                    0.0
                )
            )

        # =================================================
        # DETECTIONS
        # =================================================

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
                    "class_id":
                        class_id,

                    "name":
                        class_name,

                    "confidence":
                        confidence,

                    "x1":
                        x1,

                    "y1":
                        y1,

                    "x2":
                        x2,

                    "y2":
                        y2
                }
            )

        # =================================================
        # FPS
        # =================================================

        now = (
            time.perf_counter()
        )

        delta = (
            now
            - previous_time
        )

        previous_time = now

        if delta > 0:

            fps = (
                1.0
                / delta
            )

        if fps_smooth == 0:

            fps_smooth = fps

        else:

            fps_smooth = (
                (fps_smooth * 0.90)
                +
                (fps * 0.10)
            )

        # =================================================
        # UI
        # =================================================

        display = ui.render(
            frame=frame,
            detections=detections,
            fps=fps_smooth,
            inference_ms=inference_ms
        )

        # =================================================
        # DEBUG LATENCY
        # =================================================

        if mode == "rtsp":

            total_frame_age_ms = (
                time.perf_counter()
                - frame_timestamp
            ) * 1000

            latency_text = (
                f"LATENCY "
                f"{total_frame_age_ms:.0f} ms"
            )

            # Green
            latency_color = (
                80,
                255,
                80
            )

            # Yellow > 300ms
            if total_frame_age_ms > 300:

                latency_color = (
                    0,
                    255,
                    255
                )

            # Red > 1000ms
            if total_frame_age_ms > 1000:

                latency_color = (
                    0,
                    0,
                    255
                )

            cv2.putText(
                display,
                latency_text,
                (
                    DISPLAY_WIDTH - 350,
                    68
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                latency_color,
                2,
                cv2.LINE_AA
            )

        # =================================================
        # SHOW
        # =================================================

        cv2.imshow(
            WINDOW_NAME,
            display
        )

        # =================================================
        # KEYBOARD
        # =================================================

        key = (
            cv2.waitKey(1)
            & 0xFF
        )

        if (
            key == ord("q")
            or
            key == 27
        ):

            break

    # =====================================================
    # CLEANUP
    # =====================================================

    camera.release()

    cv2.destroyAllWindows()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()