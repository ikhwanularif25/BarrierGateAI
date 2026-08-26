import cv2
import time
import numpy as np
import ctypes

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
# SCREEN RESOLUTION
# =========================================================

def get_screen_resolution():
    """
    Ambil resolusi monitor Windows secara aktual.
    Fallback ke DISPLAY_WIDTH / DISPLAY_HEIGHT dari config.
    """

    try:
        user32 = ctypes.windll.user32

        # Agar Windows DPI scaling tidak membuat ukuran salah
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)

        if width > 0 and height > 0:
            return width, height

    except Exception as e:
        print(
            "WARNING: Tidak dapat membaca resolusi monitor:",
            e
        )

    return DISPLAY_WIDTH, DISPLAY_HEIGHT


# =========================================================
# OPEN CAMERA
# =========================================================

def open_camera():
    mode = CAMERA_MODE.strip().lower()

    print()
    print("=" * 70)
    print("AI POWERED SMART BARRIER GATE")
    print("=" * 70)
    print("CAMERA_MODE :", mode)

    # =====================================================
    # WEBCAM
    # =====================================================

    if mode == "webcam":

        print("Opening Webcam...")
        print("Webcam Index:", WEBCAM_INDEX)

        cap = cv2.VideoCapture(
            WEBCAM_INDEX,
            cv2.CAP_DSHOW
        )

        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        if not cap.isOpened():

            # Coba backend default kalau DirectShow gagal
            print(
                "DirectShow gagal. "
                "Mencoba backend default..."
            )

            cap.release()

            cap = cv2.VideoCapture(
                WEBCAM_INDEX
            )

        if not cap.isOpened():
            raise RuntimeError(
                f"Webcam index {WEBCAM_INDEX} "
                "tidak dapat dibuka."
            )

        width = int(
            cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        height = int(
            cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        fps = cap.get(
            cv2.CAP_PROP_FPS
        )

        print(
            f"Webcam Resolution : "
            f"{width}x{height}"
        )

        print(
            f"Webcam FPS        : "
            f"{fps:.1f}"
        )

        return cap

    # =====================================================
    # RTSP CCTV
    # =====================================================

    elif mode == "rtsp":

        print("Opening CCTV RTSP...")

        print(
            f"Camera            : "
            f"Cam{CAMERA_NUMBER:03d}"
        )

        print(
            f"RTSP Channel      : "
            f"{CCTV_CHANNEL}"
        )

        camera = LatestFrameCamera(
            source=RTSP_URL,
            backend=cv2.CAP_FFMPEG,
            reconnect=True,
            reconnect_delay=1.0
        )

        camera.start()

        print(
            "Waiting for first RTSP frame..."
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
                    f"RTSP Resolution   : "
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

        if not cap.isOpened():

            raise RuntimeError(
                "Video tidak dapat dibuka."
            )

        width = int(
            cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        height = int(
            cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        fps = cap.get(
            cv2.CAP_PROP_FPS
        )

        print(
            f"Video Resolution  : "
            f"{width}x{height}"
        )

        print(
            f"Video FPS         : "
            f"{fps:.1f}"
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
    # SCREEN
    # =====================================================

    screen_width, screen_height = (
        get_screen_resolution()
    )

    print()
    print(
        f"Screen Resolution : "
        f"{screen_width}x{screen_height}"
    )

    # =====================================================
    # LOAD MODEL
    # =====================================================

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE
    )

    print(
        f"YOLO Confidence   : "
        f"{CONFIDENCE}"
    )

    print(
        f"YOLO Image Size   : "
        f"{IMAGE_SIZE}"
    )

    # =====================================================
    # UI
    # =====================================================

    # Scaling UI berdasarkan resolusi layar.
    scale_y = (
        screen_height / 1080.0
    )

    top_height = max(
        80,
        int(
            TOP_BAR_HEIGHT
            * scale_y
        )
    )

    bottom_height = max(
        55,
        int(
            BOTTOM_PANEL_HEIGHT
            * scale_y
        )
    )

    ui = BarrierGateUI(
        width=screen_width,
        height=screen_height,
        top_height=top_height,
        bottom_height=bottom_height,
        max_distance=MAX_DISTANCE
    )

    # =====================================================
    # ODOO VALIDATE SIMULATION
    # =====================================================

    # Nantinya diganti input asli dari Odoo / Node-RED / API.

    validate_left = False
    validate_right = False

    # =====================================================
    # OPEN CAMERA
    # =====================================================

    camera = open_camera()

    if not camera.isOpened():

        print(
            "ERROR: Kamera tidak dapat dibuka."
        )

        return

    # =====================================================
    # WINDOW INITIALIZATION
    # =====================================================

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL
    )

    # Tampilkan satu frame kosong dulu.
    # Ini membantu fullscreen OpenCV lebih stabil di Windows.
    startup_frame = np.zeros(
        (
            screen_height,
            screen_width,
            3
        ),
        dtype=np.uint8
    )

    cv2.putText(
        startup_frame,
        "AI POWERED SMART BARRIER GATE",
        (
            max(
                40,
                screen_width // 4
            ),
            screen_height // 2
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (
            0,
            230,
            255
        ),
        3,
        cv2.LINE_AA
    )

    cv2.imshow(
        WINDOW_NAME,
        startup_frame
    )

    cv2.waitKey(
        200
    )

    # =====================================================
    # FULLSCREEN
    # =====================================================

    if FULLSCREEN:

        cv2.setWindowProperty(
            WINDOW_NAME,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )

        # Beri waktu Windows mengubah state window
        cv2.waitKey(
            100
        )

    else:

        cv2.resizeWindow(
            WINDOW_NAME,
            screen_width,
            screen_height
        )

    # =====================================================
    # FPS VARIABLES
    # =====================================================

    previous_time = (
        time.perf_counter()
    )

    fps = 0.0
    fps_smooth = 0.0

    # =====================================================
    # FRAME TRACKING RTSP
    # =====================================================

    last_frame_id = -1

    # =====================================================
    # DEBUG
    # =====================================================

    last_detection_count = -1
    last_debug_time = 0.0

    # =====================================================
    # LOOP
    # =====================================================

    try:

        while True:

            # =================================================
            # READ FRAME
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

                # Hindari process frame yang sama
                if frame_id == last_frame_id:

                    time.sleep(
                        0.001
                    )

                    continue

                last_frame_id = (
                    frame_id
                )

            else:

                ret, frame = (
                    camera.read()
                )

                if not ret:

                    # =========================================
                    # VIDEO RESTART
                    # =========================================

                    if mode == "video":

                        print(
                            "Video selesai. "
                            "Restart dari awal..."
                        )

                        camera.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            0
                        )

                        previous_time = (
                            time.perf_counter()
                        )

                        continue

                    print(
                        "Frame kamera gagal dibaca."
                    )

                    break

                frame_timestamp = (
                    time.perf_counter()
                )

            # =================================================
            # YOLO
            # =================================================

            result = detector.detect(
                frame
            )

            # =================================================
            # DETECTION DEBUG
            # =================================================

            detection_count = len(
                result.boxes
            )

            debug_now = (
                time.perf_counter()
            )

            # Print maksimal kira-kira setiap 0.5 detik
            # agar terminal tidak menjadi bottleneck.
            if (
                debug_now
                - last_debug_time
                >= 0.5
            ):

                print(
                    f"Detections: "
                    f"{detection_count}",
                    end=""
                )

                if detection_count > 0:

                    print(
                        " | ",
                        end=""
                    )

                    debug_objects = []

                    for box in result.boxes:

                        debug_class_id = int(
                            box.cls[0]
                        )

                        debug_conf = float(
                            box.conf[0]
                        )

                        debug_name = (
                            detector
                            .model
                            .names[
                                debug_class_id
                            ]
                        )

                        debug_objects.append(
                            f"{debug_name} "
                            f"{debug_conf:.2f}"
                        )

                    print(
                        ", ".join(
                            debug_objects
                        )
                    )

                else:

                    print()

                last_debug_time = (
                    debug_now
                )

                last_detection_count = (
                    detection_count
                )

            # =================================================
            # YOLO INFERENCE
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
            # CONVERT YOLO RESULTS
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
                    .names[
                        class_id
                    ]
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
                            int(x1),

                        "y1":
                            int(y1),

                        "x2":
                            int(x2),

                        "y2":
                            int(y2)
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

            # Smooth FPS
            if fps_smooth == 0:

                fps_smooth = fps

            else:

                fps_smooth = (
                    (
                        fps_smooth
                        * 0.90
                    )
                    +
                    (
                        fps
                        * 0.10
                    )
                )

            # =================================================
            # UI RENDER
            # =================================================

            display = ui.render(
                frame=frame,
                detections=detections,
                fps=fps_smooth,
                inference_ms=inference_ms,
                validate_left=validate_left,
                validate_right=validate_right
            )

            # =================================================
            # LATENCY
            # =================================================

            if mode == "rtsp":

                total_latency_ms = (
                    time.perf_counter()
                    - frame_timestamp
                ) * 1000

                latency_text = (
                    f"LATENCY "
                    f"{total_latency_ms:.0f} MS"
                )

                # Good
                latency_color = (
                    80,
                    255,
                    80
                )

                # Warning
                if total_latency_ms > 300:

                    latency_color = (
                        0,
                        255,
                        255
                    )

                # Bad
                if total_latency_ms > 1000:

                    latency_color = (
                        0,
                        0,
                        255
                    )

                text_size = (
                    cv2.getTextSize(
                        latency_text,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        2
                    )[0]
                )

                latency_x = (
                    screen_width
                    - text_size[0]
                    - 300
                )

                latency_y = max(
                    35,
                    int(
                        top_height
                        * 0.92
                    )
                )

                cv2.putText(
                    display,
                    latency_text,
                    (
                        latency_x,
                        latency_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    latency_color,
                    2,
                    cv2.LINE_AA
                )

            # =================================================
            # DEBUG DETECTION COUNT ON SCREEN
            # =================================================

            detection_text = (
                f"DET {detection_count}"
            )

            cv2.putText(
                display,
                detection_text,
                (
                    max(
                        15,
                        screen_width - 470
                    ),
                    35
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (
                    255,
                    255,
                    255
                ),
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

            # -------------------------------------------------
            # EXIT
            # -------------------------------------------------

            if (
                key == ord("q")
                or key == 27
            ):

                print(
                    "Exit requested."
                )

                break

            # -------------------------------------------------
            # LEFT VALIDATE
            # -------------------------------------------------

            if key == ord("1"):

                validate_left = (
                    not validate_left
                )

                print(
                    "ODOO VALIDATE LEFT =",
                    validate_left
                )

            # -------------------------------------------------
            # RIGHT VALIDATE
            # -------------------------------------------------

            if key == ord("2"):

                validate_right = (
                    not validate_right
                )

                print(
                    "ODOO VALIDATE RIGHT =",
                    validate_right
                )

            # -------------------------------------------------
            # RESET VALIDATION
            # -------------------------------------------------

            if key == ord("r"):

                validate_left = False
                validate_right = False

                print(
                    "ODOO VALIDATE RESET"
                )

            # -------------------------------------------------
            # FORCE FULLSCREEN
            # -------------------------------------------------

            if key == ord("f"):

                cv2.setWindowProperty(
                    WINDOW_NAME,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN
                )

                print(
                    "Fullscreen re-enabled."
                )

            # -------------------------------------------------
            # VIDEO PAUSE
            # -------------------------------------------------

            if (
                key == ord(" ")
                and mode == "video"
            ):

                print(
                    "VIDEO PAUSED"
                )

                while True:

                    pause_key = (
                        cv2.waitKey(0)
                        & 0xFF
                    )

                    if pause_key == ord(" "):

                        print(
                            "VIDEO RESUME"
                        )

                        previous_time = (
                            time.perf_counter()
                        )

                        break

                    if (
                        pause_key == ord("q")
                        or pause_key == 27
                    ):

                        return

    # =====================================================
    # CTRL+C
    # =====================================================

    except KeyboardInterrupt:

        print()
        print(
            "Program dihentikan "
            "dari keyboard."
        )

    # =====================================================
    # CLEANUP
    # =====================================================

    finally:

        print(
            "Closing application..."
        )

        camera.release()

        cv2.destroyAllWindows()

        print(
            "Application closed."
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()