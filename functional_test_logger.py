import base64
import json
import queue
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import requests


class FunctionalTestLogger:
    """Non-blocking logger untuk functional test Barrier Gate AI.

    - Snapshot disimpan lokal.
    - Event dikirim ke Google Apps Script webhook bila URL tersedia.
    - Cooldown per zone + class mencegah spam satu objek setiap frame.
    """

    TRACKED_CLASSES = {
        "forklift_loaded",
        "forklift_empty",
        "troli_loaded",
        "troli_empty",
    }

    def __init__(
        self,
        snapshot_dir,
        webhook_url="",
        cooldown_seconds=10.0,
        camera_name="CAM",
        request_timeout=8.0,
        jpeg_quality=85,
        queue_size=30,
    ):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        self.webhook_url = (webhook_url or "").strip()
        self.cooldown_seconds = float(cooldown_seconds)
        self.camera_name = camera_name
        self.request_timeout = float(request_timeout)
        self.jpeg_quality = int(jpeg_quality)

        self.last_event = {}
        self.jobs = queue.Queue(maxsize=queue_size)
        self.running = True

        self.worker = threading.Thread(
            target=self._worker_loop,
            name="functional-test-uploader",
            daemon=True,
        )
        self.worker.start()

        if self.webhook_url:
            print("Functional test webhook: ENABLED")
        else:
            print("Functional test webhook: DISABLED (snapshot lokal tetap aktif)")

    def _normalize_name(self, name):
        return str(name).replace("empety", "empty").strip().lower()

    def _can_log(self, zone, class_name):
        key = f"{zone}:{class_name}"
        now = time.monotonic()
        previous = self.last_event.get(key, 0.0)

        if now - previous < self.cooldown_seconds:
            return False

        self.last_event[key] = now
        return True

    def process(self, frame, detections, source="AI"):
        """Cari detection yang perlu dicatat dan enqueue tanpa blocking inference."""
        if frame is None or not detections:
            return 0

        frame_h, frame_w = frame.shape[:2]
        center_line = frame_w / 2.0
        logged = 0

        for obj in detections:
            class_name = self._normalize_name(obj.get("name", ""))
            if class_name not in self.TRACKED_CLASSES:
                continue

            x1 = int(obj.get("x1", 0))
            y1 = int(obj.get("y1", 0))
            x2 = int(obj.get("x2", 0))
            y2 = int(obj.get("y2", 0))
            confidence = float(obj.get("confidence", 0.0))

            object_center_x = (x1 + x2) / 2.0
            zone = "IN" if object_center_x < center_line else "OUT"

            if not self._can_log(zone, class_name):
                continue

            event_id = uuid.uuid4().hex[:12]
            timestamp = datetime.now()
            timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            filename = (
                f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]}_"
                f"{self.camera_name}_{zone}_{class_name}_{event_id}.jpg"
            )
            image_path = self.snapshot_dir / filename

            snapshot = frame.copy()
            self._annotate(
                snapshot,
                zone=zone,
                class_name=class_name,
                confidence=confidence,
                box=(x1, y1, x2, y2),
                timestamp=timestamp_text,
            )

            cv2.imwrite(
                str(image_path),
                snapshot,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
            )

            event = {
                "event_id": event_id,
                "timestamp": timestamp_text,
                "camera": self.camera_name,
                "zone": zone,
                "detection": class_name,
                "load_status": "LOADED" if class_name.endswith("_loaded") else "EMPTY",
                "confidence": round(confidence, 4),
                "source": source,
                "snapshot_file": filename,
                "local_snapshot": str(image_path),
            }

            try:
                self.jobs.put_nowait((event, image_path))
                logged += 1
                print(
                    f"[FUNCTION TEST] queued | {zone} | {class_name} | "
                    f"conf={confidence:.2f} | {filename}"
                )
            except queue.Full:
                print("[FUNCTION TEST] upload queue penuh, event dilewati")

        return logged

    def _annotate(self, image, zone, class_name, confidence, box, timestamp):
        x1, y1, x2, y2 = box
        color = (0, 255, 0) if class_name.endswith("_loaded") else (0, 230, 255)

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
        label = f"{zone} | {class_name} | {confidence:.2f}"
        cv2.putText(
            image,
            label,
            (max(10, x1), max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            timestamp,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def _worker_loop(self):
        while self.running or not self.jobs.empty():
            try:
                event, image_path = self.jobs.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if self.webhook_url:
                    self._send_to_webhook(event, image_path)
                else:
                    print(
                        f"[FUNCTION TEST] local only | {event['detection']} | "
                        f"{image_path}"
                    )
            except Exception as exc:
                print(f"[FUNCTION TEST] upload gagal: {exc}")
            finally:
                self.jobs.task_done()

    def _send_to_webhook(self, event, image_path):
        image_bytes = image_path.read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        payload = dict(event)
        payload["image_base64"] = image_b64
        payload["image_mime_type"] = "image/jpeg"

        response = requests.post(
            self.webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        try:
            result = response.json()
        except ValueError:
            result = {"raw": response.text[:200]}

        print(
            f"[FUNCTION TEST] spreadsheet OK | {event['event_id']} | "
            f"{result.get('image_url', '')}"
        )

    def close(self, wait_seconds=3.0):
        self.running = False
        deadline = time.monotonic() + wait_seconds

        while not self.jobs.empty() and time.monotonic() < deadline:
            time.sleep(0.05)

        self.worker.join(timeout=1.0)
