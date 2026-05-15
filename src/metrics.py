from prometheus_client import Gauge

vdbench_iops = Gauge(
    'vdbench_iops',
    'IOPS'
)

vdbench_latency = Gauge(
    'vdbench_latency',
    'Latency ms'
)

vdbench_throughput = Gauge(
    'vdbench_throughput',
    'Bytes/sec'
)