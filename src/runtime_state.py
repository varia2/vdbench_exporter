import time


class RuntimeState:
    def __init__(self):
        self.started_at = time.time()

        self.last_metrics_update = None

        self.reader_running = False

    def mark_metrics_update(self):
        self.last_metrics_update = time.time()

    @property
    def uptime_seconds(self):
        return int(time.time() - self.started_at)

    @property
    def seconds_since_last_update(self):
        if self.last_metrics_update is None:
            return None

        return int(
            time.time() - self.last_metrics_update
        )