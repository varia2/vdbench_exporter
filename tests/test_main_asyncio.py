import inspect
from unittest.mock import patch, AsyncMock

import pytest

from src.main import start_app
from src.vdbench_runner import follow_vdbench_output


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_main_creates_reader_task(
        mock_create_task,
        mock_follow
):
    class Args:
        output_file = "output/flatfile.html"
        push_gateway = "http://localhost:9091"
        job_name = "test_job"
        polling = 5

    await start_app(Args)

    assert mock_create_task.called

    mock_follow.assert_called_with(
        Args.output_file,
        push_gateway="http://localhost:9091",
        job_name="test_job",
        polling=5
    )


@pytest.mark.asyncio
@patch("src.main.follow_vdbench_output", new_callable=AsyncMock)
async def test_main_does_not_crash(mock_follow):
    class Args:
        output_file = "output/flatfile.html"
        push_gateway = None
        job_name = "vdbench"
        polling = 5

    await start_app(Args)

    mock_follow.assert_called_once()


def test_follow_vdbench_output_signature():
    sig = inspect.signature(follow_vdbench_output)

    assert "push_gateway" in sig.parameters
    assert "job_name" in sig.parameters
    assert "polling" in sig.parameters


def test_create_task_signature():
    import src.main

    sig = inspect.signature(src.main.asyncio.create_task)

    assert "push_gateway" not in sig.parameters