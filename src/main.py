import asyncio
import argparse
from src.utils import validate_args, render_workload
from prometheus_client import start_http_server
from src.vdbench_runner import run_vdbench

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="VDbench Prometheus exporter")

    parser.add_argument(
        "--mode",
        choices=["online", "offline"],
        default="online",
        help="Mode: online (run vdbench) or offline (read file)"
    )

    parser.add_argument(
        "--vdbench-path",
        help="Path to vdbench.bat or vdbench.jar",
        default=r"C:\Users\varia\Downloads\vdbench50407\vdbench50407\vdbench.bat"
    )

    parser.add_argument(
        "--input-file",
        help="Path to vdbench output file (offline mode)"
    )

    parser.add_argument(
        "--workload-config",
        type=str,
        help="Path to vdbench workload configuration file(optional, default will be generated)"
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

    return parser.parse_args(argv)


async def main():
    args = parse_args()
    validate_args(args)
    print(f"Starting exporter on :{args.port}")
    start_http_server(args.port)

    if args.workload_path is None:
        args.workload_path = render_workload("workloads/default.tpl")

    if args.mode == "online":
        if not args.vdbench_path:
            raise ValueError("--vdbench-path is required in online mode")

        asyncio.create_task(run_vdbench(args.vdbench_path,
                                        args.workload_file),
                                        push_gateway=args.push_gateway,
                                        job_name=args.job_name
                                        )

    else:
        if not args.input_file:
            raise ValueError("--input-file is required in offline mode")
        return NotImplementedError
        # asyncio.create_task(run_offline(args.input_file))

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())

