import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests
import logging

from src.vdbench_runner import parse_metrics_line, discover_flatfile_schema

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

flatfile = Path("output/flatfile.html")

initial_lines = len(
    flatfile.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines()
)

pytestmark = pytest.mark.integration

def prom_query(metric):
    session = requests.Session()
    session.trust_env = False

    r = session.get(
        "http://localhost:9090/api/v1/query",
        params={"query": metric},
        timeout=5,
    )

    result = r.json()["data"]["result"]

    return float(result[0]["value"][1])

def get_exporter_metrics():
    session = requests.Session()
    session.trust_env = False

    text = session.get(
        "http://localhost:8000/metrics"
    ).text

    def metric(name):
        m = re.search(
            rf"^{name}\s+([0-9.]+(?:[eE][+-]?\d+)?)$",
            text, re.MULTILINE
        )

        return float(m.group(1))

    return {
        "iops": metric("vdbench_iops"),
        "throughput": metric("vdbench_throughput"),
        "latency": metric("vdbench_latency"),
    }

def get_last_vdbench_values(path):
    lines = Path(path).read_text().splitlines()
    # logger.info(lines)
    for line in reversed(lines):
        if "avg_" in line:
            continue

        parts = line.split()

        if len(parts) < 15:
            continue

        try:
            rate = float(parts[7])
            resp = float(parts[10])
            mbs = float(parts[13])

            return rate, mbs, resp

        except ValueError:
            continue

    raise RuntimeError("No metrics found")

def get_health():
    session = requests.Session()
    session.trust_env = False

    return session.get(
        "http://localhost:8080/health",
        timeout=5
    ).json()

def get_runtime_line():
    session = requests.Session()
    session.trust_env = False

    health = session.get(
        "http://localhost:8080/health"
    ).json()

    return health["last_raw_line"]


def wait_for_metrics_update(timeout=30):
    before = get_health()["last_metrics_update"]

    start = time.time()

    while time.time() - start < timeout:
        current = get_health()["last_metrics_update"]

        if current != before:
            return

        time.sleep(1)

    raise AssertionError(
        "Exporter did not process new metrics"
    )


@dataclass
class MetricsSnapshot:
    timestamp: float

    vd_iops: float
    vd_lat: float
    vd_thr: float

    exp_iops: float
    exp_lat: float
    exp_thr: float

    prom_iops: float
    prom_lat: float
    prom_thr: float

def collect_snapshot():
    vd_iops, vd_mbs, vd_lat = get_last_vdbench_values(
        "output/flatfile.html"
    )

    exporter = get_exporter_metrics()

    return MetricsSnapshot(
        timestamp=time.time(),

        vd_iops=vd_iops,
        vd_lat=vd_lat,
        vd_thr=vd_mbs * 1024 * 1024,

        exp_iops=exporter["iops"],
        exp_lat=exporter["latency"],
        exp_thr=exporter["throughput"],

        prom_iops=prom_query("vdbench_iops"),
        prom_lat=prom_query("vdbench_latency"),
        prom_thr=prom_query("vdbench_throughput"),
    )


def test_health():
    session = requests.Session()
    session.trust_env = False

    r = session.get(
        "http://localhost:8080/health",
        timeout=5
    )

    assert r.status_code == 200


def test_metrics():
    session = requests.Session()
    session.trust_env = False

    r = session.get(
        "http://localhost:8000/metrics",
        timeout=5
    )

    assert r.status_code == 200

    assert "vdbench_iops" in r.text


def test_prometheus_target():
    session = requests.Session()
    session.trust_env = False

    r = session.get(
        "http://localhost:9090/api/v1/query",
        params={
            "query": 'up{job="vdbench"}'
        },
        timeout=5
    )
    prom_query('up{job="vdbench"}')

    result = r.json()["data"]["result"]

    assert result
    assert result[0]["value"][1] == "1"

