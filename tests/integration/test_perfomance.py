import json
import statistics
import time
from pathlib import Path

import pytest

import logging

logger = logging.getLogger(__name__)


TRACE_FILE = Path("output/exporter_trace.jsonl")


def load_trace():
    with TRACE_FILE.open() as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


@pytest.mark.performance
def test_exporter_detection_latency():

    deadline = time.time() + 60

    while True:

        entries = load_trace()

        if len(entries) >= 30:
            break

        assert time.time() < deadline, (
            "Not enough trace entries collected"
        )

        time.sleep(1)

    entries = entries[-30:]

    latencies = []

    for entry in entries:

        latency = (
            entry["processed_at"]
            - entry["flatfile_mtime"]
        )

        latencies.append(latency)

    avg_latency = statistics.mean(latencies)

    p95_latency = statistics.quantiles(
        latencies,
        n=100
    )[94]

    max_latency = max(latencies)

    logger.info(
        f"\nDetection latency:"
        f"\nAVG={avg_latency:.3f}s"
        f"\nP95={p95_latency:.3f}s"
        f"\nMAX={max_latency:.3f}s"
    )

    #
    # При sleep(0.2)
    # ожидаем примерно:
    #
    # avg ~0.1
    # max <0.25
    #

    assert avg_latency < 0.2
    assert p95_latency < 0.3