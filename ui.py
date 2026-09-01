import cv2
import numpy as np


class BarrierGateUI:

    def __init__(
        self,
        width=1920,
        height=1080,
        top_height=100,
        bottom_height=70,
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

        self.bg_black = (0, 0, 0)

        self.panel_gray = (120, 120, 120)
        self.header_gray = (115, 115, 115)

        self.white = (245, 245, 245)
        self.black = (0, 0, 0)

        self.yellow = (0, 230, 255)
        self.green = (80, 190, 80)
        self.red = (40, 40, 255)

        self.pink = (180, 105, 255)

        self.gray = (170, 170, 170)

        # =====================================================
        # LAYOUT
        # =====================================================

        self.outer_margin = 14
        self.zone_gap = 14

        self.info_bar_height = 95
        self.zone_border = 8

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
    # CENTER TEXT
    # =========================================================

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

        text_x = (
            x1
            + ((x2 - x1) - text_size[0]) // 2
        )

        text_y = (
            y1
            + ((y2 - y1) + text_size[1]) // 2
        )

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
        inference_ms
    ):

        cv2.rectangle(
            canvas,
            (
                self.outer_margin,
                self.outer_margin
            ),
            (
                self.width - self.outer_margin,
                self.top_height
            ),
            self.header_gray,
            -1
        )

        # =====================================================
        # TITLE
        # =====================================================

        self.put_text(
            canvas,
            "AI POWERED SMART BARRIER GATE",
            (
                max(
                    40,
                    int(self.width * 0.11)
                ),
                int(self.top_height * 0.68)
            ),
            scale=1.45,
            color=self.yellow,
            thickness=3
        )

        # =====================================================
        # RIGHT INFORMATION
        # =====================================================

        info_x = (
            self.width
            - 220
        )

        self.put_text(
            canvas,
            f"MAX DISTANCE {self.max_distance:.1f} M",
            (
                info_x,
                35
            ),
            scale=0.68,
            color=self.yellow,
            thickness=2
        )

        self.put_text(
            canvas,
            f"YOLO {inference_ms:.0f}MS",
            (
                info_x,
                62
            ),
            scale=0.68,
            color=self.yellow,
            thickness=2
        )

        self.put_text(
            canvas,
            f"FPS {fps:.1f}",
            (
                info_x,
                89
            ),
            scale=0.68,
            color=self.yellow,
            thickness=2
        )

    # =========================================================
    # ZONE LOGIC
    # =========================================================

    def get_zone_logic(
        self,
        objects,
        validated=False
    ):

        # =====================================================
        # NO OBJECT
        # =====================================================

        if not objects:

            return {
                "line1": "-",
                "line2": "-",

                "line1_color":
                    self.red,

                "line2_color":
                    self.red,

                "gate_state":
                    "standby"
            }

        names = [
            obj["name"]
            for obj in objects
        ]

        loaded_name = None
        empty_name = None

        # =====================================================
        # SEARCH LOADED FIRST
        # =====================================================

        for name in names:

            if name in (
                "forklift_loaded",
                "troli_loaded"
            ):

                loaded_name = name
                break

        # =====================================================
        # SEARCH EMPTY
        # =====================================================

        for name in names:

            if name in (
                "forklift_empty",
                "troli_empty"
            ):

                empty_name = name
                break

        # =====================================================
        # LOADED
        # =====================================================

        if loaded_name is not None:

            if (
                loaded_name
                == "forklift_loaded"
            ):

                line1 = (
                    "FORKLIFT TERDETEKSI "
                    "(ADA MUATAN)"
                )

            else:

                line1 = (
                    "TROLI TERDETEKSI "
                    "(ADA MUATAN)"
                )

            # =============================================
            # VALIDATED
            # =============================================

            if validated:

                return {
                    "line1":
                        line1,

                    "line2":
                        "VALIDATE OK",

                    "line1_color":
                        self.green,

                    "line2_color":
                        self.green,

                    "gate_state":
                        "open"
                }

            # =============================================
            # NOT VALIDATED
            # =============================================

            return {
                "line1":
                    line1,

                "line2":
                    "LAKUKAN VALIDATE "
                    "UNTUK MEMBUKA PORTAL",

                "line1_color":
                    self.green,

                "line2_color":
                    self.red,

                "gate_state":
                    "lock"
            }

        # =====================================================
        # EMPTY
        # =====================================================

        if empty_name is not None:

            if (
                empty_name
                == "forklift_empty"
            ):

                line1 = (
                    "FORKLIFT TERDETEKSI "
                    "(TIDAK ADA MUATAN)"
                )

            else:

                line1 = (
                    "TROLI TERDETEKSI "
                    "(TIDAK ADA MUATAN)"
                )

            return {
                "line1":
                    line1,

                "line2":
                    "-",

                "line1_color":
                    self.yellow,

                "line2_color":
                    self.red,

                "gate_state":
                    "countdown"
            }

        # =====================================================
        # UNKNOWN
        # =====================================================

        return {
            "line1": "-",
            "line2": "-",

            "line1_color":
                self.red,

            "line2_color":
                self.red,

            "gate_state":
                "standby"
        }

    # =========================================================
    # DRAW ZONE
    # =========================================================

    def draw_zone_panel(
        self,
        canvas,
        x1,
        y1,
        x2,
        y2,
        title,
        zone_frame,
        logic
    ):

        # =====================================================
        # PINK BORDER
        # =====================================================

        cv2.rectangle(
            canvas,
            (
                x1,
                y1
            ),
            (
                x2,
                y2
            ),
            self.pink,
            self.zone_border
        )

        # =====================================================
        # INFO PANEL
        # =====================================================

        info_y2 = (
            y1
            + self.info_bar_height
        )

        cv2.rectangle(
            canvas,
            (
                x1 + self.zone_border,
                y1 + self.zone_border
            ),
            (
                x2 - self.zone_border,
                info_y2
            ),
            self.panel_gray,
            -1
        )

        # =====================================================
        # CAMERA AREA
        # =====================================================

        frame_x1 = (
            x1
            + self.zone_border
        )

        frame_x2 = (
            x2
            - self.zone_border
        )

        frame_y1 = (
            info_y2
        )

        frame_y2 = (
            y2
            - self.zone_border
        )

        frame_width = (
            frame_x2
            - frame_x1
        )

        frame_height = (
            frame_y2
            - frame_y1
        )

        if (
            frame_width > 0
            and frame_height > 0
        ):

            resized = cv2.resize(
                zone_frame,
                (
                    frame_width,
                    frame_height
                ),
                interpolation=cv2.INTER_LINEAR
            )

            canvas[
                frame_y1:frame_y2,
                frame_x1:frame_x2
            ] = resized

        # =====================================================
        # INFO PANEL REPAINT
        # =====================================================

        cv2.rectangle(
            canvas,
            (
                x1 + self.zone_border,
                y1 + self.zone_border
            ),
            (
                x2 - self.zone_border,
                info_y2
            ),
            self.panel_gray,
            -1
        )

        # =====================================================
        # ZONE TITLE
        # =====================================================

        self.put_text(
            canvas,
            title,
            (
                x1 + 20,
                y1 + 38
            ),
            scale=0.78,
            color=self.yellow,
            thickness=2
        )

        # =====================================================
        # STATUS LINE 1
        # =====================================================

        self.put_text(
            canvas,
            logic["line1"],
            (
                x1 + 20,
                y1 + 68
            ),
            scale=0.68,
            color=logic[
                "line1_color"
            ],
            thickness=2
        )

        # =====================================================
        # STATUS LINE 2
        # =====================================================

        self.put_text(
            canvas,
            logic["line2"],
            (
                x1 + 20,
                y1 + 93
            ),
            scale=0.64,
            color=logic[
                "line2_color"
            ],
            thickness=2
        )

    # =========================================================
    # GET BOTTOM BAR STYLE
    # =========================================================

    def get_bottom_bar_style(
        self,
        state
    ):

        # =====================================================
        # OPEN
        # =====================================================

        if state == "open":

            return (
                self.green,
                "OPEN"
            )

        # =====================================================
        # LOCK
        # =====================================================

        if state == "lock":

            return (
                self.red,
                "LOCK"
            )

        # =====================================================
        # EMPTY COUNTDOWN
        # =====================================================

        if state == "countdown":

            return (
                self.yellow,
                "TERBUKA DALAM 5 DETIK"
            )

        # =====================================================
        # DEFAULT
        # =====================================================

        return (
            self.gray,
            "STANDBY"
        )

    # =========================================================
    # DRAW BOTTOM STATUS
    # =========================================================

    def draw_bottom_status(
        self,
        canvas,
        left_logic,
        right_logic
    ):

        bar_y1 = (
            self.height
            - self.bottom_height
            - self.outer_margin
        )

        bar_y2 = (
            self.height
            - self.outer_margin
        )

        available_width = (
            self.width
            - (self.outer_margin * 2)
            - self.zone_gap
        )

        half_width = (
            available_width
            // 2
        )

        # =====================================================
        # LEFT
        # =====================================================

        left_x1 = (
            self.outer_margin
        )

        left_x2 = (
            left_x1
            + half_width
        )

        left_color, left_text = (
            self.get_bottom_bar_style(
                left_logic[
                    "gate_state"
                ]
            )
        )

        cv2.rectangle(
            canvas,
            (
                left_x1,
                bar_y1
            ),
            (
                left_x2,
                bar_y2
            ),
            left_color,
            -1
        )

        self.put_center_text(
            canvas,
            left_text,
            left_x1,
            bar_y1,
            left_x2,
            bar_y2,
            scale=0.90,
            color=self.black,
            thickness=2
        )

        # =====================================================
        # RIGHT
        # =====================================================

        right_x1 = (
            left_x2
            + self.zone_gap
        )

        right_x2 = (
            self.width
            - self.outer_margin
        )

        right_color, right_text = (
            self.get_bottom_bar_style(
                right_logic[
                    "gate_state"
                ]
            )
        )

        cv2.rectangle(
            canvas,
            (
                right_x1,
                bar_y1
            ),
            (
                right_x2,
                bar_y2
            ),
            right_color,
            -1
        )

        self.put_center_text(
            canvas,
            right_text,
            right_x1,
            bar_y1,
            right_x2,
            bar_y2,
            scale=0.90,
            color=self.black,
            thickness=2
        )

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

        # =====================================================
        # CANVAS
        # =====================================================

        canvas = np.zeros(
            (
                self.height,
                self.width,
                3
            ),
            dtype=np.uint8
        )

        canvas[:] = (
            self.bg_black
        )

        # =====================================================
        # HEADER
        # =====================================================

        self.draw_header(
            canvas,
            fps,
            inference_ms
        )

        # =====================================================
        # ZONE DIMENSIONS
        # =====================================================

        zone_y1 = (
            self.top_height
            + 6
        )

        zone_y2 = (
            self.height
            - self.bottom_height
            - (self.outer_margin * 2)
        )

        available_width = (
            self.width
            - (self.outer_margin * 2)
            - self.zone_gap
        )

        zone_width = (
            available_width
            // 2
        )

        # =====================================================
        # LEFT POSITION
        # =====================================================

        left_x1 = (
            self.outer_margin
        )

        left_x2 = (
            left_x1
            + zone_width
        )

        # =====================================================
        # RIGHT POSITION
        # =====================================================

        right_x1 = (
            left_x2
            + self.zone_gap
        )

        right_x2 = (
            self.width
            - self.outer_margin
        )

        # =====================================================
        # CAMERA DISPLAY SIZE
        # =====================================================

        camera_height = (
            zone_y2
            - zone_y1
            - self.info_bar_height
            - self.zone_border
        )

        camera_height = max(
            camera_height,
            1
        )

        # =====================================================
        # ORIGINAL FRAME SIZE
        # =====================================================

        original_h, original_w = (
            frame.shape[:2]
        )

        # =====================================================
        # RESIZE FULL FRAME
        # =====================================================

        target_width = (
            zone_width
            * 2
        )

        display_frame = cv2.resize(
            frame,
            (
                target_width,
                camera_height
            ),
            interpolation=cv2.INTER_LINEAR
        )

        # =====================================================
        # SPLIT
        # =====================================================

        left_frame = (
            display_frame[
                :,
                :zone_width
            ]
            .copy()
        )

        right_frame = (
            display_frame[
                :,
                zone_width:
            ]
            .copy()
        )

        # =====================================================
        # DETECTION OBJECT LIST
        # =====================================================

        left_objects = []
        right_objects = []

        scale_x = (
            target_width
            / original_w
        )

        scale_y = (
            camera_height
            / original_h
        )

        # =====================================================
        # DRAW DETECTIONS
        # =====================================================

        for obj in detections:

            x1 = int(
                obj["x1"]
                * scale_x
            )

            y1 = int(
                obj["y1"]
                * scale_y
            )

            x2 = int(
                obj["x2"]
                * scale_x
            )

            y2 = int(
                obj["y2"]
                * scale_y
            )

            center_x = (
                (x1 + x2)
                // 2
            )

            name = (
                obj["name"]
            )

            confidence = (
                obj["confidence"]
            )

            label = (
                f"{name} "
                f"{confidence:.2f}"
            )

            # =================================================
            # BOX COLOR
            # =================================================

            if "loaded" in name:

                color = (
                    self.green
                )

            else:

                color = (
                    self.yellow
                )

            # =================================================
            # LEFT ZONE
            # =================================================

            if (
                center_x
                < zone_width
            ):

                left_objects.append(
                    obj
                )

                # Clip coordinates
                lx1 = max(
                    0,
                    min(
                        zone_width - 1,
                        x1
                    )
                )

                lx2 = max(
                    0,
                    min(
                        zone_width - 1,
                        x2
                    )
                )

                ly1 = max(
                    0,
                    min(
                        camera_height - 1,
                        y1
                    )
                )

                ly2 = max(
                    0,
                    min(
                        camera_height - 1,
                        y2
                    )
                )

                cv2.rectangle(
                    left_frame,
                    (
                        lx1,
                        ly1
                    ),
                    (
                        lx2,
                        ly2
                    ),
                    color,
                    2
                )

                self.put_text(
                    left_frame,
                    label,
                    (
                        lx1,
                        max(
                            20,
                            ly1 - 8
                        )
                    ),
                    scale=0.45,
                    color=color,
                    thickness=2
                )

            # =================================================
            # RIGHT ZONE
            # =================================================

            else:

                right_objects.append(
                    obj
                )

                rx1 = (
                    x1
                    - zone_width
                )

                rx2 = (
                    x2
                    - zone_width
                )

                rx1 = max(
                    0,
                    min(
                        zone_width - 1,
                        rx1
                    )
                )

                rx2 = max(
                    0,
                    min(
                        zone_width - 1,
                        rx2
                    )
                )

                ry1 = max(
                    0,
                    min(
                        camera_height - 1,
                        y1
                    )
                )

                ry2 = max(
                    0,
                    min(
                        camera_height - 1,
                        y2
                    )
                )

                cv2.rectangle(
                    right_frame,
                    (
                        rx1,
                        ry1
                    ),
                    (
                        rx2,
                        ry2
                    ),
                    color,
                    2
                )

                self.put_text(
                    right_frame,
                    label,
                    (
                        rx1,
                        max(
                            20,
                            ry1 - 8
                        )
                    ),
                    scale=0.45,
                    color=color,
                    thickness=2
                )

        # =====================================================
        # LEFT LOGIC
        # =====================================================

        left_logic = (
            self.get_zone_logic(
                left_objects,
                validated=validate_left
            )
        )

        # =====================================================
        # RIGHT LOGIC
        # =====================================================

        right_logic = (
            self.get_zone_logic(
                right_objects,
                validated=validate_right
            )
        )

        # =====================================================
        # DRAW LEFT ZONE
        # =====================================================

        self.draw_zone_panel(
            canvas,
            left_x1,
            zone_y1,
            left_x2,
            zone_y2,
            "IN ZONE",
            left_frame,
            left_logic
        )

        # =====================================================
        # DRAW RIGHT ZONE
        # =====================================================

        self.draw_zone_panel(
            canvas,
            right_x1,
            zone_y1,
            right_x2,
            zone_y2,
            "OUT ZONE",
            right_frame,
            right_logic
        )

        # =====================================================
        # DRAW INDEPENDENT BOTTOM STATUS
        # =====================================================

        self.draw_bottom_status(
            canvas,
            left_logic,
            right_logic
        )

        return canvas