def test_exporter_trace_consistency():
    flatfile = Path("output/flatfile.html")
    tracefile = Path("output/exporter_trace.jsonl")

    assert flatfile.exists(), (
        f"Missing flatfile: {flatfile}"
    )

    assert tracefile.exists(), (
        f"Missing trace file: {tracefile}"
    )

    schema = discover_flatfile_schema(flatfile)

    logger.info("Reading exporter trace...")

    trace_entries = []

    with tracefile.open(
            encoding="utf-8"
    ) as f:
        for raw in f:
            raw = raw.strip()

            if not raw:
                continue

            trace_entries.append(
                json.loads(raw)
            )

    assert trace_entries, (
        "Trace file is empty"
    )

    logger.info(
        f"Trace entries: {len(trace_entries)}"
    )

    logger.info("Parsing flatfile...")

    flat_lines = []
    parsed_entries = []

    with flatfile.open(
            encoding="utf-8",
            errors="ignore"
    ) as f:

        for raw_line in f:
            line = raw_line.strip()

            metrics = parse_metrics_line(
                line,
                schema
            )

            if not metrics:
                continue

            flat_lines.append(line)

            parsed_entries.append(
                {
                    "line": line,
                    "iops": metrics.iops,
                    "throughput": metrics.throughput_bytes,
                    "latency": metrics.latency_ms,
                }
            )

    assert parsed_entries, (
        "No metrics found in flatfile"
    )

    logger.info(
        f"Flatfile entries: {len(parsed_entries)}"
    )

    trace_lines = [
        entry["line"]
        for entry in trace_entries
    ]

    #
    # Ищем первую строку trace в flatfile
    #
    start_idx = None

    for i, line in enumerate(flat_lines):
        if line == trace_lines[0]:
            start_idx = i
            break

    assert start_idx is not None, (
        "First trace line not found in flatfile"
    )

    logger.info(
        f"Trace starts at flatfile index {start_idx}"
    )

    remaining = flat_lines[start_idx:]

    assert len(remaining) >= len(trace_lines), (
        f"Flatfile tail shorter than trace: "
        f"{len(remaining)} < {len(trace_lines)}"
    )

    #
    # Проверяем отсутствие потерь строк
    #
    line_mismatches = []

    for idx, trace_line in enumerate(trace_lines):

        if remaining[idx] != trace_line:
            line_mismatches.append(
                {
                    "index": idx,
                    "trace": trace_line,
                    "flat": remaining[idx]
                }
            )

    if line_mismatches:
        logger.error(
            f"Line mismatches: "
            f"{len(line_mismatches)}"
        )

        for mismatch in line_mismatches[:10]:
            logger.error(
                f"#{mismatch['index']}\n"
                f"TRACE: {mismatch['trace']}\n"
                f"FLAT : {mismatch['flat']}"
            )

    assert not line_mismatches

    #
    # Выравниваем parsed_entries по найденной позиции
    #
    aligned_parsed = parsed_entries[
        start_idx:start_idx + len(trace_entries)
    ]

    assert len(aligned_parsed) == len(trace_entries)

    metric_mismatches = []

    for idx, (
            trace,
            parsed
    ) in enumerate(
        zip(trace_entries, aligned_parsed)
    ):
        errors = []

        if trace["iops"] != parsed["iops"]:
            errors.append(
                f"IOPS mismatch: "
                f"trace={trace['iops']}, "
                f"parsed={parsed['iops']}"
            )

        if abs(
                trace["latency"]
                - parsed["latency"]
        ) > 0.0001:
            errors.append(
                f"Latency mismatch: "
                f"trace={trace['latency']}, "
                f"parsed={parsed['latency']}"
            )

        if abs(
                trace["throughput"]
                - parsed["throughput"]
        ) > 1:
            errors.append(
                f"Throughput mismatch: "
                f"trace={trace['throughput']}, "
                f"parsed={parsed['throughput']}"
            )

        if errors:
            metric_mismatches.append(
                {
                    "index": idx,
                    "errors": errors,
                    "trace": trace,
                    "parsed": parsed,
                }
            )

    logger.info(
        f"Metric mismatches: "
        f"{len(metric_mismatches)}"
    )

    for mismatch in metric_mismatches[:10]:
        logger.error(
            f"Entry #{mismatch['index']}"
        )

        for err in mismatch["errors"]:
            logger.error(err)

    assert not metric_mismatches