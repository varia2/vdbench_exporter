import inspect
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.main import start_app
from src.runtime_state import RuntimeState
from src.vdbench_runner import follow_vdbench_output
from src.shutdown import ShutdownController


class Args:
    output_file = "output/flatfile.html"
    input_file = None
    push_gateway = "http://localhost:9091"
    job_name = "test_job"
    polling = 5
    read_polling = 0.2
    stop_mode = "infinite"
    trace_file = "output/exporter_trace.jsonl"
    api_port = 8080


@pytest.mark.asyncio
@patch("src.main.wait_for_server_started", new_callable=AsyncMock)
@patch("src.main.create_control_api", return_value=MagicMock())
@patch("src.main.uvicorn.Server")
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_main_creates_reader_task(
        mock_create_task,
        mock_follow,
        mock_uvicorn_server,
        mock_create_api,
        mock_wait_server,
):
    mock_uvicorn_server.return_value.serve = AsyncMock()
    mock_create_task.side_effect = lambda coro: coro.close()

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    assert mock_create_task.called
    mock_follow.assert_called_with(
        Args.output_file,
        controller,
        runtime_state,
        push_gateway="http://localhost:9091",
        job_name="test_job",
        polling=5,
        read_polling=0.2,
        trace_file="output/exporter_trace.jsonl"
    )


@pytest.mark.asyncio
@patch("src.main.wait_for_server_started", new_callable=AsyncMock)
@patch("src.main.create_control_api", return_value=MagicMock())
@patch("src.main.uvicorn.Server")
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
async def test_main_does_not_crash(
        mock_follow,
        mock_uvicorn_server,
        mock_create_api,
        mock_wait_server,
):
    mock_uvicorn_server.return_value.serve = AsyncMock()

    class ArgsNoPush:
        output_file = "output/flatfile.html"
        input_file = None
        push_gateway = None
        job_name = "vdbench"
        polling = 5
        read_polling = 0.2
        stop_mode = "infinite"
        trace_file = "output/exporter_trace.jsonl"
        api_port = 8080

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(ArgsNoPush, controller, runtime_state)

    mock_follow.assert_called_once()

def test_follow_vdbench_output_signature():
    sig = inspect.signature(follow_vdbench_output)

    assert "push_gateway" in sig.parameters
    assert "job_name" in sig.parameters
    assert "polling" in sig.parameters
    assert "shutdown_controller" in sig.parameters
    assert "runtime_state" in sig.parameters


def test_create_task_signature():
    import src.main

    sig = inspect.signature(src.main.asyncio.create_task)

    assert "push_gateway" not in sig.parameters