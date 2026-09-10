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
    MIN_CONF_VEHICLE,
    MIN_CONF_OBJECT,
    LOAD_ASSOCIATION_EXPAND_X,
    LOAD_ASSOCIATION_EXPAND_TOP,
    LOAD_ASSOCIATION_EXPAND_BOTTOM,
    LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
    NODE_RED_ENABLED,
    NODE_RED_URL,
    NODE_RED_TIMEOUT,
)
from best4_adapter import adapt_best4_detections
from detector import Detector
from functional_test_logger import FunctionalTestLogger
from main import get_screen_resolution, open_camera
from node_red_sender import NodeRedSender
from ui import BarrierGateUI


FUNCTION_TEST_WEBHOOK_URL = os.getenv("FUNCTION_TEST_WEBHOOK_URL", "")
FUNCTION_TEST_COOLDOWN = float(os.getenv("FUNCTION_TEST_COOLDOWN", "10"))
FUNCTION_TEST_SNAPSHOT_DIR = BASE_DIR / "functional_test_snapshots"

TRACKED_CLASSES = {
    "forklift_loaded",
    "forklift_empty",
    "troli_loaded",
    "troli_empty",
}


def convert_detections(result, detector):
    """Convert YOLO best4 output to simple dictionaries."""
    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = str(detector.model.names[class_id]).strip().lower()

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


def derive_legacy_detections(raw_detections):
    """forklift/trolley/object -> legacy loaded/empty contract."""
    return adapt_best4_detections(
        raw_detections,
        min_vehicle_conf=MIN_CONF_VEHICLE,
        min_object_conf=MIN_CONF_OBJECT,
        expand_x=LOAD_ASSOCIATION_EXPAND_X,
        expand_top=LOAD_ASSOCIATION_EXPAND_TOP,
        expand_bottom=LOAD_ASSOCIATION_EXPAND_BOTTOM,
        min_object_overlap=LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
    )


def filter_decision_confidence(detections):
    """Confidence filter for derived loaded/empty decisions only."""
    filtered = []

    for obj in detections:
        class_name = str(obj.get("name", "")).strip().lower()
        confidence = float(obj.get("confidence", 0.0))

        if class_name not in TRACKED_CLASSES:
            continue

        if class_name.endswith("_loaded") and confidence < MIN_CONF_LOADED:
            continue

        if class_name.endswith("_empty") and confidence < MIN_CONF_EMPTY:
            continue

        item = dict(obj)
        item["name"] = class_name
        filtered.append(item)

    return filtered


def get_roi_qualified_detections(ui, frame, detections):
    """
    Return only detections whose bounding-box center point is inside pink ROI.
    This function is the single outbound filter for Node-RED and logger.
    """
    if frame is None or not detections:
        return []

    original_h, original_w = frame.shape[:2]
    cam_w = ui.width
    cam_h = ui.height - ui.top_height - ui.bottom_height

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


def build_node_red_payload(obj):
    """Keep existing Node-RED payload contract."""
    class_name = str(obj.get("name", "")).strip().lower()
    confidence = float(obj.get("confidence", 0.0))

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
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "camera": f"CAM{CAMERA_NUMBER:03d}",
        "zone": "OUT",
        "object_type": object_type,
        "load_status": load_status,
        "class_name": class_name,
        "confidence": round(confidence, 4),
        "inside_roi": True,
        "source": "BarrierGateAI",
    }


def print_detection_debug(raw_detections, decisions, qualified):
    if raw_detections:
        raw_text = ", ".join(
            f'{obj["name"]} {float(obj["confidence"]):.2f}'
            for obj in raw_detections
        )
        print("[MODEL]", raw_text)
    else:
        print("[MODEL] no detection")

    if decisions:
        decision_text = ", ".join(
            f'{obj["name"]} {float(obj["confidence"]):.2f}'
            for obj in decisions
        )
        print("[DECISION]", decision_text)

    if qualified:
        qualified_text = ", ".join(
            f'{obj["name"]} {float(obj["confidence"]):.2f}'
            for obj in qualified
        )
        print("[ROI SEND]", qualified_text)


