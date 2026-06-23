import time


class RuntimeState:
    def __init__(self):
        self.started_at = time.time()

        self.last_metrics_update = None

        self.reader_running = False

        self.last_raw_line = None
        self.last_metrics = None

        self.processed_lines = 0
        self.mode = None
        self.offline_completed = False

    def mark_metrics_update(self, raw_line=None, metrics=None):
        self.last_metrics_update = time.time()

        if raw_line is not None:
            self.last_raw_line = raw_line

        if metrics is not None:
            self.last_metrics = metrics

        self.processed_lines += 1

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

    @property
    def has_metrics(self):
        return self.last_raw_line is not None