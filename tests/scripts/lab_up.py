import subprocess
import sys
import time
import shutil
from tests.config import (VDBENCH, WORKLOAD, OUTPUT_DIR, GRAFANA_URL, PROMETHEUS_URL,
                          EXPORTER_HEALTH_URL, EXPORTER_METRICS_URL, PROMETHEUS_CONTAINER_NAME,
                          GRAFANA_CONTAINER_NAME)

import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

OUTPUT = OUTPUT_DIR / "flatfile.html"


def ensure_container(name: str):
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Container '{name}' not found")

    if result.stdout.strip() != "true":
        logger.info(f"Starting container {name}")
        subprocess.run(["docker", "start", name], check=True)


def main():
    logger.info("Starting Prometheus...")
    ensure_container(PROMETHEUS_CONTAINER_NAME)

    logger.info("Starting Grafana...")
    ensure_container(GRAFANA_CONTAINER_NAME)

    if OUTPUT_DIR.exists():
        logger.info("Removing previous VDbench output...")
        shutil.rmtree(OUTPUT_DIR)

    logger.info("Starting VDbench...")

    subprocess.Popen(
        [VDBENCH, f"-f{WORKLOAD}"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    logger.info("Waiting for flatfile...")

    for _ in range(60):
        if OUTPUT.exists():
            break

        time.sleep(1)
    else:
        raise RuntimeError("flatfile.html was not created")

    logger.info("Starting exporter...")

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "src.main",
            "--output-file",
            str(OUTPUT),
            "--stop-mode",
            "api",
            "--trace-file",
            "output/exporter_trace.jsonl"
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    logger.info("\n")
    logger.info("Environment started")
    logger.info(f"Prometheus: {PROMETHEUS_URL}")
    logger.info(f"Grafana:    {GRAFANA_URL}")
    logger.info(f"Metrics:    {EXPORTER_METRICS_URL}")
    logger.info(f"Health:     {EXPORTER_HEALTH_URL}")


if __name__ == "__main__":
    main()