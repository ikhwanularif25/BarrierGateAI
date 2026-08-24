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
VERSION = "1.1.0"


# =========================================================
# MODEL
# =========================================================

MODEL_PATH = BASE_DIR / "models" / "best.pt"

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

WEBCAM_INDEX = 1


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

STREAM_NUMBER = os.getenv(
    "STREAM_NUMBER",
    "02"
)


# =========================================================
# CAMERA AUTO ROTATION
# =========================================================

CAMERA_AUTO_ROTATE = True

CAMERA_START = 1
CAMERA_END = 16

# Ganti kamera setiap 10 detik
CAMERA_SWITCH_INTERVAL = 10


# =========================================================
# VALIDATE ENV
# =========================================================

if CAMERA_MODE.strip().lower() == "rtsp":

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
# URL ENCODING
# =========================================================

CCTV_USERNAME_ENCODED = quote(
    CCTV_USERNAME or "",
    safe=""
)

CCTV_PASSWORD_ENCODED = quote(
    CCTV_PASSWORD or "",
    safe=""
)


# =========================================================
# RTSP URL GENERATOR
# =========================================================

def get_cctv_channel(camera_number: int) -> str:
    """
    Contoh substream:
    Cam001 -> 102
    Cam002 -> 202
    Cam014 -> 1402
    Cam016 -> 1602
    """

    return f"{camera_number}{STREAM_NUMBER}"


def get_rtsp_url(camera_number: int) -> str:

    channel = get_cctv_channel(
        camera_number
    )

    return (
        f"rtsp://"
        f"{CCTV_USERNAME_ENCODED}:"
        f"{CCTV_PASSWORD_ENCODED}"
        f"@{CCTV_IP}:"
        f"{CCTV_PORT}"
        f"/Streaming/Channels/"
        f"{channel}"
    )


# =========================================================
# DISPLAY
# =========================================================

WINDOW_NAME = PROJECT_NAME

FULLSCREEN = True

DISPLAY_WIDTH = 1648
DISPLAY_HEIGHT = 928

TOP_BAR_HEIGHT = 70
BOTTOM_PANEL_HEIGHT = 190

MAX_DISTANCE = 5.0