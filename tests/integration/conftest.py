import subprocess
import sys
import time

import pytest
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def lab():
    print("\n=== Starting test lab ===")

    result = subprocess.run(
        [sys.executable, "tests/scripts/lab_up.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"lab_up failed:\n{result.stdout}\n{result.stderr}"
        )

    # Даем Prometheus немного времени на первый scrape
    time.sleep(10)

    yield

    print("\n=== Stopping test lab ===")

    subprocess.run(
        [sys.executable, "tests/scripts/lab_down.py"],
        check=False
    )