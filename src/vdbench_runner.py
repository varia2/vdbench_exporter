import asyncio
import re
from pathlib import Path

from prometheus_client import Gauge

# Метрики
iops = Gauge('vdbench_iops', 'IOPS')
latency = Gauge('vdbench_latency_ms', 'Latency in ms')
throughput = Gauge('vdbench_throughput_bytes', 'Throughput in bytes/sec')

METRICS_RE = re.compile(
    r"(?P<iops>\d+)\s+(?P<mbs>\d+\.?\d*)\s+(?P<lat>\d+\.?\d*)"
)

async def parse_vdbench_stream(stream):
    while True:
        raw = await stream.readline()
        if not raw:
            break

        line = decode_line(raw)

        if not is_valid_line(line):
            continue

        match = METRICS_RE.search(line)
        if not match:
            continue

        iops = float(match.group("iops"))
        mbs = float(match.group("mbs"))
        lat = float(match.group("lat"))

        # Prometheus update
        iops.set(iops)
        throughput.set(mbs * 1024 * 1024)
        latency.set(lat)

async def run_vdbench(vdbench_jar: str):
    proc = await asyncio.create_subprocess_exec(
        "java", "-jar", vdbench_jar,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    await parse_vdbench_stream(proc.stdout)

#TODO дописать работу офлайн
async def run_offline(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File not found: {path}")

    with path.open("rb") as f:
        for line in f:
            decoded = decode_line(line)
            print(decoded)

            await asyncio.sleep(0)


def decode_line(line: bytes) -> str:
    try:
        return line.decode("utf-8").strip()
    except UnicodeDecodeError:
        return line.decode("cp1251", errors="ignore").strip()


def is_valid_line(line: str) -> bool:
    if not line:
        return False
    if "interval" in line.lower():
        return False
    if "i/o" in line.lower():
        return False
    return True

