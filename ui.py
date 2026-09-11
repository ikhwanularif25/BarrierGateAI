import cv2
import numpy as np

from best4_adapter import adapt_best4_detections
from config import (
    MIN_CONF_VEHICLE,
    MIN_CONF_OBJECT,
    LOAD_ASSOCIATION_EXPAND_X,
    LOAD_ASSOCIATION_EXPAND_TOP,
    LOAD_ASSOCIATION_EXPAND_BOTTOM,
    LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
)


class BarrierGateUI:

    def __init__(
        self,
        width=1920,
        height=1080,
        top_height=90,
        bottom_height=60,
        max_distance=5.0
    ):
        self.width = width
        self.height = height
        self.top_height = top_height
        self.bottom_height = bottom_height
        self.max_distance = max_distance

        self.bg_black = (0, 0, 0)
        self.header_gray = (115, 115, 115)
        self.white = (245, 245, 245)
        self.black = (0, 0, 0)
        self.yellow = (0, 230, 255)
        self.green = (80, 190, 80)
        self.red = (40, 40, 255)
        self.gray = (170, 170, 170)
        self.pink = (180, 105, 255)

    def put_text(
        self,
        image,
        text,
        position,
        scale=0.7,
        color=(255, 255, 255),
        thickness=2
    ):
        cv2.putText(
            image,
            text,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA
        )

    def put_center_text(
        self,
        image,
        text,
        x1,
        y1,
        x2,
        y2,
        scale=1.0,
        color=(255, 255, 255),
        thickness=2
    ):
        text_size = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            thickness
        )[0]

        text_x = x1 + ((x2 - x1) - text_size[0]) // 2
        text_y = y1 + ((y2 - y1) + text_size[1]) // 2

        self.put_text(
            image,
            text,
            (text_x, text_y),
            scale=scale,
            color=color,
            thickness=thickness
        )

    def draw_header(
        self,
        canvas,
        fps,
        inference_ms,
        gate_logic
    ):
        cv2.rectangle(
            canvas,
            (0, 0),
            (self.width, self.top_height),
            self.header_gray,
            -1
        )

        self.put_text(
            canvas,
            "AI POWERED SMART BARRIER GATE",
            (145, 58),
            scale=1.35,
            color=self.yellow,
            thickness=3
        )

        status_x = int(self.width * 0.49)

        self.put_text(
            canvas,
            "OUT ZONE",
            (status_x, 28),
            scale=0.70,
            color=self.yellow,
            thickness=2
        )

        self.put_text(
            canvas,
            gate_logic["line1"],
            (status_x, 52),
            scale=0.65,
            color=gate_logic["line1_color"],
            thickness=2
        )

        self.put_text(
            canvas,
            gate_logic["line2"],
            (status_x, 76),
            scale=0.65,
            color=gate_logic["line2_color"],
            thickness=2
        )

        info_x = self.width - 190

        self.put_text(
            canvas,
            f"MAX DISTANCE {self.max_distance:.1f} M",
            (info_x, 24),
            scale=0.62,
            color=self.yellow,
            thickness=2
        )

        self.put_text(
            canvas,
            f"YOLO {inference_ms:.0f}MS",
            (info_x, 50),
            scale=0.62,
            color=self.yellow,
            thickness=2
        )

        self.put_text(
            canvas,
            f"FPS {fps:.1f}",
            (info_x, 76),
            scale=0.62,
            color=self.yellow,
            thickness=2
        )

    def get_roi_polygon(self, frame_w, frame_h):
        return np.array(
            [
                (int(frame_w * 0.33), int(frame_h * 0.50)),
                (int(frame_w * 0.63), int(frame_h * 0.24)),
                (int(frame_w * 0.90), int(frame_h * 0.58)),
                (int(frame_w * 0.57), int(frame_h * 1.03)),
            ],
            dtype=np.int32
        )

    def draw_roi_polygon(self, frame, pts):
        cv2.polylines(
            frame,
            [pts],
            isClosed=True,
            color=self.pink,
            thickness=6
        )

    def is_detection_inside_roi(
        self,
        x1,
        y1,
        x2,
        y2,
        roi_pts
    ):
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        result = cv2.pointPolygonTest(
            roi_pts,
            (center_x, center_y),
            False
        )

        return result >= 0, center_x, center_y

    def get_gate_logic(
        self,
        roi_objects,
        validated=False
    ):
        if not roi_objects:
            return {
                "line1": "-",
                "line2": "-",
                "line1_color": self.red,
                "line2_color": self.red,
                "gate_state": "standby"
            }

        loaded_name = None
        empty_name = None

        for obj in roi_objects:
            name = obj["name"]
            if name in ["forklift_loaded", "troli_loaded"]:
                loaded_name = name
                break

        for obj in roi_objects:
            name = obj["name"]
            if name in ["forklift_empty", "troli_empty"]:
                empty_name = name
                break

        if loaded_name is not None:
            if loaded_name == "forklift_loaded":
                line1 = "FORKLIFT TERDETEKSI (ADA MUATAN)"
            else:
                line1 = "TROLI TERDETEKSI (ADA MUATAN)"

            if validated:
                return {
                    "line1": line1,
                    "line2": "VALIDATE OK",
                    "line1_color": self.green,
                    "line2_color": self.green,
                    "gate_state": "open"
                }

            return {
                "line1": line1,
                "line2": "LAKUKAN VALIDATE UNTUK MEMBUKA PORTAL",
                "line1_color": self.green,
                "line2_color": self.red,
                "gate_state": "lock"
            }

        if empty_name is not None:
            if empty_name == "forklift_empty":
                line1 = "FORKLIFT TERDETEKSI (TIDAK ADA MUATAN)"
            else:
                line1 = "TROLI TERDETEKSI (TIDAK ADA MUATAN)"

            return {
                "line1": line1,
                "line2": "AKAN TERBUKA DALAM 5 DETIK",
                "line1_color": self.yellow,
                "line2_color": self.yellow,
                "gate_state": "countdown"
            }

        return {
            "line1": "-",
            "line2": "-",
            "line1_color": self.red,
            "line2_color": self.red,
            "gate_state": "standby"
        }

    def get_gate_bar_style(self, gate_state):
        if gate_state == "open":
            return self.green, "OPEN"

        if gate_state == "lock":
            return self.red, "LOCK"

        if gate_state == "countdown":
            return self.yellow, "TERBUKA DALAM 5 DETIK"

        return self.gray, "STANDBY"

    def draw_bottom_gate_status(self, canvas, gate_logic):
        bar_y1 = self.height - self.bottom_height
        bar_y2 = self.height

        color, text = self.get_gate_bar_style(
            gate_logic["gate_state"]
        )

        cv2.rectangle(
            canvas,
            (0, bar_y1),
            (self.width, bar_y2),
            color,
            -1
        )

        self.put_center_text(
            canvas,
            text,
            0,
            bar_y1,
            self.width,
            bar_y2,
            scale=1.0,
            color=self.black,
            thickness=2
        )

    def _raw_detection_color(self, name, inside_roi):
        """Raw model detections remain visible both inside and outside ROI."""
        if not inside_roi:
            return self.gray

        if name == "forklift":
            return self.green

        if name in {"trolley", "troli"}:
            return self.yellow

        if name == "object":
            return self.white

        return self.white

    def draw_raw_detections(
        self,
        frame,
        detections,
        roi_pts
    ):
        """
        Draw every raw best4 model detection.

        IMPORTANT:
        ROI only changes visual emphasis. Detections outside ROI are still
        displayed so the operator can see the complete model reading.
        """
        for obj in detections:
            x1 = int(obj["x1"])
            y1 = int(obj["y1"])
            x2 = int(obj["x2"])
            y2 = int(obj["y2"])

            name = str(obj.get("name", "")).strip().lower()
            conf = float(obj.get("confidence", 0.0))

            inside_roi, cx, cy = self.is_detection_inside_roi(
                x1,
                y1,
                x2,
                y2,
                roi_pts
            )

            color = self._raw_detection_color(name, inside_roi)
            thickness = 3 if inside_roi else 1

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                thickness
            )

            roi_flag = "ROI" if inside_roi else "OUT"
            label = f"{name} {conf:.2f} [{roi_flag}]"

            self.put_text(
                frame,
                label,
                (x1, max(18, y1 - 8)),
                scale=0.50,
                color=color,
                thickness=2 if inside_roi else 1
            )

            cv2.circle(
                frame,
                (cx, cy),
                5 if inside_roi else 3,
                color,
                -1
            )

        return frame

    def get_roi_objects(
        self,
        detections,
        roi_pts
    ):
        """Return only decision detections whose center point is inside ROI."""
        roi_objects = []

        for obj in detections:
            inside_roi, _, _ = self.is_detection_inside_roi(
                int(obj["x1"]),
                int(obj["y1"]),
                int(obj["x2"]),
                int(obj["y2"]),
                roi_pts
            )

            if inside_roi:
                roi_objects.append(obj)

        return roi_objects

    def _scale_detections(self, detections, scale_x, scale_y):
        scaled = []

        for obj in detections:
            item = dict(obj)
            item["x1"] = int(obj["x1"] * scale_x)
            item["y1"] = int(obj["y1"] * scale_y)
            item["x2"] = int(obj["x2"] * scale_x)
            item["y2"] = int(obj["y2"] * scale_y)
            scaled.append(item)

        return scaled

    def render(
        self,
        frame,
        detections,
        fps,
        inference_ms,
        validate_left=False,
        validate_right=False,
        decision_detections=None
    ):
        """
        `detections` is the raw best4 model output and is ALWAYS displayed.

        `decision_detections` is the legacy loaded/empty result used only for
        gate state. Only decision detections whose center point is inside the
        pink ROI can influence the gate.

        For main.py compatibility, when decision_detections is omitted the
        raw detections are adapted here automatically.
        """
        if decision_detections is None:
            decision_detections = adapt_best4_detections(
                detections,
                min_vehicle_conf=MIN_CONF_VEHICLE,
                min_object_conf=MIN_CONF_OBJECT,
                expand_x=LOAD_ASSOCIATION_EXPAND_X,
                expand_top=LOAD_ASSOCIATION_EXPAND_TOP,
                expand_bottom=LOAD_ASSOCIATION_EXPAND_BOTTOM,
                min_object_overlap=LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP,
            )

        canvas = np.zeros(
            (self.height, self.width, 3),
            dtype=np.uint8
        )
        canvas[:] = self.bg_black

        cam_y1 = self.top_height
        cam_y2 = self.height - self.bottom_height
        cam_h = cam_y2 - cam_y1
        cam_w = self.width

        display_frame = cv2.resize(
            frame,
            (cam_w, cam_h),
            interpolation=cv2.INTER_LINEAR
        )

        original_h, original_w = frame.shape[:2]
        scale_x = cam_w / original_w
        scale_y = cam_h / original_h

        scaled_raw = self._scale_detections(
            detections,
            scale_x,
            scale_y
        )

        scaled_decisions = self._scale_detections(
            decision_detections,
            scale_x,
            scale_y
        )

        roi_pts = self.get_roi_polygon(cam_w, cam_h)

        # Display every raw best4 reading, including detections outside ROI.
        display_frame = self.draw_raw_detections(
            display_frame,
            scaled_raw,
            roi_pts
        )

        self.draw_roi_polygon(
            display_frame,
            roi_pts
        )

        # Gate state is determined ONLY by legacy decisions inside ROI.
        roi_objects = self.get_roi_objects(
            scaled_decisions,
            roi_pts
        )

        gate_logic = self.get_gate_logic(
            roi_objects,
            validated=validate_right
        )

        canvas[cam_y1:cam_y2, 0:self.width] = display_frame

        self.draw_header(
            canvas,
            fps,
            inference_ms,
            gate_logic
        )

        self.draw_bottom_gate_status(
            canvas,
            gate_logic
        )

        return canvas
