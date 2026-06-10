import requests
import logging
import subprocess

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def stop_exporter():
    try:
        session = requests.Session()
        session.trust_env = False

        r = session.post(
            "http://localhost:8080/shutdown",
            timeout=5,
        )

        logger.info(r.json())

    except Exception as e:
        logger.info(
            f"Exporter already stopped: {e}"
        )


def stop_container(name):

    logger.info(f"Stopping {name}")

    res = subprocess.run(
        ["docker", "stop", name],
        check=False,
        capture_output=True,
        text=True
    )

    if res.returncode != 0:
        logger.error(res.stdout)
        logger.error(res.stderr)


def main():
    stop_exporter()

    stop_container("inspiring_vaughan")
    stop_container("grafana")

    logger.info("Environment stopped")


if __name__ == "__main__":
    main()