import asyncio
import re
import time
from pathlib import Path
from dataclasses import dataclass
from prometheus_client import REGISTRY

from prometheus_client import push_to_gateway
from src.metrics import (
    vdbench_iops as iops,
    vdbench_latency as latency,
    vdbench_throughput as throughput
)

import logging

logger = logging.getLogger(__name__)

METRICS_RE = re.compile(
    r"(?P<iops>\d+)\s+(?P<mbs>\d+\.?\d*)\s+(?P<lat>\d+\.?\d*)"
)

@dataclass
class VdbenchMetrics:
    iops: float
    throughput_bytes: float
    latency_ms: float

def parse_metrics_line(line: str) -> VdbenchMetrics | None:
    if not is_valid_line(line):
        return None

    match = METRICS_RE.search(line)

    if not match:
        return None

    return VdbenchMetrics(
        iops=float(match.group("iops")),
        throughput_bytes=float(match.group("mbs")) * 1024 * 1024,
        latency_ms=float(match.group("lat"))
    )

def export_metrics(metrics: VdbenchMetrics):
    iops.set(metrics.iops)
    throughput.set(metrics.throughput_bytes)
    latency.set(metrics.latency_ms)

def maybe_push_metrics(
        push_gateway: str | None,
        job_name: str
):
    if push_gateway:
        push_metrics(push_gateway, job_name)

async def follow_vdbench_output(
        file_path: str,
        push_gateway=None,
        job_name="vdbench",
        polling=5
):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"VDbench output file not found: {file_path}"
        )

    logger.info(f"Following VDbench output: {file_path}")

    last_push = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                await asyncio.sleep(0.2)
                continue

            line = line.strip()

            metrics = parse_metrics_line(line)

            if not metrics:
                continue

            export_metrics(metrics)

            logger.debug(
                f"IOPS={metrics.iops}, "
                f"THR={metrics.throughput_bytes}, "
                f"LAT={metrics.latency_ms}"
            )

            if push_gateway and time.time() - last_push > polling:
                maybe_push_metrics(push_gateway, job_name)
                last_push = time.time()

                logger.info(
                    f"Pushing metrics to {push_gateway}, "
                    f"job={job_name}"
                )

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
    push_to_gateway(gateway, job=job, registry=REGISTRY)


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

