import os
from pathlib import Path


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


PROMETHEUS_URL = env(
    "TEST_PROMETHEUS_URL",
    "http://localhost:9090"
)

PROMETHEUS_QUERY_URL = env("TEST_PROMETHEUS_QUEUE_URL",
                           "http://localhost:9090/api/v1/query")

PROMETHEUS_CONTAINER_NAME = env("TEST_PROMETHEUS_CONTAINER_NAME",
                                "inspiring_vaughan")

PUSHGATEWAY_URL = env(
    "TEST_PUSHGATEWAY_URL",
    "http://localhost:9091"
)

GRAFANA_URL = env(
    "TEST_GRAFANA_URL",
    "http://localhost:3000"
)

GRAFANA_CONTAINER_NAME = env("TEST_GRAFANA_CONTAINER_NAME",
                             "grafana")

EXPORTER_METRICS_URL = env(
    "TEST_EXPORTER_METRICS_URL",
    "http://localhost:8000/metrics"
)

EXPORTER_HEALTH_URL = env(
    "TEST_EXPORTER_HEALTH_URL",
    "http://localhost:8080/health"
)

EXPORTER_SHUTDOWN_URL = env(
    "TEST_EXPORTER_SHUTDOWN_URL",
    "http://localhost:8080/shutdown"
)

VDBENCH = env("TEST_VDBENCH",
              r"C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat")
WORKLOAD = env("TEST_WORKLOAD",
               "workload.txt")

OUTPUT_DIR = Path(env("TEST_OUTPUT_DIR",
                      "output"))
