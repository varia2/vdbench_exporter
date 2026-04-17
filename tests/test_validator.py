import pytest
from src.main import validate_args


class Args:
    def __init__(self, mode, port=8000, vdbench_path=None, input_file=None):
        self.mode = mode
        self.port = port
        self.vdbench_path = vdbench_path
        self.input_file = input_file


def test_invalid_port():
    args = Args(mode="online", port=99999)
    with pytest.raises(ValueError):
        validate_args(args)


def test_missing_vdbench_path():
    args = Args(mode="online")
    with pytest.raises(ValueError):
        validate_args(args)


def test_missing_input_file():
    args = Args(mode="offline")
    with pytest.raises(ValueError):
        validate_args(args)