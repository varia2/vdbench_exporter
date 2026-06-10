import json
from pathlib import Path

from src.vdbench_runner import VdbenchMetrics


def validate_file_arg(
    arg_name,
    file_path,
    optional=False,
    must_exist=True
):
    if not optional and not file_path:
        raise ValueError(f"--{arg_name} is required")

    if optional and not file_path:
        return

    path = Path(file_path)

    if must_exist and not path.exists():
        raise ValueError(
            f"{arg_name} does not exist: {path}"
        )

def validate_args(args):
    if not (1 <= args.port <= 65535):
        raise ValueError(f"Invalid port: {args.port}")

    validate_file_arg("output_file", args.output_file, must_exist=False)
    validate_file_arg("trace_file", args.trace_file, optional=True, must_exist=False)

def get_default_lun():
    return str(Path("vdbench_testfile").absolute())


def render_workload(template_path: str) -> str:
    template = Path(template_path).read_text()

    lun = get_default_lun()

    content = template.replace("{LUN}", lun)

    output_path = Path("workload_generated.txt")
    output_path.write_text(content)

    return str(output_path)

def get_project_root():
    return Path(__file__).resolve().parent.parent
