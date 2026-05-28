import asyncio
import argparse
from src.utils import validate_args
from prometheus_client import start_http_server
from src.vdbench_runner import follow_vdbench_output

from src.logger import setup_logging
import logging

logger = logging.getLogger(__name__)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="VDbench Prometheus exporter")

    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to VDbench flatfile.html"
    )

    parser.add_argument(
        "--input-file",
        help="Path to vdbench output file (offline mode)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Prometheus port"
    )

    parser.add_argument(
        "--push-gateway",
        type=str,
        help="Pushgateway URL (e.g. http://localhost:9091)"
    )

    parser.add_argument(
        "--job-name",
        type=str,
        default="vdbench",
        help="Prometheus job name for push"
    )

    parser.add_argument(
        "--polling",
        type=int,
        default=5,
        help="Polling time in seconds"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )

    return parser.parse_args(argv)

async def start_app(args):
    asyncio.create_task(
        follow_vdbench_output(
            args.output_file,
            push_gateway=args.push_gateway,
            job_name=args.job_name,
            polling=args.polling
        )
    )


async def main():
    args = parse_args()
    setup_logging(args.log_level)
    validate_args(args)
    logger.info(f"Starting exporter on :{args.port}")
    start_http_server(args.port)

    await start_app(args)

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())

