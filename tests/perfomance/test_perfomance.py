import asyncio
import json
import statistics
import time

import pytest

from src.runtime_state import RuntimeState
from src.shutdown import ShutdownController
from src.vdbench_runner import follow_vdbench_output, FlatfileSchema

import logging

logger = logging.getLogger(__name__)

@pytest.mark.performance
@pytest.mark.asyncio
async def test_processing_latency(tmp_path):
    flatfile = tmp_path / "flatfile.html"
    tracefile = tmp_path / "trace.jsonl"

    flatfile.touch()

    controller = ShutdownController()
    runtime = RuntimeState()
    schema = FlatfileSchema(
        rate_idx=0,
        mbs_idx=1,
        resp_idx=2
    )

    writer_times = {}

    reader_task = asyncio.create_task(
        follow_vdbench_output(
            str(flatfile),
            shutdown_controller=controller,
            runtime_state=runtime,
            polling=0,
            trace_file=str(tracefile),
            schema=schema,
        )
    )

    await asyncio.sleep(0.5)

    with flatfile.open("a") as f:

        for i in range(100):

            line = f"{1000+i} 10.5 1.2"

            writer_times[line] = time.time()

            f.write(line + "\n")
            f.flush()

            await asyncio.sleep(0.01)

    deadline = time.time() + 10

    while time.time() < deadline:

        if tracefile.exists():

            count = sum(
                1
                for _ in tracefile.open()
            )

            if count >= 100:
                break

        await asyncio.sleep(0.1)

    controller.stop()

    await reader_task

    latencies = []

    with tracefile.open() as f:

        for raw in f:

            entry = json.loads(raw)

            line = entry["line"]

            written_at = writer_times[line]

            processed_at = entry["processed_at"]

            latencies.append(
                processed_at - written_at
            )

    assert len(latencies) == 100

    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(
        latencies,
        n=100
    )[94]

    max_latency = max(latencies)

    logger.info(
        f"\nAVG={avg_latency:.6f}s "
        f"P95={p95_latency:.6f}s "
        f"MAX={max_latency:.6f}s"
    )

    assert p95_latency < 0.25