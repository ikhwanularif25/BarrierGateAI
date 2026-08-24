from pathlib import Path
from urllib.parse import quote
import os

from dotenv import load_dotenv


# =========================================================
# BASE
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


# =========================================================
# PROJECT
# =========================================================

PROJECT_NAME = "Smart Barrier Gate AI"
VERSION = "1.0.1"


# =========================================================
# MODEL
# =========================================================

MODEL_PATH = BASE_DIR / "models" / "best2.pt"

CONFIDENCE = 0.35
IMAGE_SIZE = 640


# =========================================================
# CAMERA SOURCE
# =========================================================

# Pilihan:
# "webcam"
# "rtsp"
# "video"

CAMERA_MODE = "rtsp"


# =========================================================
# WEBCAM
# =========================================================

WEBCAM_INDEX = 0


# =========================================================
# VIDEO RECORDING
# =========================================================

VIDEO_PATH = BASE_DIR / "videos" / "record_cctv.mp4"


# =========================================================
# CCTV / RTSP
# =========================================================

CCTV_IP = os.getenv("CCTV_IP")
CCTV_USERNAME = os.getenv("CCTV_USERNAME")
CCTV_PASSWORD = os.getenv("CCTV_PASSWORD")

CCTV_PORT = int(
    os.getenv("CCTV_PORT", "554")
)

CAMERA_NUMBER = int(
    os.getenv("CAMERA_NUMBER", "14")
)

STREAM_NUMBER = os.getenv(
    "STREAM_NUMBER",
    "02"
)


# =========================================================
# VALIDATE ENV
# =========================================================

if CAMERA_MODE == "rtsp":

    required_env = {
        "CCTV_IP": CCTV_IP,
        "CCTV_USERNAME": CCTV_USERNAME,
        "CCTV_PASSWORD": CCTV_PASSWORD,
    }

    missing = [
        key
        for key, value in required_env.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Environment variable belum diisi: "
            + ", ".join(missing)
        )


# =========================================================
# RTSP URL
# =========================================================

# Password harus URL encoded.
# Contoh @ menjadi %40 secara otomatis.

CCTV_USERNAME_ENCODED = quote(
    CCTV_USERNAME or "",
    safe=""
)

CCTV_PASSWORD_ENCODED = quote(
    CCTV_PASSWORD or "",
    safe=""
)

# Camera 14:
# 1401 = main stream
# 1402 = sub stream

CCTV_CHANNEL = (
    f"{CAMERA_NUMBER}"
    f"{STREAM_NUMBER}"
)

RTSP_URL = (
    f"rtsp://"
    f"{CCTV_USERNAME_ENCODED}:"
    f"{CCTV_PASSWORD_ENCODED}"
    f"@{CCTV_IP}:"
    f"{CCTV_PORT}"
    f"/Streaming/Channels/"
    f"{CCTV_CHANNEL}"
)


# =========================================================
# DISPLAY
# =========================================================

WINDOW_NAME = (
    f"{PROJECT_NAME} - "
    f"Cam{CAMERA_NUMBER:03d}"
)

FULLSCREEN = True

DISPLAY_WIDTH = 1648
DISPLAY_HEIGHT = 928

TOP_BAR_HEIGHT = 70
BOTTOM_PANEL_HEIGHT = 190

MAX_DISTANCE = 5.0