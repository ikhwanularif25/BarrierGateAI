import cv2
import threading
import time


class LatestFrameCamera:
    """
    Camera reader untuk realtime AI.

    Thread kamera terus membaca RTSP.
    Frame lama tidak diantrikan untuk inference.
    Program AI hanya mengambil frame terbaru.
    """

    def __init__(
        self,
        source,
        backend=cv2.CAP_FFMPEG,
        reconnect=True,
        reconnect_delay=1.0
    ):
        self.source = source
        self.backend = backend

        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay

        self.cap = None

        self.frame = None
        self.frame_timestamp = None
        self.frame_id = 0

        self.running = False
        self.connected = False

        self.lock = threading.Lock()
        self.thread = None

    # =========================================================
    # OPEN CAMERA
    # =========================================================

    def _open(self):

        if self.cap is not None:
            self.cap.release()

        print("Connecting camera...")

        self.cap = cv2.VideoCapture(
            self.source,
            self.backend
        )

        # Request minimum buffering.
        self.cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        self.connected = self.cap.isOpened()

        if self.connected:
            print("Camera stream opened.")
        else:
            print("Camera stream failed.")

        return self.connected

    # =========================================================
    # START
    # =========================================================

    def start(self):

        if self.running:
            return self

        self.running = True

        self._open()

        self.thread = threading.Thread(
            target=self._reader_loop,
            daemon=True
        )

        self.thread.start()

        return self

    # =========================================================
    # CAMERA THREAD
    # =========================================================

    def _reader_loop(self):

        while self.running:

            if (
                self.cap is None
                or not self.cap.isOpened()
            ):

                self.connected = False

                if not self.reconnect:
                    break

                time.sleep(
                    self.reconnect_delay
                )

                self._open()

                continue

            ret, frame = self.cap.read()

            if not ret:

                self.connected = False

                print(
                    "RTSP frame gagal dibaca. "
                    "Mencoba reconnect..."
                )

                self.cap.release()

                if self.reconnect:

                    time.sleep(
                        self.reconnect_delay
                    )

                    self._open()

                    continue

                break

            # =================================================
            # ONLY KEEP LATEST FRAME
            # =================================================

            with self.lock:

                self.frame = frame

                self.frame_timestamp = (
                    time.perf_counter()
                )

                self.frame_id += 1

            self.connected = True

    # =========================================================
    # READ LATEST FRAME
    # =========================================================

    def read(self):

        with self.lock:

            if self.frame is None:

                return (
                    False,
                    None,
                    None,
                    None
                )

            return (
                True,
                self.frame.copy(),
                self.frame_timestamp,
                self.frame_id
            )

    # =========================================================
    # STATUS
    # =========================================================

    def isOpened(self):

        return (
            self.connected
            or self.frame is not None
        )

    # =========================================================
    # RELEASE
    # =========================================================

    def release(self):

        print(
            "Closing camera..."
        )

        self.running = False

        if self.cap is not None:
            self.cap.release()

        if self.thread is not None:
            self.thread.join(
                timeout=2
            )

        self.connected = False