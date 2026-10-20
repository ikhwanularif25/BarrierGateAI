"""Dual CCTV view shared by main.py and functional_test.py."""
import threading
import time

import cv2

from config import (
    CAMERAS, CAMERA_STALE_SECONDS, MODEL_PATH, CONFIDENCE, IMAGE_SIZE,
    WINDOW_NAME, FULLSCREEN, MIN_CONF_VEHICLE, MIN_CONF_OBJECT,
    LOAD_ASSOCIATION_EXPAND_X, LOAD_ASSOCIATION_EXPAND_TOP,
    LOAD_ASSOCIATION_EXPAND_BOTTOM, LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
    DISPLAY_TARGET_FPS, DETECTION_MAX_AGE_SECONDS,
)
from best4_adapter import adapt_best4_detections
from ui import DualCameraUI


class StreamReader:
    """Each stream opens/reconnects independently; capture owned by its worker."""
    def __init__(self, settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.latest = None
        self.connected = False
        self.sequence = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def _run(self):
        while not self.stop.is_set():
            cap = None
            try:
                cap = cv2.VideoCapture(self.settings['url'], cv2.CAP_FFMPEG, [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000,
                ])
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                while not self.stop.is_set() and cap.isOpened():
                    ok, frame = cap.read()
                    if not ok:
                        break
                    with self.lock:
                        self.sequence += 1
                        self.latest = (frame, time.perf_counter(), self.sequence)
                        self.connected = True
            except cv2.error:
                print(f"CCTV {self.settings['side']}: koneksi gagal, mencoba ulang")
            finally:
                with self.lock:
                    self.connected = False
                if cap is not None:
                    cap.release()
            self.stop.wait(1.0)

    def read(self):
        with self.lock:
            if not self.connected or self.latest is None:
                return None
            frame, timestamp, sequence = self.latest
            if time.perf_counter() - timestamp > CAMERA_STALE_SECONDS:
                return None
            return frame.copy(), timestamp, sequence

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)


def convert_result(result, detector):
    detections = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
        detections.append(dict(class_id=class_id, name=str(detector.model.names[class_id]),
                               confidence=float(box.conf[0]), x1=int(x1), y1=int(y1),
                               x2=int(x2), y2=int(y2)))
    return detections


def decision_detections(raw):
    return adapt_best4_detections(
        raw, min_vehicle_conf=MIN_CONF_VEHICLE, min_object_conf=MIN_CONF_OBJECT,
        expand_x=LOAD_ASSOCIATION_EXPAND_X, expand_top=LOAD_ASSOCIATION_EXPAND_TOP,
        expand_bottom=LOAD_ASSOCIATION_EXPAND_BOTTOM,
        min_object_overlap=LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
    )


class InferenceWorker:
    """One model, one worker; fair turns for both cameras, latest frames only."""
    def __init__(self, detector, readers, functional_test=False):
        self.detector = detector
        self.readers = readers
        self.functional_test = functional_test
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.results = [None] * len(readers)
        self.thread = threading.Thread(target=self._run, name="DualCameraAI", daemon=True)

    def start(self):
        self.thread.start()

    def snapshot(self):
        # Published frames/detections are immutable; renderer copies before drawing.
        with self.lock:
            return list(self.results)

    def _run(self):
        last_ids = [None] * len(self.readers)
        previous = [None] * len(self.readers)
        rates = [0.0] * len(self.readers)
        last_errors = [0.0] * len(self.readers)
        for_filter = None
        if self.functional_test:
            from functional_test import filter_detection_confidence
            for_filter = filter_detection_confidence
        while not self.stop.is_set():
            processed = False
            for index, reader in enumerate(self.readers):
                if self.stop.is_set():
                    break
                sample = reader.read()
                if sample is None:
                    with self.lock:
                        self.results[index] = None
                    last_ids[index] = None
                    previous[index] = None
                    rates[index] = 0.0
                    continue
                frame, timestamp, sequence = sample
                if sequence == last_ids[index]:
                    continue
                last_ids[index] = sequence
                processed = True
                try:
                    result = self.detector.detect(frame)
                    raw = convert_result(result, self.detector)
                    decisions = decision_detections(raw)
                    if for_filter:
                        decisions = for_filter(decisions)
                    now = time.perf_counter()
                    if previous[index] is not None:
                        rate = 1.0 / max(0.001, now - previous[index])
                        rates[index] = rate if not rates[index] else .8 * rates[index] + .2 * rate
                    previous[index] = now
                    item = dict(frame=frame, timestamp=timestamp, sequence=sequence,
                                detections=raw, decisions=decisions, ai_fps=rates[index])
                    with self.lock:
                        self.results[index] = item
                except Exception as exc:
                    # Failed inference is unknown, never an empty/clear ROI.
                    with self.lock:
                        self.results[index] = None
                    now = time.perf_counter()
                    if now - last_errors[index] >= 1:
                        print(f"CCTV {CAMERAS[index]['side']}: inferensi gagal ({type(exc).__name__})")
                        last_errors[index] = now
            if not processed:
                self.stop.wait(.005)

    def close(self):
        self.stop.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=5)


