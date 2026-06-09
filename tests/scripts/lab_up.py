from pathlib import Path
import subprocess
import sys
import time
import shutil

import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

VDBENCH = r"C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat"
WORKLOAD = "workload.txt"

OUTPUT_DIR = Path("output")
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
    ensure_container("inspiring_vaughan")

    logger.info("Starting Grafana...")
    ensure_container("grafana")

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
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    logger.info("\n")
    logger.info("Environment started")
    logger.info("Prometheus: http://localhost:9090")
    logger.info("Grafana:    http://localhost:3000")
    logger.info("Metrics:    http://localhost:8000/metrics")
    logger.info("Health:     http://localhost:8080/health")


if __name__ == "__main__":
    main()