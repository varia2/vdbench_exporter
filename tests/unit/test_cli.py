from src.main import parse_args


def test_default_args():
    args = parse_args([
        "--output-file",
        "output/flatfile.html"
    ])

    assert args.output_file == "output/flatfile.html"
    assert args.port == 8000
    assert args.push_gateway is None
    assert args.job_name == "vdbench"
    assert args.polling == 5
    assert args.log_level == "INFO"