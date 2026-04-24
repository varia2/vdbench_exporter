import pytest
from unittest.mock import patch

from src.metrics import registry
from src.vdbench_runner import push_metrics, parse_vdbench_stream


@patch("src.vdbench_runner.push_to_gateway")
def test_push_metrics_called(mock_push):
    push_metrics("http://localhost:9091", "test_job")

    mock_push.assert_called_once()

    args, kwargs = mock_push.call_args

    assert args[0] == "http://localhost:9091"
    assert kwargs["job"] == "test_job"
    assert kwargs["registry"] == registry

class FakeStream:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    async def readline(self):
        if self.i >= len(self.lines):
            return b""
        line = self.lines[self.i]
        self.i += 1
        return line


@pytest.mark.asyncio
@patch("src.vdbench_runner.push_metrics")
async def test_parse_stream_triggers_push(mock_push):
    stream = FakeStream([
        b"1000 10.5 1.2\n"
    ])

    await parse_vdbench_stream(
        stream,
        push_gateway="http://localhost:9091",
        job_name="test_job"
    )

    assert mock_push.called

@pytest.mark.asyncio
@patch("src.vdbench_runner.push_metrics")
async def test_parse_stream_no_push(mock_push):
    stream = FakeStream([
        b"1000 10.5 1.2\n"
    ])

    await parse_vdbench_stream(stream)

    mock_push.assert_not_called()

@pytest.mark.asyncio
@patch("src.vdbench_runner.push_metrics")
async def test_parse_stream_ignores_invalid(mock_push):
    stream = FakeStream([
        b"header line\n",
        b"\n",
        b"invalid data\n"
    ])

    await parse_vdbench_stream(
        stream,
        push_gateway="http://localhost:9091"
    )

    mock_push.assert_not_called()