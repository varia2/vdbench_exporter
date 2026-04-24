from prometheus_client import Gauge, CollectorRegistry

# Метрики для режима c пушем в Prometheus
registry = CollectorRegistry()

vdbench_iops = Gauge('vdbench_iops', 'IOPS', registry=registry)
vdbench_latency = Gauge('vdbench_latency', 'Latency ms', registry=registry)
vdbench_throughput = Gauge('vdbench_throughput', 'Bytes/sec', registry=registry)
