from threading import Thread


class DaemonThread:
    def __init__(self, target) -> None:
        self.thread = Thread(
            target=target.run,
            daemon=True,
        )

    def start(self):
        self.thread.start()
