import pytest

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
async def test_parse_stream():
    from src.vdbench_runner import parse_vdbench_stream

    stream = FakeStream([
        b"iops 1000 latency 1.2\n",
        b"iops 2000 latency 2.3\n"
    ])

    # просто проверяем что не падает
    await parse_vdbench_stream(stream)