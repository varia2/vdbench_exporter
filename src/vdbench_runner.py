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

@dataclass
class FlatfileSchema:
    rate_idx: int
    resp_idx: int
    mbs_idx: int

def parse_header(line: str) -> FlatfileSchema | None:
    columns = line.split()

    if "Rate" not in columns or "Resp" not in columns or "MB/sec" not in columns:
        return None

    return FlatfileSchema(
        rate_idx=columns.index("Rate"),
        resp_idx=columns.index("Resp"),
        mbs_idx=columns.index("MB/sec")
    )

def discover_flatfile_schema(path: Path, timeout: int=20) -> FlatfileSchema:
    start = time.time()

    while time.time() - start < timeout:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:
            for line in f:
                schema = parse_header(line)

                if schema:
                    return schema

    raise RuntimeError(
        f"Could not find VDbench header in {path}"
    )

def parse_metrics_line(
        line: str,
        schema: FlatfileSchema
) -> VdbenchMetrics | None:

    parts = line.split()

    try:
        iops = float(parts[schema.rate_idx])
        latency = float(parts[schema.resp_idx])
        mbs = float(parts[schema.mbs_idx])

        return VdbenchMetrics(
            iops=iops,
            throughput_bytes=mbs * 1024 * 1024,
            latency_ms=latency
        )

    except (ValueError, IndexError):
        return None

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
        shutdown_controller,
        runtime_state,
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
        logger.info("Discovering flatfile schema...")
        schema = discover_flatfile_schema(path)

        logger.info(
            f"SCHEMA: "
            f"rate={schema.rate_idx}, "
            f"resp={schema.resp_idx}, "
            f"mbs={schema.mbs_idx}"
        )

        f.seek(0, 2)
        runtime_state.reader_running = True
        try:
            while not shutdown_controller.is_stopped:
                line = f.readline()

                if not line:
                    await asyncio.sleep(0.2)
                    continue

                line = line.strip()

                metrics = parse_metrics_line(
                    line,
                    schema
                )

                logger.info(f"LINE={line}")

                logger.info(f"PARSED={metrics}")

                if not metrics:
                    continue

                runtime_state.last_raw_line = line
                runtime_state.last_metrics = metrics
                export_metrics(metrics)
                runtime_state.mark_metrics_update()

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
        finally:
            runtime_state.reader_running = False

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

