import copy
import queue
import threading
import time
from datetime import datetime, timezone

import requests


class NodeRedSender:
    def __init__(
        self,
        url,
        timeout=3.0,
        queue_size=100,
        presence_interval=1.0,
        presence_max_age=2.0,
    ):
        self.url = url
        self.timeout = timeout
        self.presence_interval = presence_interval
        self.presence_max_age = presence_max_age

        # Antrean pengiriman deteksi lama: LOADED / EMPTY.
        self.jobs = queue.Queue(maxsize=queue_size)

        # Presence hanya menyimpan laporan terbaru per kamera.
        self._presence_pending = {}
        self._presence_last_sent = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()

        self.running = True

        self.worker = threading.Thread(
            target=self._worker_loop,
            name="NodeRedSender",
            daemon=True,
        )
        self.worker.start()

    def send(self, payload):
        """
        Pengiriman deteksi seperti sebelumnya.
        Pemanggilan lama sender.send(payload) tetap berlaku.
        """
        with self._lock:
            if not self.running:
                return False

            try:
                self.jobs.put_nowait(copy.deepcopy(payload))
                return True

            except queue.Full:
                print(
                    "[NODE-RED] queue penuh, payload dilewati"
                )
                return False

    def send_presence(self, camera, has_vehicle):
        """
        Panggil setelah frame DAN inferensi berhasil.

        True  = ada kendaraan di ROI.
        False = tidak ada kendaraan di ROI.

        Jangan panggil False saat kamera/inferensi gagal.
        """
        if not isinstance(has_vehicle, bool):
            raise ValueError("has_vehicle harus boolean")

        camera = str(camera)
        now = time.monotonic()

        payload = {
            "event": "vehicle_presence",
            "camera": camera,
            "has_vehicle": has_vehicle,
            "observed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        with self._lock:
            if not self.running:
                return False

            # Timpa laporan lama dengan pengamatan terbaru.
            self._presence_pending[camera] = (
                now,
                payload,
            )

        return True

    def _take_presence(self):
        now = time.monotonic()

        with self._lock:
            for camera, item in list(
                self._presence_pending.items()
            ):
                observed_at, payload = item

                # Jangan mengirim pengamatan lama ketika
                # kamera berhenti atau koneksi melambat.
                if now - observed_at > self.presence_max_age:
                    del self._presence_pending[camera]
                    continue

                previous = self._presence_last_sent.get(camera)

                if previous is not None:
                    last_attempt, last_state = previous

                    state_changed = (
                        payload["has_vehicle"] != last_state
                    )

                    # Perubahan status dikirim segera.
                    # Status tetap dikirim maksimal 1x/detik.
                    if (
                        not state_changed
                        and now - last_attempt
                        < self.presence_interval
                    ):
                        continue

                del self._presence_pending[camera]

                self._presence_last_sent[camera] = (
                    now,
                    payload["has_vehicle"],
                )

                return payload

        return None

    def _post(self, session, payload):
        try:
            response = session.post(
                self.url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            print("[NODE-RED] sent:", payload)

        except requests.RequestException as exc:
            print("[NODE-RED] send failed:", exc)

    def _worker_loop(self):
        with requests.Session() as session:
            while not self._stop.is_set():
                # Dahulukan laporan keberadaan kendaraan.
                presence = self._take_presence()

                if presence is not None:
                    if self._stop.is_set():
                        break
                    self._post(session, presence)

                if self._stop.is_set():
                    break

                try:
                    payload = self.jobs.get(timeout=0.1)
                except queue.Empty:
                    continue

                try:
                    if not self._stop.is_set():
                        self._post(session, payload)
                finally:
                    self.jobs.task_done()

    def close(self):
        """
        Hentikan pengiriman baru.
        Pesan yang belum dikirim dibuang saat shutdown.
        """
        with self._lock:
            self.running = False
            self._presence_pending.clear()

        self._stop.set()

        while True:
            try:
                self.jobs.get_nowait()
            except queue.Empty:
                break
            else:
                self.jobs.task_done()

        # Permintaan HTTP yang sedang berjalan mungkin
        # masih menunggu timeout.
        self.worker.join(timeout=1.0)


class VehiclePresenceSender:
    """
    Kompatibilitas dengan contoh pemanggilan sebelumnya.
    Jika sudah memakai NodeRedSender, cukup gunakan
    metode send_presence() pada objek yang sama.
    """

    def __init__(
        self,
        url="http://192.168.5.2:1880/barrier-gate/detection",
        interval_seconds=1.0,
    ):
        self._sender = NodeRedSender(
            url=url,
            timeout=1.0,
            presence_interval=interval_seconds,
        )

    def send_presence(self, camera, has_vehicle):
        return self._sender.send_presence(
            camera=camera,
            has_vehicle=has_vehicle,
        )

    def close(self):
        self._sender.close()