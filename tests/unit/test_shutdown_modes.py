import pytest
from unittest.mock import patch, AsyncMock

from src.main import start_app, stop_after_timeout
from src.shutdown import ShutdownController
from src.runtime_state import RuntimeState


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.uvicorn.Server")
@patch("src.main.uvicorn.Config")
@patch("src.main.create_control_api")
@patch("src.main.asyncio.create_task")
async def test_infinite_mode_starts_reader_and_api(
        mock_create_task,
        mock_create_control_api,
        mock_uvicorn_config,
        mock_uvicorn_server,
        mock_follow
):
    mock_create_task.side_effect = (
        lambda coro: coro.close()
    )

    class Args:
        output_file = "output/flatfile.html"
        push_gateway = None
        job_name = "vdbench"
        polling = 5
        read_polling = 0.2

        stop_mode = "infinite"
        trace_file = "output/exporter_trace.jsonl"
        api_port = 8080

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    mock_create_control_api.assert_called_once_with(
        controller,
        runtime_state,
        Args.output_file,
        Args.stop_mode
    )

    mock_uvicorn_config.assert_called_once()
    mock_uvicorn_server.assert_called_once()

    # reader + api
    assert mock_create_task.call_count == 2


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.uvicorn.Server")
@patch("src.main.uvicorn.Config")
@patch("src.main.create_control_api")
@patch("src.main.asyncio.create_task")
async def test_timer_mode_starts_reader_api_and_timeout(
        mock_create_task,
        mock_create_control_api,
        mock_uvicorn_config,
        mock_uvicorn_server,
        mock_follow
):
    mock_create_task.side_effect = (
        lambda coro: coro.close()
    )

    class Args:
        output_file = "output/flatfile.html"
        push_gateway = None
        job_name = "vdbench"
        polling = 5
        read_polling = 0.2

        stop_mode = "timer"
        duration = 10
        trace_file = "output/exporter_trace.jsonl"
        api_port = 8080

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    mock_create_control_api.assert_called_once_with(
        controller,
        runtime_state,
        Args.output_file,
        Args.stop_mode
    )

    mock_uvicorn_config.assert_called_once()
    mock_uvicorn_server.assert_called_once()

    # reader + api + timer
    assert mock_create_task.call_count == 3


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.uvicorn.Server")
@patch("src.main.uvicorn.Config")
@patch("src.main.create_control_api")
@patch("src.main.asyncio.create_task")
async def test_api_mode_starts_reader_and_api(
        mock_create_task,
        mock_create_control_api,
        mock_uvicorn_config,
        mock_uvicorn_server,
        mock_follow
):
    mock_create_task.side_effect = (
        lambda coro: coro.close()
    )

    class Args:
        output_file = "output/flatfile.html"
        push_gateway = None
        job_name = "vdbench"
        polling = 5
        read_polling = 0.2

        stop_mode = "api"
        api_port = 8080
        trace_file = "output/exporter_trace.jsonl"

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    mock_create_control_api.assert_called_once_with(
        controller,
        runtime_state,
        Args.output_file,
        Args.stop_mode
    )

    mock_uvicorn_config.assert_called_once()
    mock_uvicorn_server.assert_called_once()

    # reader + api
    assert mock_create_task.call_count == 2


@pytest.mark.asyncio
async def test_stop_after_timeout():
    controller = ShutdownController()

    assert not controller.is_stopped

    await stop_after_timeout(controller, 0)

    assert controller.is_stopped