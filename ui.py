import cv2
import numpy as np


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

        # =====================================================
        # COLORS (BGR)
        # =====================================================
        self.bg_black = (0, 0, 0)
        self.header_gray = (115, 115, 115)

        self.white = (245, 245, 245)
        self.black = (0, 0, 0)

        self.yellow = (0, 230, 255)
        self.green = (80, 190, 80)
        self.red = (40, 40, 255)
        self.gray = (170, 170, 170)

        self.pink = (180, 105, 255)

    # =========================================================
    # TEXT
    # =========================================================
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

    # =========================================================
    # HEADER
    # =========================================================
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

        # Title kiri
        self.put_text(
            canvas,
            "AI POWERED SMART BARRIER GATE",
            (145, 58),
            scale=1.35,
            color=self.yellow,
            thickness=3
        )

        # Status tengah atas
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

        # Info kanan atas
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

    # =========================================================
    # ROI POLYGON
    # =========================================================
    def get_roi_polygon(self, frame_w, frame_h):
        """
        Polygon pink / ungu seperti contoh Anda.
        """
        pts = np.array(
            [
                (int(frame_w * 0.32), int(frame_h * 0.40)),
                (int(frame_w * 0.58), int(frame_h * 0.16)),
                (int(frame_w * 0.90), int(frame_h * 0.58)),
                (int(frame_w * 0.57), int(frame_h * 1.03)),
            ],
            dtype=np.int32
        )
        return pts

    def draw_roi_polygon(self, frame, pts):
        cv2.polylines(
            frame,
            [pts],
            isClosed=True,
            color=self.pink,
            thickness=6
        )

    # =========================================================
    # CHECK POINT INSIDE ROI
    # =========================================================
    def is_detection_inside_roi(
        self,
        x1,
        y1,
        x2,
        y2,
        roi_pts
    ):
        """
        Penilaian diambil dari center point box.
        """
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        result = cv2.pointPolygonTest(
            roi_pts,
            (center_x, center_y),
            False
        )

        return result >= 0, center_x, center_y

    # =========================================================
    # GATE LOGIC
    # =========================================================
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

        # -----------------------------------------------------
        # LOADED
        # -----------------------------------------------------
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

        # -----------------------------------------------------
        # EMPTY
        # -----------------------------------------------------
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

    # =========================================================
    # GATE BAR
    # =========================================================
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

    # =========================================================
    # DRAW DETECTIONS
    # =========================================================
    def draw_detections(
        self,
        frame,
        detections,
        roi_pts
    ):
        """
        Return:
        - frame yang sudah digambar
        - list object yang valid di dalam ROI
        """

        roi_objects = []

        for obj in detections:

            x1 = int(obj["x1"])
            y1 = int(obj["y1"])
            x2 = int(obj["x2"])
            y2 = int(obj["y2"])

            name = obj["name"]
            conf = obj["confidence"]

            inside_roi, cx, cy = self.is_detection_inside_roi(
                x1, y1, x2, y2, roi_pts
            )

            # Hanya yang di dalam ROI yang dipakai untuk penilaian
            if inside_roi:
                roi_objects.append(obj)

                if "loaded" in name:
                    color = self.green
                else:
                    color = self.yellow

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2
                )

                label = f"{name} {conf:.2f}"

                self.put_text(
                    frame,
                    label,
                    (x1, max(00, y1 - 8)),
                    scale=0.50,
                    color=color,
                    thickness=2
                )

                # titik center
                cv2.circle(
                    frame,
                    (cx, cy),
                    5,
                    color,
                    -1
                )

            else:
                # Object di luar ROI diabaikan untuk gate
                # Kalau mau tetap ditampilkan, pakai warna abu-abu tipis
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (120, 120, 120),
                    1
                )

        return frame, roi_objects

    # =========================================================
    # RENDER
    # =========================================================
    def render(
        self,
        frame,
        detections,
        fps,
        inference_ms,
        validate_left=False,
        validate_right=False
    ):
        """
        validate_right dipakai sebagai validate gate utama.
        """

        canvas = np.zeros(
            (self.height, self.width, 3),
            dtype=np.uint8
        )
        canvas[:] = self.bg_black

        # Area kamera
        cam_y1 = self.top_height
        cam_y2 = self.height - self.bottom_height
        cam_h = cam_y2 - cam_y1
        cam_w = self.width

        display_frame = cv2.resize(
            frame,
            (cam_w, cam_h),
            interpolation=cv2.INTER_LINEAR
        )

        # Scale detections ke frame display
        original_h, original_w = frame.shape[:2]
        scale_x = cam_w / original_w
        scale_y = cam_h / original_h

        scaled_detections = []

        for obj in detections:
            scaled_detections.append(
                {
                    "name": obj["name"],
                    "confidence": obj["confidence"],
                    "x1": int(obj["x1"] * scale_x),
                    "y1": int(obj["y1"] * scale_y),
                    "x2": int(obj["x2"] * scale_x),
                    "y2": int(obj["y2"] * scale_y),
                }
            )

        # ROI polygon
        roi_pts = self.get_roi_polygon(cam_w, cam_h)

        # Draw detections and collect only inside ROI
        display_frame, roi_objects = self.draw_detections(
            display_frame,
            scaled_detections,
            roi_pts
        )

        # Draw ROI
        self.draw_roi_polygon(
            display_frame,
            roi_pts
        )

        # Gate logic berdasarkan object di ROI saja
        gate_logic = self.get_gate_logic(
            roi_objects,
            validated=validate_right
        )

        # Pasang frame ke canvas
        canvas[cam_y1:cam_y2, 0:self.width] = display_frame

        # Header
        self.draw_header(
            canvas,
            fps,
            inference_ms,
            gate_logic
        )

        # Bottom gate status
        self.draw_bottom_gate_status(
            canvas,
            gate_logic
        )

        return canvas