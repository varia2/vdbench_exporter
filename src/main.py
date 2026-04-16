import asyncio
import argparse
import os
from pathlib import Path

from src.vdbench_runner import start_http_server, run_vdbench

def validate_args(args):
    # --- port ---
    if not (1 <= args.port <= 65535):
        raise ValueError(f"Invalid port: {args.port}")

    # --- mode checks ---
    if args.mode == "online":
        if not args.vdbench_path:
            raise ValueError("--vdbench-path is required in online mode")

        path = Path(args.vdbench_path)

        if not path.exists():
            raise ValueError(f"vdbench path does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"vdbench path is not a file: {path}")

    elif args.mode == "offline":
        if not args.input_file:
            raise ValueError("--input-file is required in offline mode")

        path = Path(args.input_file)

        if not path.exists():
            raise ValueError(f"input file does not exist: {path}")

        if not path.is_file():
            raise ValueError(f"input file is not a file: {path}")


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

    if args.mode == "online":
        if not args.vdbench_path:
            raise ValueError("--vdbench-path is required in online mode")

        asyncio.create_task(run_vdbench(args.vdbench_path))

    else:
        if not args.input_file:
            raise ValueError("--input-file is required in offline mode")
        return NotImplementedError
        # asyncio.create_task(run_offline(args.input_file))

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())

