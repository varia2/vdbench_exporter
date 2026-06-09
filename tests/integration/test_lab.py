import re
from pathlib import Path

import requests
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
            rf"^{name}\s+([0-9.]+)$",
            text,
            re.MULTILINE
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
    vd_iops, vd_mbs, vd_lat = get_last_vdbench_values(
        "output/flatfile.html"
    )

    exporter = get_exporter_metrics()

    prom_iops = prom_query("vdbench_iops")
    prom_lat = prom_query("vdbench_latency")
    prom_thr = prom_query("vdbench_throughput")

    assert exporter["iops"] == vd_iops

    assert abs(
        exporter["latency"] - vd_lat
    ) < 0.01

    expected_thr = vd_mbs * 1024 * 1024

    assert abs(
        exporter["throughput"] - expected_thr
    ) < 1

    assert prom_iops == exporter["iops"]

    assert abs(
        prom_lat - exporter["latency"]
    ) < 0.01

    assert abs(
        prom_thr - exporter["throughput"]
    ) < 1