def build_views(readers, results, now):
    """Display current video and bound overlays to a recent successful AI result."""
    views = []
    for index, reader in enumerate(readers):
        view = dict(ip=CAMERAS[index]['ip'], online=False, frame=None,
                    detections=[], decisions=[], inference_ready=False, ai_fps=0.0)
        sample = reader.read()
        if sample is not None:
            frame, timestamp, sequence = sample
            view.update(online=True, frame=frame, timestamp=timestamp, sequence=sequence)
            result = results[index]
            if (result is not None
                    and 0 <= now - result['timestamp'] <= DETECTION_MAX_AGE_SECONDS
                    and result['frame'].shape == frame.shape):
                view.update(detections=result['detections'], decisions=result['decisions'],
                            inference_ready=True, ai_fps=result['ai_fps'])
        views.append(view)
    return views


class RightCameraEvents:
    """Retain existing OUT-zone integration for the original right camera."""
    def __init__(self, detector, ui):
        import functional_test as ft
        self.ft, self.ui = ft, ui
        self.camera_name = f"CAM{ft.CAMERA_NUMBER:03d}"
        names = detector.model.names
        if isinstance(names, dict):
            names = names.values()
        self.presence_supported = bool({ft.normalize_class_name(n) for n in names} & ft.PRESENCE_CLASSES)
        self.sender = None
        self.logger = ft.FunctionalTestLogger(
            snapshot_dir=ft.FUNCTION_TEST_SNAPSHOT_DIR,
            webhook_url=ft.FUNCTION_TEST_WEBHOOK_URL,
            cooldown_seconds=ft.FUNCTION_TEST_COOLDOWN, camera_name=self.camera_name,
        )
        if ft.NODE_RED_ENABLED:
            self.sender = ft.NodeRedSender(url=ft.NODE_RED_URL, timeout=ft.NODE_RED_TIMEOUT)
        self.last_sent = None

    def process(self, view, display):
        ft = self.ft
        if time.perf_counter() - view['timestamp'] > ft.MAX_PRESENCE_FRAME_AGE_SECONDS:
            return
        frame, raw = view['frame'], view['detections']
        if self.sender and self.presence_supported:
            self.sender.send_presence(camera=self.camera_name,
                                      has_vehicle=ft.get_vehicle_presence(self.ui, frame, raw))
        qualified = ft.get_ui2_qualified_detections(self.ui, frame, view['decisions'])
        now = time.monotonic()
        if self.sender and (self.last_sent is None or now - self.last_sent >= ft.NODE_RED_DETECTION_INTERVAL):
            sent = False
            for obj in qualified:
                payload = ft.build_node_red_payload(obj)
                if payload is not None and self.sender.send(payload):
                    sent = True
            if sent:
                self.last_sent = now
        self.logger.process(snapshot_frame=display, qualified_detections=qualified,
                            source="FUNCTIONAL_TEST_UI2", zone="OUT")

    def close(self):
        if self.sender:
            self.sender.close()
        self.logger.close()


def run_dual_camera(functional_test=False):
    from detector import Detector
    from main import get_screen_resolution
    width, height = get_screen_resolution()
    ui = DualCameraUI(width=width, height=height)
    detector = Detector(model_path=MODEL_PATH, confidence=CONFIDENCE, image_size=IMAGE_SIZE)
    readers = [StreamReader(settings) for settings in CAMERAS]
    views = [dict(ip=c['ip'], online=False, frame=None, detections=[], decisions=[]) for c in CAMERAS]
    worker = InferenceWorker(detector, readers, functional_test)
    last_event_sequence = None
    validated = [False, False]
    events = None
    fps, fps_frames, fps_since = 0.0, 0, time.perf_counter()
    try:
        if functional_test:
            events = RightCameraEvents(detector, ui)
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.imshow(WINDOW_NAME, ui.render_dual(views))
        cv2.waitKey(1)
        if FULLSCREEN:
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.resizeWindow(WINDOW_NAME, width, height)
        for reader in readers:
            reader.start()
        worker.start()
        while True:
            loop_start = time.perf_counter()
            results = worker.snapshot()
            now = time.perf_counter()
            views = build_views(readers, results, now)
            for index, view in enumerate(views):
                if not view['online'] or not view['inference_ready']:
                    validated[index] = False
            fps_frames += 1
            if now - fps_since >= 1.0:
                fps = fps_frames / (now - fps_since)
                fps_frames, fps_since = 0, now
            display = ui.render_dual(views, validated, fps)
            right = results[1]
            if (events and views[1]['online'] and views[1]['inference_ready']
                    and right['sequence'] != last_event_sequence):
                # Events use the exact inferred frame, never the newer display frame.
                events.process(right, display)
                last_event_sequence = right['sequence']
            cv2.imshow(WINDOW_NAME, display)
            remaining_ms = int((1.0 / DISPLAY_TARGET_FPS - (time.perf_counter() - loop_start)) * 1000)
            key = cv2.waitKey(max(1, remaining_ms)) & 0xFF
            if key in (ord('q'), 27) or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in (ord('1'), ord('2')):
                index = key - ord('1')
                if views[index]['online'] and views[index]['inference_ready']:
                    validated[index] = not validated[index]
            elif key == ord('r'):
                validated[:] = [False, False]
            elif key == ord('f'):
                cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()
        for reader in readers:
            if reader.thread.ident is not None:
                reader.close()
        if events:
            events.close()
        cv2.destroyAllWindows()
