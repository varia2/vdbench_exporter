import asyncio
import argparse
import sys
from pathlib import Path
from prometheus_client import start_http_server
from src.vdbench_runner import run_vdbench

def validate_file_arg(arg_name, file_path, optional=False):
    if not optional and not file_path:
        raise ValueError(f"--{arg_name} is required")

    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"{arg_name} does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"{arg_name} is not a file: {path}")

def validate_args(args):
    # --- port ---
    if not (1 <= args.port <= 65535):
        raise ValueError(f"Invalid port: {args.port}")

    validate_file_arg("vdbench_path", args.vdbench_path)
    validate_file_arg("workload_config", args.workload_config, True)

    if args.mode == "offline":
        validate_file_arg("input_file", args.input_file)

def get_default_lun():
    return str(Path("vdbench_testfile").absolute())


def render_workload(template_path: str) -> str:
    template = Path(template_path).read_text()

    lun = get_default_lun()

    content = template.replace("{LUN}", lun)

    output_path = Path("workload_generated.txt")
    output_path.write_text(content)

    return str(output_path)


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

        asyncio.create_task(run_vdbench(args.vdbench_path, args.workload_file))

    else:
        if not args.input_file:
            raise ValueError("--input-file is required in offline mode")
        return NotImplementedError
        # asyncio.create_task(run_offline(args.input_file))

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())

