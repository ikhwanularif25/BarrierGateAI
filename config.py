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
VERSION = "1.1.0-best4"


# =========================================================
# MODEL
# =========================================================

# best4 classes:
# - forklift
# - trolley / troli
# - object
#
# Loaded / empty tidak lagi berasal langsung dari class model.
# Status tersebut diturunkan oleh best4_adapter.py berdasarkan relasi spasial
# antara kendaraan dan object, lalu dikembalikan ke format output legacy.
MODEL_PATH = BASE_DIR / "models" / "best4.onnx"

# Global YOLO threshold. Detection di bawah nilai ini tidak dikeluarkan model.
CONFIDENCE = 0.35
IMAGE_SIZE = 416 #640

# =========================================================
# BEST4 RAW CLASS FILTER + SPATIAL ASSOCIATION
# =========================================================

MIN_CONF_VEHICLE = 0.35
MIN_CONF_OBJECT = 0.35

# Area pencarian muatan relatif terhadap bounding box forklift/trolley.
# Nilai ini sengaja sedikit diperluas karena bbox object/cargo dapat berada
# di atas atau sedikit di depan bbox kendaraan.
LOAD_ASSOCIATION_EXPAND_X = 0.25
LOAD_ASSOCIATION_EXPAND_TOP = 0.35
LOAD_ASSOCIATION_EXPAND_BOTTOM = 0.15

# Minimum intersection terhadap luas bbox object jika center object tidak
# masuk ke expanded vehicle box.
LOAD_ASSOCIATION_MIN_OBJECT_OVERLAP = 0.10

# =========================================================
# LEGACY OUTPUT CONFIDENCE FILTER
# =========================================================
# Setelah best4_adapter mengubah kelas menjadi forklift_loaded,
# forklift_empty, troli_loaded, troli_empty, threshold lama tetap digunakan.

MIN_CONF_EMPTY = 0.55
MIN_CONF_LOADED = 0.60


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

DISPLAY_WIDTH = 1920
DISPLAY_HEIGHT = 1080

TOP_BAR_HEIGHT = 100
BOTTOM_PANEL_HEIGHT = 70

MAX_DISTANCE = 5.0

# =========================================================

# NODE-RED

# =========================================================

NODE_RED_ENABLED = True

NODE_RED_URL = (
    "http://192.168.5.2:1880/"
    "barrier-gate/detection"
)

NODE_RED_TIMEOUT = 3.0
