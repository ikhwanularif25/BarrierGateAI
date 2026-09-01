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

    Logger TIDAK menentukan ROI/gate rule sendiri.
    Caller wajib mengirim hanya detection yang sudah lolos rule UI2.

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

    def process(
        self,
        snapshot_frame,
        qualified_detections,
        source="FUNCTIONAL_TEST_UI2",
        zone="OUT",
    ):
        """Log hanya detection yang SUDAH lolos rule UI2.

        `snapshot_frame` adalah canvas UI2 final agar gambar yang dikirim
        identik dengan tampilan operator.
        """
        if snapshot_frame is None or not qualified_detections:
            return 0

        logged = 0

        for obj in qualified_detections:
            class_name = self._normalize_name(obj.get("name", ""))

            if class_name not in self.TRACKED_CLASSES:
                continue

            confidence = float(obj.get("confidence", 0.0))

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

            # Simpan canvas UI2 apa adanya. Tidak menggambar overlay baru.
            cv2.imwrite(
                str(image_path),
                snapshot_frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
            )

            event = {
                "event_id": event_id,
                "timestamp": timestamp_text,
                "camera": self.camera_name,
                "zone": zone,
                "detection": class_name,
                "load_status": (
                    "LOADED" if class_name.endswith("_loaded") else "EMPTY"
                ),
                "confidence": round(confidence, 4),
                "source": source,
                "rule": "CENTER_POINT_INSIDE_UI2_ROI",
                "snapshot_file": filename,
                "local_snapshot": str(image_path),
            }

            try:
                self.jobs.put_nowait((event, image_path))
                logged += 1
                print(
                    f"[FUNCTION TEST] qualified + queued | {zone} | "
                    f"{class_name} | conf={confidence:.2f} | {filename}"
                )
            except queue.Full:
                print("[FUNCTION TEST] upload queue penuh, event dilewati")

        return logged

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
