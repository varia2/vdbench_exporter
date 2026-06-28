import asyncio
import json
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

from src.remote_write import remote_write, remote_write_batch

logger = logging.getLogger(__name__)


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

@dataclass
class OfflineRecord:
    line: str
    metrics: VdbenchMetrics
    file_mtime: float

def parse_header(line: str) -> FlatfileSchema | None:
    columns = line.split()
    columns_lower = [c.lower() for c in columns]

    if "rate" not in columns_lower or "resp" not in columns_lower or "mb/sec" not in columns_lower:
        return None

    return FlatfileSchema(
        rate_idx=columns_lower.index("rate"),
        resp_idx=columns_lower.index("resp"),
        mbs_idx=columns_lower.index("mb/sec")
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
        schema: FlatfileSchema | None
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

def trace_metrics(
        trace_file: str,
        line: str,
        metrics: VdbenchMetrics,
        file_mtime : float,
):
    if not trace_file:
        return

    with open(
            trace_file,
            "a",
            encoding="utf-8"
    ) as f:
        json.dump(
            {
                "line": line,
                "processed_at": time.time(),

                "flatfile_mtime": file_mtime,

                "iops": metrics.iops,
                "throughput": metrics.throughput_bytes,
                "latency": metrics.latency_ms
            },
            f
        )

        f.write("\n")

def process_metrics_line(
        line: str,
        schema: FlatfileSchema,
        runtime_state,
        trace_file: str | None = None,
        file_mtime: float | None = None,
) -> bool:
    metrics = parse_metrics_line(line, schema)

    if not metrics:
        return False

    runtime_state.last_raw_line = line
    runtime_state.last_metrics = metrics

    export_metrics(metrics)
    runtime_state.mark_metrics_update()

    logger.debug(
        f"IOPS={metrics.iops}, "
        f"THR={metrics.throughput_bytes}, "
        f"LAT={metrics.latency_ms}"
    )

    if trace_file:
        trace_metrics(
            trace_file=trace_file,
            line=line,
            metrics=metrics,
            file_mtime=file_mtime if file_mtime is not None else time.time()
        )

    return True

def apply_metrics(
        line: str,
        metrics: VdbenchMetrics,
        runtime_state,
        trace_file: str | None = None,
        file_mtime: float | None = None,
):
    export_metrics(metrics)

    runtime_state.last_raw_line = line
    runtime_state.last_metrics = metrics
    runtime_state.mark_metrics_update(
        raw_line=line,
        metrics=metrics
    )

    if trace_file:
        trace_metrics(
            trace_file=trace_file,
            line=line,
            metrics=metrics,
            file_mtime=file_mtime if file_mtime is not None else time.time()
        )

async def follow_vdbench_output(
        file_path: str,
        shutdown_controller,
        runtime_state,
        trace_file: str | None = None,
        push_gateway: str | None = None,
        job_name: str = "vdbench",
        polling: int = 5,
        read_polling: float = 0.05,
        schema: FlatfileSchema | None = None
):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"VDbench output file not found: {file_path}"
        )

    logger.info(f"Following VDbench output: {file_path}")

    if schema is None:
        logger.info("Discovering flatfile schema...")
        schema: FlatfileSchema = discover_flatfile_schema(path)

    logger.info(
        f"SCHEMA: "
        f"rate={schema.rate_idx}, "
        f"resp={schema.resp_idx}, "
        f"mbs={schema.mbs_idx}"
    )

    last_push = 0
    runtime_state.reader_running = True

    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            # tail mode: идем в конец файла и ждём новые строки
            f.seek(0, 2)

            while not shutdown_controller.is_stopped:
                line = f.readline()

                if not line:
                    await asyncio.sleep(read_polling)
                    continue

                line = line.strip()

                if not line:
                    continue

                file_mtime = path.stat().st_mtime

                logger.info(f"LINE={line}")

                processed = process_metrics_line(
                    line=line,
                    schema=schema,
                    runtime_state=runtime_state,
                    trace_file=trace_file,
                    file_mtime=file_mtime
                )

                logger.info(
                    f"PARSED={'ok' if processed else 'skip'}"
                )

                if not processed:
                    continue

                if push_gateway and time.time() - last_push > polling:
                    maybe_push_metrics(push_gateway, job_name)
                    last_push = time.time()

                    logger.info(
                        f"Pushing metrics to {push_gateway}, "
                        f"job={job_name}"
                    )

    finally:
        runtime_state.reader_running = False

def _read_offline_file_to_queue(
        file_path: str,
        schema: FlatfileSchema | None,
        queue,
        loop,
):
    path = Path(file_path)

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            metrics = parse_metrics_line(line, schema)

            if not metrics:
                continue

            record = OfflineRecord(
                line=line,
                metrics=metrics,
                file_mtime=path.stat().st_mtime,
            )

            loop.call_soon_threadsafe(
                queue.put_nowait,
                record
            )

    loop.call_soon_threadsafe(
        queue.put_nowait,
        None
    )


async def run_offline(
        file_path: str,
        runtime_state,
        push_gateway: str | None = None,
        job_name: str = "vdbench",
        polling: int = 5,
        trace_file: str | None = None,
        schema: FlatfileSchema | None = None,
        prometheus_url: str | None = None,
        offline_step_ms: int = 1000,
        offline_batch_size: int = 100,
):
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File not found: {path}")

    try:
        logger.info(f"Running offline import from {file_path}")

        if schema is None:
            logger.info("Discovering flatfile schema...")
            schema = await asyncio.to_thread(discover_flatfile_schema, path)

        logger.info(
            f"SCHEMA: "
            f"rate={schema.rate_idx}, "
            f"resp={schema.resp_idx}, "
            f"mbs={schema.mbs_idx}"
        )

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        runtime_state.reader_running = True
        runtime_state.offline_completed = False

        last_push = 0
        base_ts_ms = int(time.time() * 1000)
        line_counter = 0
        batch = []

        producer = asyncio.create_task(
            asyncio.to_thread(
                _read_offline_file_to_queue,
                file_path,
                schema,
                queue,
                loop,
            )
        )

        while True:
            item = await queue.get()

            if item is None:
                # Отправляем остаток батча
                if prometheus_url and batch:
                    await asyncio.to_thread(
                        remote_write_batch,
                        prometheus_url,
                        batch,
                        job_name,
                    )
                    logger.info(f"Remote write final batch: {len(batch)} samples")
                break

            apply_metrics(
                line=item.line,
                metrics=item.metrics,
                runtime_state=runtime_state,
                trace_file=trace_file,
                file_mtime=item.file_mtime,
            )

            if prometheus_url:
                ts_sec = (base_ts_ms + line_counter * offline_step_ms) / 1000.0
                batch.append((
                    {
                        "vdbench_iops": item.metrics.iops,
                        "vdbench_latency": item.metrics.latency_ms,
                        "vdbench_throughput": item.metrics.throughput_bytes,
                    },
                    ts_sec,
                ))
                line_counter += 1

                if len(batch) >= offline_batch_size:
                    await asyncio.to_thread(
                        remote_write_batch,
                        prometheus_url,
                        batch,
                        job_name,
                    )
                    logger.info(f"Remote write batch: {len(batch)} samples")
                    batch.clear()

            if push_gateway and time.time() - last_push > polling:
                maybe_push_metrics(push_gateway, job_name)
                last_push = time.time()

        await producer
        logger.info(f"Offline import completed, {line_counter} lines sent to Prometheus")

    except Exception:
        logger.exception("run_offline failed")
        raise

    finally:
        runtime_state.reader_running = False
        runtime_state.offline_completed = True

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

