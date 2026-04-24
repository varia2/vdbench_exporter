from pathlib import Path

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
