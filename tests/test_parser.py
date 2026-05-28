from src.vdbench_runner import (
    parse_metrics_line,
    VdbenchMetrics
)


def test_parse_valid_line():
    line = "1000 12.5 0.8"

    metrics = parse_metrics_line(line)

    assert metrics is not None
    assert metrics.iops == 1000
    assert metrics.throughput_bytes == 12.5 * 1024 * 1024
    assert metrics.latency_ms == 0.8


def test_parse_invalid_line():
    line = "invalid text"

    metrics = parse_metrics_line(line)

    assert metrics is None


def test_parse_header_line():
    line = "interval i/o MB/sec"

    metrics = parse_metrics_line(line)

    assert metrics is None


def test_parse_empty_line():
    metrics = parse_metrics_line("")

    assert metrics is None