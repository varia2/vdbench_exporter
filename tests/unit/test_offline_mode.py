import json
import pytest
from pathlib import Path

from src.runtime_state import RuntimeState
from src.vdbench_runner import (
    run_offline,
    FlatfileSchema,
)
from src.metrics import (
    vdbench_iops,
    vdbench_latency,
    vdbench_throughput,
)


def write_flatfile(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def reset_metrics():
    vdbench_iops.set(0)
    vdbench_latency.set(0)
    vdbench_throughput.set(0)
    yield
    vdbench_iops.set(0)
    vdbench_latency.set(0)
    vdbench_throughput.set(0)


@pytest.mark.asyncio
async def test_run_offline_exports_last_metrics(tmp_path):
    flatfile = tmp_path / "flatfile.html"

    write_flatfile(
        flatfile,
        [
            "Rate MB/sec Resp",
            "1000 10.0 1.0",
            "2000 20.5 2.5",
            "3000 30.0 3.0",
        ]
    )

    runtime = RuntimeState()
    schema = FlatfileSchema(rate_idx=0, mbs_idx=1, resp_idx=2)

    await run_offline(
        file_path=str(flatfile),
        runtime_state=runtime,
        schema=schema,
    )

    assert runtime.processed_lines == 3
    assert runtime.last_raw_line == "3000 30.0 3.0"
    assert runtime.last_metrics is not None

    assert runtime.last_metrics.iops == 3000
    assert runtime.last_metrics.latency_ms == 3.0
    assert runtime.last_metrics.throughput_bytes == 30.0 * 1024 * 1024

    assert vdbench_iops._value.get() == 3000
    assert vdbench_latency._value.get() == 3.0
    assert vdbench_throughput._value.get() == 30.0 * 1024 * 1024


@pytest.mark.asyncio
async def test_run_offline_skips_header_and_invalid_lines(tmp_path):
    flatfile = tmp_path / "flatfile.html"

    write_flatfile(
        flatfile,
        [
            "Rate MB/sec Resp",
            "",
            "interval something",
            "not_a_metric_line",
            "1500 15.0 1.5",
            "2000 25.0 2.0",
        ]
    )

    runtime = RuntimeState()
    schema = FlatfileSchema(rate_idx=0, mbs_idx=1, resp_idx=2)

    await run_offline(
        file_path=str(flatfile),
        runtime_state=runtime,
        schema=schema,
    )

    # Только две валидные строки
    assert runtime.processed_lines == 2
    assert runtime.last_raw_line == "2000 25.0 2.0"
    assert runtime.last_metrics.iops == 2000
    assert runtime.last_metrics.latency_ms == 2.0
    assert runtime.last_metrics.throughput_bytes == 25.0 * 1024 * 1024


@pytest.mark.asyncio
async def test_run_offline_writes_trace(tmp_path):
    flatfile = tmp_path / "flatfile.html"
    tracefile = tmp_path / "trace.jsonl"

    write_flatfile(
        flatfile,
        [
            "Rate MB/sec Resp",
            "1111 11.0 1.1",
            "2222 22.0 2.2",
        ]
    )

    runtime = RuntimeState()
    schema = FlatfileSchema(rate_idx=0, mbs_idx=1, resp_idx=2)

    await run_offline(
        file_path=str(flatfile),
        runtime_state=runtime,
        trace_file=str(tracefile),
        schema=schema,
    )

    assert tracefile.exists()

    rows = [
        json.loads(line)
        for line in tracefile.read_text(encoding="utf-8").splitlines()
    ]

    assert len(rows) == 2

    assert rows[0]["line"] == "1111 11.0 1.1"
    assert rows[0]["iops"] == 1111
    assert rows[0]["latency"] == 1.1

    assert rows[1]["line"] == "2222 22.0 2.2"
    assert rows[1]["iops"] == 2222
    assert rows[1]["latency"] == 2.2