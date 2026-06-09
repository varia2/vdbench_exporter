from src.vdbench_runner import (
    export_metrics,
    VdbenchMetrics
)

from src.metrics import (
    vdbench_iops,
    vdbench_latency,
    vdbench_throughput
)


def test_export_metrics():
    metrics = VdbenchMetrics(
        iops=500,
        throughput_bytes=1024,
        latency_ms=1.5
    )

    export_metrics(metrics)

    assert vdbench_iops._value.get() == 500
    assert vdbench_throughput._value.get() == 1024
    assert vdbench_latency._value.get() == 1.5