import os
import re
import sys
import time
import socket
import subprocess
from pathlib import Path

import pytest
import requests


METRIC_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)\s+(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$"
)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_health(health_url: str, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            resp = requests.get(
                health_url,
                timeout=2,
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            time.sleep(0.2)

    raise TimeoutError(
        f"Health endpoint {health_url} did not become ready in time. "
        f"Last error: {last_error}"
    )


def wait_for_metrics_update(health_url: str, timeout: int = 20) -> dict:
    deadline = time.time() + timeout
    last_health = None

    while time.time() < deadline:
        health = wait_for_health(health_url, timeout=2)
        last_health = health

        if health.get("last_metrics_update") is not None:
            return health

        if health.get("offline_completed"):
            return health

        time.sleep(0.2)

    raise TimeoutError(
        f"Exporter did not report metrics update in time. "
        f"Last health: {last_health}"
    )


def read_metrics(metrics_url: str) -> dict[str, float]:
    resp = requests.get(
        metrics_url,
        timeout=5,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()

    result = {}

    for line in resp.text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        m = METRIC_RE.match(line)
        if not m:
            continue

        result[m.group("name")] = float(m.group("value"))

    return result


def wait_for_process_health_or_fail(
    process: subprocess.Popen,
    health_url: str,
    timeout: int = 20,
) -> dict:
    """
    Ждёт, пока поднимется /health.
    Если exporter завершился раньше — падает с stdout/stderr.
    Если health не поднялся, но процесс жив — тоже падает и печатает stdout/stderr.
    """
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        returncode = process.poll()

        if returncode is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise RuntimeError(
                "Offline exporter exited before health became ready.\n"
                f"Return code: {returncode}\n\n"
                f"STDOUT:\n{stdout}\n\n"
                f"STDERR:\n{stderr}"
            )

        try:
            resp = requests.get(
                health_url,
                timeout=2,
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            time.sleep(0.2)

    #
    # timeout, но процесс ещё жив:
    # убиваем его и забираем stdout/stderr, чтобы увидеть, где он завис
    #
    process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)

    raise TimeoutError(
        f"Health endpoint {health_url} did not become ready in time.\n"
        f"Last error: {last_error}\n\n"
        f"STDOUT:\n{stdout}\n\n"
        f"STDERR:\n{stderr}"
    )


@pytest.fixture
def offline_exporter(tmp_path):
    """
    Поднимает exporter в offline-режиме как отдельный процесс.
    Если exporter не стартовал — fixture упадёт сразу с stdout/stderr.
    """
    metrics_port = get_free_port()
    api_port = get_free_port()

    flatfile = Path("tests/data/offline_flatfile.html").resolve()
    trace_file = tmp_path / "offline_trace.jsonl"

    assert flatfile.exists(), f"Missing test flatfile: {flatfile}"

    env = {
        **os.environ,
        "NO_PROXY": "localhost,127.0.0.1",
        "no_proxy": "localhost,127.0.0.1",
    }

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "src.main",
            "--input-file",
            str(flatfile),
            "--stop-mode",
            "api",
            "--port",
            str(metrics_port),
            "--api-port",
            str(api_port),
            "--trace-file",
            str(trace_file),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    health_url = f"http://localhost:{api_port}/health"
    metrics_url = f"http://localhost:{metrics_port}/metrics"

    # ВАЖНО: ждём старта health уже в fixture.
    # Если exporter упал — увидим stdout/stderr сразу здесь.
    health = wait_for_process_health_or_fail(
        process,
        health_url,
        timeout=20
    )

    try:
        yield {
            "process": process,
            "health_url": health_url,
            "metrics_url": metrics_url,
            "trace_file": trace_file,
            "flatfile": flatfile,
            "initial_health": health,
        }
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.integration
def test_offline_mode_exports_last_flatfile_metrics(offline_exporter):
    health_url = offline_exporter["health_url"]
    metrics_url = offline_exporter["metrics_url"]

    health = wait_for_metrics_update(health_url)

    assert health["status"] in ("ok", "degraded")
    assert health["last_metrics_update"] is not None

    metrics = read_metrics(metrics_url)

    assert "vdbench_iops" in metrics
    assert "vdbench_latency" in metrics
    assert "vdbench_throughput" in metrics

    expected_iops = 3000.0
    expected_latency = 3.2
    expected_throughput = 30.5 * 1024 * 1024

    assert metrics["vdbench_iops"] == expected_iops
    assert abs(metrics["vdbench_latency"] - expected_latency) < 0.0001
    assert abs(metrics["vdbench_throughput"] - expected_throughput) < 1