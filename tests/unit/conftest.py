import pytest

from src.metrics import (
    vdbench_iops,
    vdbench_latency,
    vdbench_throughput
)


@pytest.fixture(autouse=True)
def reset_metrics():
    vdbench_iops.set(0)
    vdbench_latency.set(0)
    vdbench_throughput.set(0)