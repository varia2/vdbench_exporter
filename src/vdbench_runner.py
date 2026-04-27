import asyncio
import re
import time
from pathlib import Path

from prometheus_client import push_to_gateway
from src.metrics import (
    vdbench_iops as iops,
    vdbench_latency as latency,
    vdbench_throughput as throughput,
    registry
)

# Чтение iops, mbs, latency
METRICS_RE = re.compile(
    r"(?P<iops>\d+)\s+(?P<mbs>\d+\.?\d*)\s+(?P<lat>\d+\.?\d*)"
)

async def parse_vdbench_stream(stream, push_gateway=None, job_name="vdbench", polling=5):
    last_push = 0
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

        iops_val = float(match.group("iops"))
        mbs_val = float(match.group("mbs"))
        lat_val = float(match.group("lat"))

        iops.set(iops_val)
        throughput.set(mbs_val * 1024 * 1024)
        latency.set(lat_val)

        if push_gateway and time.time() - last_push > polling:
            push_metrics(push_gateway, job_name)
            last_push = time.time()

async def run_vdbench(vdbench_jar: str, workload_file: str, push_gateway=None, job_name="vdbench", polling=5):
    proc = await asyncio.create_subprocess_exec(
        "java", "-jar", vdbench_jar,
        "-f", workload_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    await parse_vdbench_stream(proc.stdout, push_gateway, job_name, polling)

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

def push_metrics(gateway: str, job: str) -> None:
    push_to_gateway(gateway, job=job, registry=registry)


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

