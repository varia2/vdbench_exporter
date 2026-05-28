import asyncio
from unittest.mock import patch

import pytest
from prometheus_client import REGISTRY

from src.metrics import (
    vdbench_iops,
    vdbench_latency,
    vdbench_throughput
)
from src.runtime_state import RuntimeState

from src.vdbench_runner import (
    push_metrics,
    maybe_push_metrics,
    follow_vdbench_output
)

from src.shutdown import ShutdownController


@patch("src.vdbench_runner.push_to_gateway")
def test_push_metrics_called(mock_push):
    push_metrics("http://localhost:9091", "test_job")

    mock_push.assert_called_once()

    args, kwargs = mock_push.call_args

    assert args[0] == "http://localhost:9091"
    assert kwargs["job"] == "test_job"
    assert kwargs["registry"] == REGISTRY


@patch("src.vdbench_runner.push_metrics")
def test_maybe_push_metrics_calls_push(mock_push):
    maybe_push_metrics(
        "http://localhost:9091",
        "test_job"
    )

    mock_push.assert_called_once_with(
        "http://localhost:9091",
        "test_job"
    )


@patch("src.vdbench_runner.push_metrics")
def test_maybe_push_metrics_skips_none(mock_push):
    maybe_push_metrics(None, "test_job")

    mock_push.assert_not_called()


@pytest.mark.asyncio
@patch("src.vdbench_runner.push_metrics")
async def test_follow_output_updates_metrics(
        mock_push,
        tmp_path
):
    output_file = tmp_path / "flatfile.html"

    output_file.write_text("")

    async def writer():
        await asyncio.sleep(0.2)

        with output_file.open("a") as f:
            f.write("1000 10.5 1.2\n")
            f.flush()

    controller = ShutdownController()
    runtime_state = RuntimeState()

    reader_task = asyncio.create_task(
        follow_vdbench_output(
            str(output_file),
            shutdown_controller=controller,
            runtime_state=runtime_state,
            push_gateway="http://localhost:9091",
            job_name="test_job",
            polling=0
        )
    )

    writer_task = asyncio.create_task(writer())

    await asyncio.sleep(1)

    assert vdbench_iops._value.get() == 1000
    assert vdbench_throughput._value.get() == 10.5 * 1024 * 1024
    assert vdbench_latency._value.get() == 1.2

    assert mock_push.called

    # graceful shutdown
    controller.stop()

    await reader_task
    await writer_task


@pytest.mark.asyncio
@patch("src.vdbench_runner.push_metrics")
async def test_follow_output_ignores_invalid(mock_push, tmp_path):
    output_file = tmp_path / "flatfile.html"

    output_file.write_text("")

    async def writer():
        await asyncio.sleep(0.2)

        with output_file.open("a") as f:
            f.write("header line\n")
            f.write("\n")
            f.write("invalid data\n")
            f.flush()

    controller = ShutdownController()
    runtime_state = RuntimeState()
    reader_task = asyncio.create_task(
        follow_vdbench_output(
            str(output_file),
            push_gateway="http://localhost:9091",
            polling=0,
            shutdown_controller=controller,
            runtime_state=runtime_state
        )
    )

    writer_task = asyncio.create_task(writer())

    await asyncio.sleep(1)

    mock_push.assert_not_called()

    reader_task.cancel()

    try:
        await reader_task
    except asyncio.CancelledError:
        pass

    await writer_task