from src.vdbench_runner import (
    parse_metrics_line,
    FlatfileSchema
)

SCHEMA = FlatfileSchema(
    rate_idx=0,
    mbs_idx=1,
    resp_idx=2
)


def test_parse_valid_line():
    metrics = parse_metrics_line(
        "1000 12.5 0.8",
        SCHEMA
    )

    assert metrics.iops == 1000
    assert metrics.throughput_bytes == 12.5 * 1024 * 1024
    assert metrics.latency_ms == 0.8


def test_parse_invalid_line():
    assert parse_metrics_line(
        "invalid text",
        SCHEMA
    ) is None


def test_parse_empty_line():
    assert parse_metrics_line(
        "",
        SCHEMA
    ) is None