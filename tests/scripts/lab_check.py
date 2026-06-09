import requests
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def check_health():
    r = requests.get(
        "http://localhost:8080/health",
        timeout=5,
    )

    r.raise_for_status()

    logger.info("[OK] health endpoint")

    return r.json()


def check_metrics():
    r = requests.get(
        "http://localhost:8000/metrics",
        timeout=5,
    )

    r.raise_for_status()

    metrics = r.text

    required = [
        "vdbench_iops",
        "vdbench_latency",
        "vdbench_throughput",
    ]

    for metric in required:
        if metric not in metrics:
            raise RuntimeError(
                f"{metric} not found"
            )

    logger.info("[OK] metrics endpoint")


def check_prometheus():
    r = requests.get(
        "http://localhost:9090/api/v1/query",
        params={
            "query": 'up{job="vdbench"}'
        },
        timeout=5,
    )

    r.raise_for_status()

    result = r.json()

    if not result["data"]["result"]:
        raise RuntimeError(
            "Prometheus has no vdbench target"
        )

    value = result["data"]["result"][0]["value"][1]

    if value != "1":
        raise RuntimeError(
            "Prometheus target is DOWN"
        )

    logger.info("[OK] Prometheus target")


def main():
    check_health()
    check_metrics()
    check_prometheus()

    logger.info("\n")
    logger.info("Smoke test PASSED")


if __name__ == "__main__":
    main()