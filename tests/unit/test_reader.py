import asyncio

import pytest

from src.runtime_state import RuntimeState
from src.vdbench_runner import follow_vdbench_output
from src.metrics import (
    vdbench_iops,
    vdbench_latency,
    vdbench_throughput
)

from src.shutdown import ShutdownController


@pytest.mark.asyncio
async def test_follow_vdbench_output(tmp_path):
    output_file = tmp_path / "flatfile.html"

    output_file.write_text(
        "Rate Resp MB/sec\n"
    )

    async def writer():
        await asyncio.sleep(0.2)

        with output_file.open("a") as f:
            f.write("1000 1.2 10.5\n")
            f.flush()

    controller = ShutdownController()
    runtime_state = RuntimeState()
    reader_task = asyncio.create_task(
        follow_vdbench_output(str(output_file), controller, runtime_state, trace_file="")
    )

    writer_task = asyncio.create_task(writer())

    await asyncio.sleep(1)

    assert vdbench_iops._value.get() == 1000
    assert vdbench_throughput._value.get() == 10.5 * 1024 * 1024
    assert vdbench_latency._value.get() == 1.2

    reader_task.cancel()

    try:
        await reader_task
    except asyncio.CancelledError:
        pass

    await writer_task