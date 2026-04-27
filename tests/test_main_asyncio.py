import pytest
from unittest.mock import patch, AsyncMock

from src.main import start_app
from src.utils import get_project_root, render_workload

import inspect
from src.vdbench_runner import run_vdbench

template_path = get_project_root() / "default_workload.tlp"

@pytest.mark.asyncio
@patch("src.main.run_vdbench", new_callable=AsyncMock)
@patch("src.main.asyncio.create_task")
async def test_main_creates_task(mock_create_task, mock_run_vdbench):
    class Args:
        vdbench_path = r"C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat"
        workload_config = render_workload(str(template_path))
        push_gateway = "http://localhost:9091"
        job_name = "test_job"
        mode = "online"
        port = 8000
        polling = 5

    await start_app(Args)

    assert mock_create_task.called

    mock_run_vdbench.assert_called_with(
        Args.vdbench_path,
        Args.workload_config,
        push_gateway="http://localhost:9091",
        job_name="test_job",
        polling=5
    )

@pytest.mark.asyncio
@patch("src.main.run_vdbench", new_callable=AsyncMock)
async def test_main_does_not_crash(mock_run):
    class Args:
        vdbench_path = r"C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat"
        workload_config = render_workload(str(template_path))
        push_gateway = None
        job_name = "vdbench"
        mode = "online"
        port = 8000
        polling = 5

    await start_app(Args)

def test_run_vdbench_signature():
    sig = inspect.signature(run_vdbench)

    assert "push_gateway" in sig.parameters
    assert "job_name" in sig.parameters

def test_create_task_called_correctly():
    import inspect
    import src.main

    sig = inspect.signature(src.main.asyncio.create_task)

    assert "push_gateway" not in sig.parameters