import pytest

from src.vdbench_runner import (
    parse_header,
    FlatfileSchema, discover_flatfile_schema
)


def test_parse_header():
    line = (
        "tod interval Run Xfersize Threads "
        "Reqrate Rate Rate_std Rate_max "
        "Resp MB/sec"
    )

    schema = parse_header(line)

    assert schema == FlatfileSchema(
        rate_idx=6,
        resp_idx=9,
        mbs_idx=10
    )

def test_parse_header_invalid():
    line = "some random header"

    assert parse_header(line) is None

def test_discover_schema(tmp_path):
    flatfile = tmp_path / "flatfile.html"

    flatfile.write_text(
        "\n".join([
            "random line",
            "another line",
            "tod interval Run Xfersize Threads "
            "Reqrate Rate Rate_std Rate_max "
            "Resp MB/sec",
            "data line"
        ])
    )

    schema = discover_flatfile_schema(flatfile)

    assert schema.rate_idx == 6
    assert schema.resp_idx == 9
    assert schema.mbs_idx == 10

def test_discover_schema_not_found(tmp_path):
    flatfile = tmp_path / "flatfile.html"

    flatfile.write_text(
        "no vdbench header here"
    )

    with pytest.raises(RuntimeError):
        discover_flatfile_schema(flatfile)

def test_real_vdbench_header():
    line = (
        "tod interval Run Xfersize Threads Reqrate "
        "Rate Rate_std Rate_max Resp resp_std "
        "read_pct MB/sec bytes/io"
    )

    schema = parse_header(line)

    assert schema is not None