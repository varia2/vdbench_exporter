import re
import time
from pathlib import Path

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

def prom_query(metric):
    r = requests.get(
        "http://localhost:9090/api/v1/query",
        params={"query": metric},
        timeout=5,
    )

    result = r.json()["data"]["result"]

    return float(result[0]["value"][1])

def get_exporter_metrics():
    text = requests.get(
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
    return requests.get(
        "http://localhost:8080/health",
        timeout=5
    ).json()

def get_runtime_line():
    health = requests.get(
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

from dataclasses import dataclass

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
    r = requests.get(
        "http://localhost:8080/health",
        timeout=5
    )

    assert r.status_code == 200


def test_metrics():
    r = requests.get(
        "http://localhost:8000/metrics",
        timeout=5
    )

    assert r.status_code == 200

    assert "vdbench_iops" in r.text


def test_prometheus_target():
    r = requests.get(
        "http://localhost:9090/api/v1/query",
        params={
            "query": 'up{job="vdbench"}'
        },
        timeout=5
    )

    result = r.json()["data"]["result"]

    assert result
    assert result[0]["value"][1] == "1"

def test_metrics_consistency():
    wait_for_metrics_update()

    exporter = get_exporter_metrics()

    health = requests.get(
        "http://localhost:8080/health"
    ).json()

    metrics = health["last_metrics"]

    assert metrics is not None

    assert exporter["iops"] == metrics["iops"]

    assert abs(
        exporter["latency"]
        - metrics["latency"]
    ) < 0.01

    assert abs(
        exporter["throughput"]
        - metrics["throughput"]
    ) < 1
def test_vdbench_exporter_consistency_over_time():
    schema = discover_flatfile_schema(
        Path("output/flatfile.html")
    )

    mismatches = []

    samples = 5

    logger.info(
        f"Collecting {samples} consistency samples"
    )

    for idx in range(samples):

        wait_for_metrics_update()

        health = requests.get(
            "http://localhost:8080/health"
        ).json()

        metrics = health["last_metrics"]
        line = health["last_raw_line"]

        assert metrics is not None

        exporter = get_exporter_metrics()

        logger.info(
            f"[{idx + 1}/{samples}] "
            f"LINE={line}"
        )

        logger.info(
            f"[{idx + 1}/{samples}] "
            f"PARSED="
            f"(iops={metrics["iops"]}, "
            f"lat={metrics["latency"]}, "
            f"thr={metrics["throughput"]}) "
            f"EXPORTER="
            f"(iops={exporter['iops']}, "
            f"lat={exporter['latency']}, "
            f"thr={exporter['throughput']})"
        )

        errors = []

        if exporter["iops"] != metrics["iops"]:
            errors.append(
                f"IOPS mismatch: "
                f"parsed={metrics["iops"]}, "
                f"exporter={exporter['iops']}"
            )

        if abs(
                exporter["latency"]
                - metrics["latency"]
        ) > 0.01:
            errors.append(
                f"Latency mismatch: "
                f"parsed={metrics["latency"]}, "
                f"exporter={exporter['latency']}"
            )

        if abs(
                exporter["throughput"]
                - metrics["throughput"]
        ) > 1:
            errors.append(
                f"Throughput mismatch: "
                f"parsed={metrics["throughput"]}, "
                f"exporter={exporter['throughput']}"
            )

        if errors:
            mismatches.append(
                {
                    "sample": idx,
                    "line": line,
                    "errors": errors
                }
            )

    logger.info(
        f"Samples collected: {samples}"
    )

    logger.info(
        f"Mismatches found: {len(mismatches)}"
    )

    if mismatches:
        for mismatch in mismatches:
            logger.error(
                f"Sample #{mismatch['sample']}"
            )

            logger.error(
                f"Line: {mismatch['line']}"
            )

            for err in mismatch["errors"]:
                logger.error(err)

    assert not mismatches