def main():
    print("=" * 70)
    print("BARRIER GATE AI - BEST4 ROI FUNCTIONAL TEST")
    print("=" * 70)
    print("Mode       :", CAMERA_MODE)
    print("Camera     :", f"CAM{CAMERA_NUMBER:03d}")
    print("Model      :", MODEL_PATH)
    print("Image size :", IMAGE_SIZE)
    print("Confidence :", CONFIDENCE)
    print("Vehicle min:", MIN_CONF_VEHICLE)
    print("Object min :", MIN_CONF_OBJECT)
    print("Empty min  :", MIN_CONF_EMPTY)
    print("Loaded min :", MIN_CONF_LOADED)
    print("Display    : ALL raw model detections")
    print("Send rule  : ONLY derived decision center-point inside pink ROI")

    mode = CAMERA_MODE.strip().lower()
    screen_width, screen_height = get_screen_resolution()

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE,
    )

    print("MODEL CLASSES:", detector.model.names)

    scale_y = screen_height / 1080.0
    top_height = max(80, int(TOP_BAR_HEIGHT * scale_y))
    bottom_height = max(55, int(BOTTOM_PANEL_HEIGHT * scale_y))

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
        camera_name=f"CAM{CAMERA_NUMBER:03d}",
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

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    startup_frame = np.zeros(
        (screen_height, screen_width, 3),
        dtype=np.uint8,
    )

    cv2.putText(
        startup_frame,
        "AI POWERED SMART BARRIER GATE",
        (max(40, screen_width // 4), screen_height // 2),
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
        cv2.resizeWindow(WINDOW_NAME, screen_width, screen_height)

    previous_time = time.perf_counter()
    fps_smooth = 0.0
    last_frame_id = -1
    last_debug_time = 0.0
    total_logged = 0

    try:
        while True:
            if mode == "rtsp":
                ret, frame, frame_timestamp, frame_id = camera.read()

                if not ret:
                    time.sleep(0.005)
                    continue

                if frame_id == last_frame_id:
                    time.sleep(0.001)
                    continue

                last_frame_id = frame_id
            else:
                ret, frame = camera.read()

                if not ret:
                    if mode == "video":
                        camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        previous_time = time.perf_counter()
                        continue
                    break

                frame_timestamp = time.perf_counter()

            # 1. RAW MODEL READING - always preserved for display.
            result = detector.detect(frame)
            raw_detections = convert_detections(result, detector)

            # 2. Derive loaded/empty from forklift/trolley + object relation.
            derived_detections = derive_legacy_detections(raw_detections)
            decisions = filter_decision_confidence(derived_detections)

            # 3. Outbound data must pass ROI center-point rule.
            qualified = get_roi_qualified_detections(
                ui,
                frame,
                decisions,
            )

            debug_now = time.perf_counter()
            if debug_now - last_debug_time >= 0.5:
                print_detection_debug(raw_detections, decisions, qualified)
                last_debug_time = debug_now

            inference_ms = 0.0
            if hasattr(result, "speed"):
                inference_ms = result.speed.get("inference", 0.0)

            current_time = time.perf_counter()
            delta = current_time - previous_time
            previous_time = current_time
            fps = (1.0 / delta) if delta > 0 else 0.0

            if fps_smooth == 0:
                fps_smooth = fps
            else:
                fps_smooth = (fps_smooth * 0.90) + (fps * 0.10)

            # 4. UI displays ALL raw best4 detections.
            #    Gate status uses derived decisions, and UI applies ROI again.
            display = ui.render(
                frame=frame,
                detections=raw_detections,
                decision_detections=decisions,
                fps=fps_smooth,
                inference_ms=inference_ms,
                validate_left=validate_left,
                validate_right=validate_right,
            )

            # 5. ONLY ROI-qualified decisions are sent to Node-RED.
            if node_red_sender:
                for obj in qualified:
                    payload = build_node_red_payload(obj)
                    if payload:
                        node_red_sender.send(payload)

            # 6. ONLY ROI-qualified decisions are logged/sent to spreadsheet.
            new_logs = logger.process(
                snapshot_frame=display,
                qualified_detections=qualified,
                source="FUNCTIONAL_TEST_UI2_BEST4",
                zone="OUT",
            )
            total_logged += new_logs

            if mode == "rtsp":
                total_latency_ms = (
                    time.perf_counter() - frame_timestamp
                ) * 1000

                latency_text = f"LATENCY {total_latency_ms:.0f} MS"
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

                latency_x = screen_width - text_size[0] - 300
                latency_y = max(35, int(top_height * 0.92))

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
                f"MODEL {len(raw_detections)} | ROI SEND {len(qualified)}",
                (max(15, screen_width - 620), 35),
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
                print("ODOO VALIDATE LEFT =", validate_left)

            if key == ord("2"):
                validate_right = not validate_right
                print("ODOO VALIDATE RIGHT =", validate_right)

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
        print("Functional test logged events:", total_logged)

        if node_red_sender:
            node_red_sender.close()

        logger.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
