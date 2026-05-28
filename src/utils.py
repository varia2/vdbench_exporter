from pathlib import Path

def validate_file_arg(arg_name, file_path, optional=False):
    if not optional and not file_path:
        raise ValueError(f"--{arg_name} is required")

    if optional and not file_path:
        return
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"{arg_name} does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"{arg_name} is not a file: {path}")

def validate_args(args):
    if not (1 <= args.port <= 65535):
        raise ValueError(f"Invalid port: {args.port}")

    validate_file_arg("output_file", args.output_file)

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
