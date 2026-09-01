import os
import time

import cv2

from config import (
    BASE_DIR,
    CAMERA_MODE,
    CAMERA_NUMBER,
    CONFIDENCE,
    IMAGE_SIZE,
    MODEL_PATH,
)
from detector import Detector
from functional_test_logger import FunctionalTestLogger
from main import open_camera


FUNCTION_TEST_WEBHOOK_URL = os.getenv("FUNCTION_TEST_WEBHOOK_URL", "")
FUNCTION_TEST_COOLDOWN = float(os.getenv("FUNCTION_TEST_COOLDOWN", "10"))
FUNCTION_TEST_SNAPSHOT_DIR = BASE_DIR / "functional_test_snapshots"


def convert_detections(result, detector):
    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = detector.model.names[class_id]

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


def draw_test_overlay(frame, detections, logged_count, inference_ms):
    output = frame.copy()
    h, w = output.shape[:2]

    cv2.line(
        output,
        (w // 2, 0),
        (w // 2, h),
        (255, 0, 255),
        2,
    )

    cv2.putText(
        output,
        "IN ZONE",
        (30, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 230, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        output,
        "OUT ZONE",
        (w // 2 + 30, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 230, 255),
        2,
        cv2.LINE_AA,
    )

    for obj in detections:
        name = str(obj["name"]).replace("empety", "empty")
        x1, y1, x2, y2 = obj["x1"], obj["y1"], obj["x2"], obj["y2"]
        conf = obj["confidence"]
        color = (0, 255, 0) if name.endswith("_loaded") else (0, 230, 255)

        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            output,
            f"{name} {conf:.2f}",
            (x1, max(25, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        output,
        f"FUNCTION TEST | YOLO {inference_ms:.0f} ms | logged {logged_count}",
        (30, h - 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    return output


def main():
    print("=" * 70)
    print("BARRIER GATE AI - FUNCTIONAL TEST")
    print("=" * 70)
    print("Mode       :", CAMERA_MODE)
    print("Camera     :", f"CAM{CAMERA_NUMBER:03d}")
    print("Model      :", MODEL_PATH)
    print("Image size :", IMAGE_SIZE)
    print("Confidence :", CONFIDENCE)
    print("Cooldown   :", FUNCTION_TEST_COOLDOWN, "seconds")

    detector = Detector(
        model_path=MODEL_PATH,
        confidence=CONFIDENCE,
        image_size=IMAGE_SIZE,
    )

    camera = open_camera()
    logger = FunctionalTestLogger(
        snapshot_dir=FUNCTION_TEST_SNAPSHOT_DIR,
        webhook_url=FUNCTION_TEST_WEBHOOK_URL,
        cooldown_seconds=FUNCTION_TEST_COOLDOWN,
        camera_name=f"CAM{CAMERA_NUMBER:03d}",
    )

    last_frame_id = -1
    total_logged = 0
    mode = CAMERA_MODE.strip().lower()

    cv2.namedWindow("Barrier Gate Functional Test", cv2.WINDOW_NORMAL)

    try:
        while True:
            if mode == "rtsp":
                ret, frame, _, frame_id = camera.read()
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
                        continue
                    break

            result = detector.detect(frame)
            detections = convert_detections(result, detector)

            inference_ms = 0.0
            if hasattr(result, "speed"):
                inference_ms = result.speed.get("inference", 0.0)

            new_logs = logger.process(
                frame=frame,
                detections=detections,
                source="FUNCTIONAL_TEST",
            )
            total_logged += new_logs

            display = draw_test_overlay(
                frame,
                detections,
                total_logged,
                inference_ms,
            )

            cv2.imshow("Barrier Gate Functional Test", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

    except KeyboardInterrupt:
        pass
    finally:
        logger.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
