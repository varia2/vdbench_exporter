import asyncio
import argparse
from src.utils import validate_args
from prometheus_client import start_http_server
from src.vdbench_runner import follow_vdbench_output, run_offline

from src.logger import setup_logging
import logging

from src.shutdown import ShutdownController
from src.control_api import create_control_api
from src.runtime_state import RuntimeState

import uvicorn

logger = logging.getLogger(__name__)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="VDbench Prometheus exporter")

    parser.add_argument(
        "--output-file",
        required=False,
        default=None,
        help="Path to VDbench flatfile.html (required unless --input-file is specified)"
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

    parser.add_argument(
        "--stop-mode",
        choices=["infinite", "timer", "api"],
        default="infinite"
    )

    parser.add_argument(
        "--duration",
        type=int,
        help="Shutdown timeout in seconds"
    )

    parser.add_argument(
        "--api-port",
        type=int,
        default=8080,
        help="Control API port"
    )

    parser.add_argument(
        "--trace-file",
        type=str,
        help="File path to trace"
    )

    parser.add_argument(
        "--read-polling",
        type=float,
        default=0.05,
        help="How often to poll VDbench flatfile for new lines (seconds)"
    )

    return parser.parse_args(argv)

async def stop_after_timeout(controller, seconds):
    await asyncio.sleep(seconds)
    controller.stop()

async def wait_for_server_started(
        server: uvicorn.Server,
        timeout: float = 5.0
):
    deadline = asyncio.get_running_loop().time() + timeout

    while not server.started:
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(
                "Control API server did not start in time"
            )
        await asyncio.sleep(0.05)

async def start_app(args, controller, runtime_state):
    logger.info(
        f"Starting control API on :{args.api_port} "
        f"(stop_mode={args.stop_mode})"
    )

    api = create_control_api(
        controller,
        runtime_state,
        args.output_file,
        args.stop_mode
    )

    config = uvicorn.Config(
        api,
        host="0.0.0.0",
        port=args.api_port,
        log_level="info"
    )

    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())

    await wait_for_server_started(server)

    if args.input_file:
        asyncio.create_task(
            run_offline(
                file_path=args.input_file,
                runtime_state=runtime_state,
                push_gateway=args.push_gateway,
                job_name=args.job_name,
                polling=args.polling,
                trace_file=args.trace_file,
            )
        )
    else:
        asyncio.create_task(
            follow_vdbench_output(
                args.output_file,
                controller,
                runtime_state,
                push_gateway=args.push_gateway,
                job_name=args.job_name,
                polling=args.polling,
                read_polling=args.read_polling,
                trace_file=args.trace_file,
            )
        )

    if args.stop_mode == "timer":
        logger.info(
            f"Exporter will stop after {args.duration} seconds"
        )

        asyncio.create_task(
            stop_after_timeout(controller, args.duration)
        )


async def main():
    args = parse_args()
    setup_logging(args.log_level)
    validate_args(args)
    logger.info(f"Starting exporter on :{args.port}")
    start_http_server(args.port)

    controller = ShutdownController()
    runtime_state = RuntimeState()

    await start_app(args, controller, runtime_state)

    await controller.wait()

    logger.info("Exporter stopped")


if __name__ == '__main__':
    asyncio.run(main())

