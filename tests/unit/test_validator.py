import pytest

from src.utils import validate_args


class Args:
    def __init__(
            self,
            output_file="output/flatfile.html",
            port=8000
    ):
        self.output_file = output_file
        self.port = port


def test_valid_args():
    args = Args()

    validate_args(args)


def test_invalid_port_low():
    args = Args(port=0)

    with pytest.raises(ValueError):
        validate_args(args)


def test_invalid_port_high():
    args = Args(port=70000)

    with pytest.raises(ValueError):
        validate_args(args)


def test_missing_output_file():
    args = Args(output_file=None)

    with pytest.raises(ValueError):
        validate_args(args)