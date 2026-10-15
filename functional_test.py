import os
import time
from datetime import datetime

import cv2
import numpy as np

from config import (
    BASE_DIR,
    CAMERA_MODE,
    CAMERA_NUMBER,
    CONFIDENCE,
    IMAGE_SIZE,
    MODEL_PATH,
    WINDOW_NAME,
    FULLSCREEN,
    TOP_BAR_HEIGHT,
    BOTTOM_PANEL_HEIGHT,
    MAX_DISTANCE,
    MIN_CONF_EMPTY,
    MIN_CONF_LOADED,
    NODE_RED_ENABLED,
    NODE_RED_URL,
    NODE_RED_TIMEOUT,
)
from detector import Detector
from functional_test_logger import FunctionalTestLogger
from main import get_screen_resolution, open_camera
from node_red_sender import NodeRedSender
from ui import BarrierGateUI


FUNCTION_TEST_WEBHOOK_URL = os.getenv(
    "FUNCTION_TEST_WEBHOOK_URL", ""
)
FUNCTION_TEST_COOLDOWN = float(
    os.getenv("FUNCTION_TEST_COOLDOWN", "10")
)
FUNCTION_TEST_SNAPSHOT_DIR = (
    BASE_DIR / "functional_test_snapshots"
)

# Interval pengiriman deteksi LOADED / EMPTY.
NODE_RED_DETECTION_INTERVAL = 1.0

# Frame RTSP yang terlalu lama tidak dipakai untuk
# menyatakan bahwa area kosong.
MAX_PRESENCE_FRAME_AGE_SECONDS = 2.0

TRACKED_CLASSES = {
    "forklift_loaded",
    "forklift_empty",
    "troli_loaded",
    "troli_empty",
}

PRESENCE_CLASSES = TRACKED_CLASSES | {
    "forklift",
    "trolley",
    "troli",
}


def normalize_class_name(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace("empety", "empty")
    )


def convert_detections(result, detector):
    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        class_name = normalize_class_name(
            detector.model.names[class_id]
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
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
            }
        )

    return detections


def filter_detection_confidence(detections):
    """
    Filter confidence tambahan untuk keputusan LOADED/EMPTY,
    tampilan, logger, dan payload deteksi Node-RED.
    """
    filtered = []

    for obj in detections:
        class_name = normalize_class_name(
            obj.get("name", "")
        )
        confidence = float(
            obj.get("confidence", 0.0)
        )

        if class_name not in TRACKED_CLASSES:
            continue

        if class_name.endswith("_loaded"):
            if confidence < MIN_CONF_LOADED:
                continue

        elif class_name.endswith("_empty"):
            if confidence < MIN_CONF_EMPTY:
                continue

        else:
            continue

        item = dict(obj)
        item["name"] = class_name
        filtered.append(item)

    return filtered


def get_ui2_qualified_detections(ui, frame, detections):
    """
    Menggunakan pemeriksaan ROI yang sama dengan UI2.
    """
    if frame is None or not detections:
        return []

    original_h, original_w = frame.shape[:2]

    cam_w = ui.width
    cam_h = (
        ui.height
        - ui.top_height
        - ui.bottom_height
    )

    scale_x = cam_w / original_w
    scale_y = cam_h / original_h

    roi_pts = ui.get_roi_polygon(cam_w, cam_h)
    qualified = []

    for obj in detections:
        sx1 = int(obj["x1"] * scale_x)
        sy1 = int(obj["y1"] * scale_y)
        sx2 = int(obj["x2"] * scale_x)
        sy2 = int(obj["y2"] * scale_y)

        inside_roi, _, _ = ui.is_detection_inside_roi(
            sx1,
            sy1,
            sx2,
            sy2,
            roi_pts,
        )

        if inside_roi:
            qualified.append(obj)

    return qualified


def get_vehicle_presence(ui, frame, raw_detections):
    """
    Pemeriksaan keberadaan kendaraan dilakukan sebelum
    filter MIN_CONF_EMPTY / MIN_CONF_LOADED.

    raw_detections tetap mengikuti threshold dasar
    CONFIDENCE yang digunakan oleh detector.
    """
    vehicles = [
        obj
        for obj in raw_detections
        if normalize_class_name(
            obj.get("name", "")
        ) in PRESENCE_CLASSES
    ]

    vehicles_in_roi = get_ui2_qualified_detections(
        ui,
        frame,
        vehicles,
    )

    return bool(vehicles_in_roi)


