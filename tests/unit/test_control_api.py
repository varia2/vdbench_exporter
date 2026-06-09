import pytest

from httpx import (
    AsyncClient,
    ASGITransport
)

from src.control_api import create_control_api
from src.runtime_state import RuntimeState
from src.shutdown import ShutdownController


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path):
    output_file = tmp_path / "flatfile.html"

    output_file.write_text("")

    controller = ShutdownController()

    runtime_state = RuntimeState()

    app = create_control_api(
        controller,
        runtime_state,
        str(output_file),
        "api"
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:

        response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert data["reader_running"] is False

    assert data["shutdown_requested"] is False

    assert data["output_file_exists"] is True

    assert data["mode"] == "api"


@pytest.mark.asyncio
async def test_shutdown_endpoint(tmp_path):
    output_file = tmp_path / "flatfile.html"

    output_file.write_text("")

    controller = ShutdownController()

    runtime_state = RuntimeState()

    app = create_control_api(
        controller,
        runtime_state,
        str(output_file),
        "api"
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(
            transport=transport,
            base_url="http://test"
    ) as client:

        response = await client.post("/shutdown")

    assert response.status_code == 200

    assert response.json() == {
        "status": "stopping"
    }

    assert controller.is_stopped