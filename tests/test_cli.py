from src.main import parse_args


def test_default_args():
    args = parse_args([])

    assert args.mode == "online"
    assert args.port == 8000