def build_node_red_payload(obj):
    class_name = normalize_class_name(
        obj.get("name", "")
    )
    confidence = float(
        obj.get("confidence", 0.0)
    )

    if class_name.startswith("forklift"):
        object_type = "forklift"
    elif class_name.startswith("troli"):
        object_type = "troli"
    else:
        return None

    if class_name.endswith("_loaded"):
        load_status = "loaded"
    elif class_name.endswith("_empty"):
        load_status = "empty"
    else:
        return None

    return {
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "camera": f"CAM{CAMERA_NUMBER:03d}",
        "zone": "OUT",
        "object_type": object_type,
        "load_status": load_status,
        "class_name": class_name,
        "confidence": round(confidence, 4),
        "inside_roi": True,
        "has_vehicle": True,
        "source": "BarrierGateAI",
    }


def main():
    camera_name = f"CAM{CAMERA_NUMBER:03d}"

    print("=" * 70)
    print("BARRIER GATE AI - UI2 FUNCTIONAL TEST LOGGER")
    print("=" * 70)
    print("Mode       :", CAMERA_MODE)
    print("Camera     :", camera_name)
    print("Model      :", MODEL_PATH)
    print("Image size :", IMAGE_SIZE)
    print("Confidence :", CONFIDENCE)
    print("Min empty  :", MIN_CONF_EMPTY)
    print("Min loaded :", MIN_CONF_LOADED)
    print("Cooldown   :", FUNCTION_TEST_COOLDOWN, "seconds")
    print("Presence   : laporan maksimal setiap 1 detik")
    print("UI         : UI2")

    mode = CAMERA_MODE.strip().lower()
    screen_width, screen_height = get_screen_resolution()

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE,
    )

    print("MODEL CLASSES:", detector.model.names)

    model_names = detector.model.names

    if isinstance(model_names, dict):
        model_names = model_names.values()

    known_names = {
        normalize_class_name(name)
        for name in model_names
    }

    presence_supported = bool(
        known_names & PRESENCE_CLASSES
    )

    if not presence_supported:
        print(
            "[PRESENCE] DINONAKTIFKAN: "
            "model tidak memiliki kelas kendaraan yang dikenal."
        )

    scale_y = screen_height / 1080.0
    top_height = max(
        80,
        int(TOP_BAR_HEIGHT * scale_y),
    )
    bottom_height = max(
        55,
        int(BOTTOM_PANEL_HEIGHT * scale_y),
    )

    ui = BarrierGateUI(
        width=screen_width,
        height=screen_height,
        top_height=top_height,
        bottom_height=bottom_height,
        max_distance=MAX_DISTANCE,
    )

    camera = open_camera()

    logger = FunctionalTestLogger(
        snapshot_dir=FUNCTION_TEST_SNAPSHOT_DIR,
        webhook_url=FUNCTION_TEST_WEBHOOK_URL,
        cooldown_seconds=FUNCTION_TEST_COOLDOWN,
        camera_name=camera_name,
    )

    node_red_sender = None

    if NODE_RED_ENABLED:
        node_red_sender = NodeRedSender(
            url=NODE_RED_URL,
            timeout=NODE_RED_TIMEOUT,
        )
        print("Node-RED   : ENABLED ->", NODE_RED_URL)
    else:
        print("Node-RED   : DISABLED")

    validate_left = False
    validate_right = False

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL,
    )

    startup_frame = np.zeros(
        (screen_height, screen_width, 3),
        dtype=np.uint8,
    )

    cv2.putText(
        startup_frame,
        "AI POWERED SMART BARRIER GATE",
        (
            max(40, screen_width // 4),
            screen_height // 2,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 230, 255),
        3,
        cv2.LINE_AA,
    )

    cv2.imshow(WINDOW_NAME, startup_frame)
    cv2.waitKey(200)

    if FULLSCREEN:
        cv2.setWindowProperty(
            WINDOW_NAME,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN,
        )
        cv2.waitKey(100)
    else:
        cv2.resizeWindow(
            WINDOW_NAME,
            screen_width,
            screen_height,
        )

    previous_time = time.perf_counter()
    fps_smooth = 0.0
    last_frame_id = -1
    total_logged = 0
    last_detection_sent = None

    try:
        while True:
            # =============================================
            # BACA FRAME
            # =============================================
            if mode == "rtsp":
                (
                    ret,
                    frame,
                    frame_timestamp,
                    frame_id,
                ) = camera.read()

                if not ret or frame is None:
                    # Kamera gagal: jangan kirim ROI kosong.
                    time.sleep(0.005)
                    continue

                if frame_id == last_frame_id:
                    time.sleep(0.001)
                    continue

                last_frame_id = frame_id

            else:
                ret, frame = camera.read()

                if not ret or frame is None:
                    if mode == "video":
                        camera.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            0,
                        )
                        previous_time = time.perf_counter()
                        continue

                    break

                frame_timestamp = time.perf_counter()

            # =============================================
            # INFERENSI
            # Jika inferensi gagal, program keluar melalui
            # finally; tidak mengirim has_vehicle=False.
            # =============================================
            result = detector.detect(frame)

            raw_detections = convert_detections(
                result,
                detector,
            )

            for obj in raw_detections:
                print(
                    "[RAW DET]",
                    obj["name"],
                    f'{float(obj["confidence"]):.2f}',
                )

            # =============================================
            # PRESENCE: SEBELUM FILTER LOADED / EMPTY
            # =============================================
            frame_age = (
                time.perf_counter() - frame_timestamp
            )

            presence_frame_fresh = (
                0 <= frame_age
                <= MAX_PRESENCE_FRAME_AGE_SECONDS
            )

            if (
                node_red_sender is not None
                and presence_supported
                and presence_frame_fresh
            ):
                has_vehicle_in_roi = get_vehicle_presence(
                    ui,
                    frame,
                    raw_detections,
                )

                # Dipanggil pada setiap frame berhasil.
                # Sender membatasi pengiriman ke 1x/detik.
                node_red_sender.send_presence(
                    camera=camera_name,
                    has_vehicle=has_vehicle_in_roi,
                )

            # =============================================
            # FILTER KEPUTUSAN LOADED / EMPTY
            # =============================================
            detections = filter_detection_confidence(
                raw_detections
            )
            detection_count = len(detections)

            inference_ms = 0.0

            if hasattr(result, "speed") and result.speed:
                inference_ms = result.speed.get(
                    "inference",
                    0.0,
                )

            # =============================================
            # FPS
            # =============================================
            current_time = time.perf_counter()
            delta = current_time - previous_time
            previous_time = current_time

            fps = 1.0 / delta if delta > 0 else 0.0

            if fps_smooth == 0:
                fps_smooth = fps
            else:
                fps_smooth = (
                    fps_smooth * 0.90
                    + fps * 0.10
                )

            # =============================================
            # RENDER UI2
            # =============================================
            display = ui.render(
                frame=frame,
                detections=detections,
                fps=fps_smooth,
                inference_ms=inference_ms,
                validate_left=validate_left,
                validate_right=validate_right,
            )

            qualified = get_ui2_qualified_detections(
                ui,
                frame,
                detections,
            )

            # =============================================
            # KIRIM DETEKSI LOADED / EMPTY
            # =============================================
            now = time.monotonic()

            detection_due = (
                last_detection_sent is None
                or now - last_detection_sent
                >= NODE_RED_DETECTION_INTERVAL
            )

            if node_red_sender is not None and detection_due:
                sent_any = False

                for obj in qualified:
                    payload = build_node_red_payload(obj)

                    if payload is not None:
                        if node_red_sender.send(payload):
                            sent_any = True

                if sent_any:
                    last_detection_sent = now

            # =============================================
            # SPREADSHEET / SNAPSHOT LOGGER
            # =============================================
            new_logs = logger.process(
                snapshot_frame=display,
                qualified_detections=qualified,
                source="FUNCTIONAL_TEST_UI2",
                zone="OUT",
            )
            total_logged += new_logs

            # =============================================
            # LATENCY
            # =============================================
            if mode == "rtsp":
                total_latency_ms = (
                    time.perf_counter() - frame_timestamp
                ) * 1000

                latency_text = (
                    f"LATENCY {total_latency_ms:.0f} MS"
                )
                latency_color = (80, 255, 80)

                if total_latency_ms > 300:
                    latency_color = (0, 255, 255)

                if total_latency_ms > 1000:
                    latency_color = (0, 0, 255)

                text_size = cv2.getTextSize(
                    latency_text,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    2,
                )[0]

                latency_x = (
                    screen_width - text_size[0] - 300
                )
                latency_y = max(
                    35,
                    int(top_height * 0.92),
                )

                cv2.putText(
                    display,
                    latency_text,
                    (latency_x, latency_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    latency_color,
                    2,
                    cv2.LINE_AA,
                )

            cv2.putText(
                display,
                f"DET {detection_count}",
                (max(15, screen_width - 470), 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(WINDOW_NAME, display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

            if key == ord("1"):
                validate_left = not validate_left
                print(
                    "ODOO VALIDATE LEFT =",
                    validate_left,
                )

            if key == ord("2"):
                validate_right = not validate_right
                print(
                    "ODOO VALIDATE RIGHT =",
                    validate_right,
                )

            if key == ord("r"):
                validate_left = False
                validate_right = False
                print("ODOO VALIDATE RESET")

            if key == ord("f"):
                cv2.setWindowProperty(
                    WINDOW_NAME,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN,
                )

    except KeyboardInterrupt:
        pass

    finally:
        print(
            "Functional test logged events:",
            total_logged,
        )

        if node_red_sender is not None:
            node_red_sender.close()

        logger.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()