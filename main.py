import cv2
import time

from config import (
    MODEL_PATH,
    CONFIDENCE,
    IMAGE_SIZE,
    WINDOW_NAME,

    CAMERA_MODE,
    WEBCAM_INDEX,
    VIDEO_PATH,

    CCTV_IP,
    STREAM_NUMBER,
    get_rtsp_url,
    get_cctv_channel,

    CAMERA_AUTO_ROTATE,
    CAMERA_START,
    CAMERA_END,
    CAMERA_SWITCH_INTERVAL,

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
# OPEN RTSP CAMERA
# =========================================================

def open_rtsp_camera(camera_number):

    rtsp_url = get_rtsp_url(
        camera_number
    )

    channel = get_cctv_channel(
        camera_number
    )

    print()
    print("=" * 60)
    print(
        f"OPENING Cam{camera_number:03d}"
    )
    print(
        f"Channel : {channel}"
    )
    print(
        f"IP      : {CCTV_IP}"
    )
    print("=" * 60)

    cap = cv2.VideoCapture(
        rtsp_url,
        cv2.CAP_FFMPEG
    )

    cap.set(
        cv2.CAP_PROP_BUFFERSIZE,
        1
    )

    if cap.isOpened():

        print(
            f"Cam{camera_number:03d} connected successfully."
        )

    else:

        print(
            f"WARNING: Cam{camera_number:03d} "
            f"tidak dapat dibuka."
        )

    return cap


# =========================================================
# OPEN CAMERA
# =========================================================

def open_camera(
    camera_number=None
):

    mode = CAMERA_MODE.strip().lower()

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
            WEBCAM_INDEX,
            cv2.CAP_DSHOW
        )

        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        return cap

    # =====================================================
    # RTSP
    # =====================================================

    elif mode == "rtsp":

        if camera_number is None:
            camera_number = CAMERA_START

        return open_rtsp_camera(
            camera_number
        )

    # =====================================================
    # VIDEO
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

        return cv2.VideoCapture(
            str(VIDEO_PATH)
        )

    else:

        raise ValueError(
            f"CAMERA_MODE tidak valid: "
            f"{CAMERA_MODE}. "
            f"Gunakan 'webcam', 'rtsp', "
            f"atau 'video'."
        )


# =========================================================
# GET NEXT CAMERA
# =========================================================

def get_next_camera(
    current_camera
):

    next_camera = (
        current_camera + 1
    )

    if next_camera > CAMERA_END:

        next_camera = (
            CAMERA_START
        )

    return next_camera


# =========================================================
# SWITCH CAMERA
# =========================================================

def switch_camera(
    cap,
    current_camera
):

    if cap is not None:

        cap.release()

    next_camera = get_next_camera(
        current_camera
    )

    print()
    print(
        f"Switching "
        f"Cam{current_camera:03d}"
        f" -> "
        f"Cam{next_camera:03d}"
    )

    new_cap = open_rtsp_camera(
        next_camera
    )

    return (
        new_cap,
        next_camera
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
    # CURRENT CAMERA
    # =====================================================

    current_camera = (
        CAMERA_START
    )

    # =====================================================
    # OPEN CAMERA
    # =====================================================

    cap = open_camera(
        current_camera
        if mode == "rtsp"
        else None
    )

    if not cap.isOpened():

        print(
            "ERROR: Kamera pertama "
            "tidak dapat dibuka."
        )

        # Kalau RTSP rotation aktif,
        # jangan langsung matikan aplikasi.
        if not (
            mode == "rtsp"
            and CAMERA_AUTO_ROTATE
        ):

            return

    # =====================================================
    # CAMERA SWITCH TIMER
    # =====================================================

    camera_switch_time = (
        time.monotonic()
    )

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
    # LOOP
    # =====================================================

    while True:

        # =================================================
        # AUTO SWITCH CAMERA
        # =================================================

        if (
            mode == "rtsp"
            and CAMERA_AUTO_ROTATE
        ):

            elapsed = (
                time.monotonic()
                - camera_switch_time
            )

            if (
                elapsed
                >= CAMERA_SWITCH_INTERVAL
            ):

                (
                    cap,
                    current_camera
                ) = switch_camera(
                    cap,
                    current_camera
                )

                camera_switch_time = (
                    time.monotonic()
                )

                # Reset FPS supaya tidak kacau
                # setelah reconnect.
                previous_time = (
                    time.perf_counter()
                )

                fps_smooth = 0.0

                continue

        # =================================================
        # READ FRAME
        # =================================================

        ret, frame = cap.read()

        if not ret:

            print(
                f"Frame gagal dibaca"
                + (
                    f" dari Cam"
                    f"{current_camera:03d}"
                    if mode == "rtsp"
                    else ""
                )
            )

            # =============================================
            # RTSP: SKIP CAMERA ERROR
            # =============================================

            if (
                mode == "rtsp"
                and CAMERA_AUTO_ROTATE
            ):

                (
                    cap,
                    current_camera
                ) = switch_camera(
                    cap,
                    current_camera
                )

                camera_switch_time = (
                    time.monotonic()
                )

                previous_time = (
                    time.perf_counter()
                )

                fps_smooth = 0.0

                continue

            # =============================================
            # VIDEO: LOOP
            # =============================================

            elif mode == "video":

                print(
                    "Video selesai. Restart..."
                )

                cap.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    0
                )

                continue

            else:

                break

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
        # DETECTION DATA
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
                    "class_id": class_id,
                    "name": class_name,
                    "confidence": confidence,

                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
            )

        # =================================================
        # FPS
        # =================================================

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
                1.0
                / delta
            )

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
        # CAMERA INFO OVERLAY
        # =================================================

        if mode == "rtsp":

            camera_text = (
                f"CAM {current_camera:03d}"
            )

            cv2.putText(
                display,
                camera_text,
                (25, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Countdown camera switch
            elapsed = (
                time.monotonic()
                - camera_switch_time
            )

            remaining = max(
                0,
                CAMERA_SWITCH_INTERVAL
                - elapsed
            )

            switch_text = (
                f"NEXT CAMERA: "
                f"{remaining:.1f}s"
            )

            cv2.putText(
                display,
                switch_text,
                (25, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
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

        # Q / ESC
        if (
            key == ord("q")
            or key == 27
        ):

            break

        # N = manual next camera
        if (
            key == ord("n")
            and mode == "rtsp"
        ):

            (
                cap,
                current_camera
            ) = switch_camera(
                cap,
                current_camera
            )

            camera_switch_time = (
                time.monotonic()
            )

            previous_time = (
                time.perf_counter()
            )

            fps_smooth = 0.0

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