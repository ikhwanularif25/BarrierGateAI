import cv2
import numpy as np


class BarrierGateUI:

    def __init__(
        self,
        width=1648,
        height=928,
        top_height=70,
        bottom_height=190,
        max_distance=5.0
    ):

        self.width = width
        self.height = height

        self.top_height = top_height
        self.bottom_height = bottom_height

        self.max_distance = max_distance

        # =====================================================
        # COLORS - BGR
        # =====================================================

        self.bg_color = (34, 34, 34)

        self.white = (245, 245, 245)
        self.gray = (110, 110, 110)
        self.light_gray = (200, 200, 200)

        self.red = (0, 0, 255)
        self.green = (80, 255, 80)
        self.yellow = (0, 255, 255)

        self.orange = (0, 165, 255)

        self.black_overlay = (20, 20, 20)

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

    # =========================================================
    # HEADER
    # =========================================================

    def draw_header(
        self,
        canvas,
        fps,
        inference_ms
    ):

        cv2.rectangle(
            canvas,
            (0, 0),
            (self.width, self.top_height),
            self.bg_color,
            -1
        )

        # -----------------------------------------------------
        # APP NAME
        # -----------------------------------------------------

        self.put_text(
            canvas,
            "Smart Barrier Gate AI v1.0.1",
            (25, 46),
            scale=1.0,
            color=self.white,
            thickness=2
        )

        # -----------------------------------------------------
        # MAX DISTANCE
        # -----------------------------------------------------

        distance_text = (
            f"MAX DISTANCE: {self.max_distance:.1f} M"
        )

        text_size = cv2.getTextSize(
            distance_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            2
        )[0]

        center_x = (
            self.width // 2
            - text_size[0] // 2
        )

        self.put_text(
            canvas,
            distance_text,
            (center_x, 46),
            scale=0.55,
            color=self.yellow,
            thickness=2
        )

        # -----------------------------------------------------
        # YOLO SPEED
        # -----------------------------------------------------

        yolo_text = f"YOLO {inference_ms:.0f} ms"

        self.put_text(
            canvas,
            yolo_text,
            (self.width - 315, 46),
            scale=0.55,
            color=self.white,
            thickness=2
        )

        # -----------------------------------------------------
        # FPS
        # -----------------------------------------------------

        fps_text = f"FPS {fps:.1f}"

        self.put_text(
            canvas,
            fps_text,
            (self.width - 130, 46),
            scale=0.55,
            color=self.green,
            thickness=2
        )

    # =========================================================
    # ZONE HEADER
    # =========================================================

    def draw_zone_header(
        self,
        image,
        zone_name,
        status_line1,
        status_line2,
        status_color
    ):

        overlay = image.copy()

        cv2.rectangle(
            overlay,
            (0, 0),
            (image.shape[1], 115),
            self.black_overlay,
            -1
        )

        cv2.addWeighted(
            overlay,
            0.78,
            image,
            0.22,
            0,
            image
        )

        self.put_text(
            image,
            zone_name,
            (40, 45),
            scale=0.8,
            color=self.white,
            thickness=2
        )

        self.put_text(
            image,
            status_line1,
            (40, 78),
            scale=0.48,
            color=status_color,
            thickness=2
        )

        self.put_text(
            image,
            status_line2,
            (40, 104),
            scale=0.46,
            color=status_color,
            thickness=2
        )

    # =========================================================
    # VALIDATE PANEL
    # =========================================================

    def draw_validate_panel(
        self,
        canvas,
        x1,
        y1,
        x2,
        y2,
        title,
        enabled=False
    ):

        if enabled:

            background = (55, 95, 55)
            border = self.green

            status_text = "VALIDATE READY"
            status_color = self.green

        else:

            background = (105, 105, 105)
            border = self.light_gray

            status_text = "VALIDATE LOCKED"
            status_color = self.light_gray

        cv2.rectangle(
            canvas,
            (x1, y1),
            (x2, y2),
            background,
            -1
        )

        cv2.rectangle(
            canvas,
            (x1, y1),
            (x2, y2),
            border,
            4
        )

        # -----------------------------------------------------
        # TITLE
        # -----------------------------------------------------

        title_size = cv2.getTextSize(
            title,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            2
        )[0]

        title_x = (
            x1
            + ((x2 - x1) // 2)
            - (title_size[0] // 2)
        )

        self.put_text(
            canvas,
            title,
            (title_x, y1 + 65),
            scale=0.75,
            color=self.white,
            thickness=2
        )

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        status_size = cv2.getTextSize(
            status_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            2
        )[0]

        status_x = (
            x1
            + ((x2 - x1) // 2)
            - (status_size[0] // 2)
        )

        self.put_text(
            canvas,
            status_text,
            (status_x, y1 + 140),
            scale=0.45,
            color=status_color,
            thickness=2
        )

    # =========================================================
    # STATUS LOGIC
    # =========================================================

    def get_zone_status(
        self,
        objects
    ):

        if not objects:

            return (
                "OBJECT TIDAK ADA",
                "VALIDATE TERKUNCI",
                self.red,
                False
            )

        # -----------------------------------------------------
        # PRIORITY LOADED
        # -----------------------------------------------------

        for obj in objects:

            name = obj["name"]

            if name == "forklift_loaded":

                return (
                    "FORKLIFT BAWA BARANG",
                    "VALIDATE READY",
                    self.yellow,
                    True
                )

            if name == "troli_loaded":

                return (
                    "TROLI BAWA BARANG",
                    "VALIDATE READY",
                    self.yellow,
                    True
                )

        # -----------------------------------------------------
        # EMPTY
        # -----------------------------------------------------

        for obj in objects:

            name = obj["name"]

            if name == "forklift_empty":

                return (
                    "FORKLIFT KOSONG",
                    "AUTO GATE MODE",
                    self.green,
                    False
                )

            if name == "troli_empty":

                return (
                    "TROLI KOSONG",
                    "AUTO GATE MODE",
                    self.green,
                    False
                )

        return (
            "OBJECT TIDAK ADA",
            "VALIDATE TERKUNCI",
            self.red,
            False
        )

    # =========================================================
    # RENDER
    # =========================================================

    def render(
        self,
        frame,
        detections,
        fps,
        inference_ms
    ):

        canvas = np.zeros(
            (
                self.height,
                self.width,
                3
            ),
            dtype=np.uint8
        )

        canvas[:] = self.bg_color

        # =====================================================
        # HEADER
        # =====================================================

        self.draw_header(
            canvas,
            fps,
            inference_ms
        )

        # =====================================================
        # CAMERA AREA
        # =====================================================

        camera_y1 = self.top_height

        camera_y2 = (
            self.height
            - self.bottom_height
            - 15
        )

        camera_height = (
            camera_y2
            - camera_y1
        )

        half_width = self.width // 2

        # Resize CCTV
        camera_frame = cv2.resize(
            frame,
            (
                self.width,
                camera_height
            )
        )

        # Left/right image
        left_frame = camera_frame[
            :,
            0:half_width
        ].copy()

        right_frame = camera_frame[
            :,
            half_width:self.width
        ].copy()

        left_objects = []
        right_objects = []

        # =====================================================
        # DETECTIONS
        # =====================================================

        original_h, original_w = frame.shape[:2]

        scale_x = (
            self.width / original_w
        )

        scale_y = (
            camera_height / original_h
        )

        for obj in detections:

            x1 = int(
                obj["x1"] * scale_x
            )

            y1 = int(
                obj["y1"] * scale_y
            )

            x2 = int(
                obj["x2"] * scale_x
            )

            y2 = int(
                obj["y2"] * scale_y
            )

            center_x = (
                x1 + x2
            ) // 2

            name = obj["name"]
            confidence = obj["confidence"]

            # -------------------------------------------------
            # LEFT
            # -------------------------------------------------

            if center_x < half_width:

                left_objects.append(
                    obj
                )

                color = self.green

                if "loaded" in name:
                    color = self.yellow

                cv2.rectangle(
                    left_frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    3
                )

                label = (
                    f"{name} "
                    f"{confidence:.2f}"
                )

                self.put_text(
                    left_frame,
                    label,
                    (
                        x1,
                        max(
                            25,
                            y1 - 10
                        )
                    ),
                    scale=0.48,
                    color=color,
                    thickness=2
                )

            # -------------------------------------------------
            # RIGHT
            # -------------------------------------------------

            else:

                right_objects.append(
                    obj
                )

                local_x1 = (
                    x1
                    - half_width
                )

                local_x2 = (
                    x2
                    - half_width
                )

                color = self.green

                if "loaded" in name:
                    color = self.yellow

                cv2.rectangle(
                    right_frame,
                    (
                        local_x1,
                        y1
                    ),
                    (
                        local_x2,
                        y2
                    ),
                    color,
                    3
                )

                label = (
                    f"{name} "
                    f"{confidence:.2f}"
                )

                self.put_text(
                    right_frame,
                    label,
                    (
                        local_x1,
                        max(
                            25,
                            y1 - 10
                        )
                    ),
                    scale=0.48,
                    color=color,
                    thickness=2
                )

        # =====================================================
        # STATUS
        # =====================================================

        (
            left_status_1,
            left_status_2,
            left_color,
            left_validate
        ) = self.get_zone_status(
            left_objects
        )

        (
            right_status_1,
            right_status_2,
            right_color,
            right_validate
        ) = self.get_zone_status(
            right_objects
        )

        # =====================================================
        # ZONE HEADERS
        # =====================================================

        self.draw_zone_header(
            left_frame,
            "ZONA KIRI",
            left_status_1,
            left_status_2,
            left_color
        )

        self.draw_zone_header(
            right_frame,
            "ZONA KANAN",
            right_status_1,
            right_status_2,
            right_color
        )

        # =====================================================
        # PLACE CAMERA
        # =====================================================

        canvas[
            camera_y1:camera_y2,
            0:half_width
        ] = left_frame

        canvas[
            camera_y1:camera_y2,
            half_width:self.width
        ] = right_frame

        # =====================================================
        # RED BORDER
        # =====================================================

        cv2.rectangle(
            canvas,
            (
                5,
                camera_y1 + 4
            ),
            (
                half_width - 5,
                camera_y2
            ),
            self.red,
            6
        )

        cv2.rectangle(
            canvas,
            (
                half_width + 5,
                camera_y1 + 4
            ),
            (
                self.width - 5,
                camera_y2
            ),
            self.red,
            6
        )

        # Center divider
        cv2.line(
            canvas,
            (
                half_width,
                camera_y1
            ),
            (
                half_width,
                camera_y2
            ),
            self.yellow,
            4
        )

        # =====================================================
        # VALIDATE PANEL
        # =====================================================

        panel_y1 = (
            camera_y2 + 18
        )

        panel_y2 = (
            self.height - 18
        )

        margin = 25

        self.draw_validate_panel(
            canvas,
            margin,
            panel_y1,
            half_width - 15,
            panel_y2,
            "VALIDATE KIRI",
            left_validate
        )

        self.draw_validate_panel(
            canvas,
            half_width + 15,
            panel_y1,
            self.width - margin,
            panel_y2,
            "VALIDATE KANAN",
            right_validate
        )

        return canvas