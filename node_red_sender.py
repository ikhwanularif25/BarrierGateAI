import requests

import threading

import queue

import time





class NodeRedSender:

    def __init__(

        self,

        url,

        timeout=3.0,

        queue_size=100

    ):

        self.url = url

        self.timeout = timeout



        self.jobs = queue.Queue(

            maxsize=queue_size

        )



        self.running = True



        self.worker = threading.Thread(

            target=self._worker_loop,

            daemon=True

        )



        self.worker.start()



    def send(self, payload):

        try:

            self.jobs.put_nowait(payload)

            return True



        except queue.Full:

            print(

                "[NODE-RED] queue penuh, "

                "payload dilewati"

            )

            return False



    def _worker_loop(self):

        while (

            self.running

            or not self.jobs.empty()

        ):



            try:

                payload = self.jobs.get(

                    timeout=0.5

                )



            except queue.Empty:

                continue



            try:

                response = requests.post(

                    self.url,

                    json=payload,

                    timeout=self.timeout

                )



                response.raise_for_status()



                print(

                    "[NODE-RED] sent:",

                    payload

                )



            except Exception as exc:

                print(

                    "[NODE-RED] send failed:",

                    exc

                )



            finally:

                self.jobs.task_done()



    def close(self):

        self.running = False



        deadline = (

            time.monotonic()

            + 2.0

        )



        while (

            not self.jobs.empty()

            and time.monotonic()

            < deadline

        ):

            time.sleep(0.05)



        self.worker.join(

            timeout=1.0

        )