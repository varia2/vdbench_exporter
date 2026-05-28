from unittest.mock import patch, AsyncMock

import pytest

from src.main import (
    start_app,
    stop_after_timeout
)
from src.runtime_state import RuntimeState

from src.shutdown import ShutdownController


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_infinite_mode_starts_only_reader(
        mock_create_task,
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

        stop_mode = "infinite"

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    # только reader task
    assert mock_create_task.call_count == 1


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_timer_mode_starts_timeout_task(
        mock_create_task,
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

        stop_mode = "timer"
        duration = 10

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    # reader + timer
    assert mock_create_task.call_count == 2


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_api_mode_starts_api_server(
        mock_create_task,
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

        stop_mode = "api"
        api_port = 8080

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    # reader + api
    assert mock_create_task.call_count == 2


@pytest.mark.asyncio
async def test_stop_after_timeout():
    controller = ShutdownController()

    assert not controller.is_stopped

    await stop_after_timeout(controller, 0)

    assert controller.is_stopped

@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_timer_mode_starts_timeout_task(
        mock_create_task,
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

        stop_mode = "timer"
        duration = 10

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(Args, controller, runtime_state)

    assert mock_create_task.call_count == 2