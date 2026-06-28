import snappy
import requests
import logging

logger = logging.getLogger(__name__)


def _encode_varint(value: int) -> bytes:
    bits = value & 0x7F
    value >>= 7
    result = b""
    while value:
        result += bytes([0x80 | bits])
        bits = value & 0x7F
        value >>= 7
    result += bytes([bits])
    return result


def _encode_field(field_number: int, wire_type: int, data: bytes) -> bytes:
    tag = (field_number << 3) | wire_type
    return _encode_varint(tag) + data


def _encode_len(data: bytes) -> bytes:
    return _encode_varint(len(data)) + data


def _encode_string(value: str) -> bytes:
    return _encode_len(value.encode("utf-8"))


def _encode_int64(value: int) -> bytes:
    result = b""
    for _ in range(8):
        result += bytes([value & 0xFF])
        value >>= 8
    return result


def _encode_double(value: float) -> bytes:
    import struct
    return struct.pack("<d", value)


def _build_label(name: str, value: str) -> bytes:
    """Label { name, value }"""
    msg = b""
    msg += _encode_field(1, 2, _encode_string(name))   # name
    msg += _encode_field(2, 2, _encode_string(value))  # value
    return msg


def _build_sample(value: float, timestamp_ms: int) -> bytes:
    """Sample { value, timestamp }"""
    msg = b""
    msg += _encode_field(1, 1, _encode_double(value))       # value (double, wire=1)
    msg += _encode_field(2, 0, _encode_varint(timestamp_ms & 0xFFFFFFFFFFFFFFFF))  # timestamp (int64)
    return msg


def _build_timeseries(labels: dict[str, str], samples: list[tuple[float, int]]) -> bytes:
    """TimeSeries { labels, samples }"""
    msg = b""
    for name, value in labels.items():
        label_bytes = _build_label(name, value)
        msg += _encode_field(1, 2, _encode_len(label_bytes))  # labels

    for value, ts_ms in samples:
        sample_bytes = _build_sample(value, ts_ms)
        msg += _encode_field(2, 2, _encode_len(sample_bytes))  # samples

    return msg


def _build_write_request(timeseries: list[bytes]) -> bytes:
    """WriteRequest { timeseries }"""
    msg = b""
    for ts in timeseries:
        msg += _encode_field(1, 2, _encode_len(ts))
    return msg


def remote_write(
    prometheus_url: str,
    metrics: dict[str, float],
    timestamp: float,
    job: str = "vdbench",
):
    """
    Отправляет метрики в Prometheus remote write API.

    metrics: {"vdbench_iops": 3000.0, ...}
    timestamp: Unix timestamp в секундах (из flatfile)
    """
    timestamp_ms = int(timestamp * 1000)

    timeseries = []
    for metric_name, value in metrics.items():
        labels = {
            "__name__": metric_name,
            "job": job,
        }
        ts_bytes = _build_timeseries(labels, [(value, timestamp_ms)])
        timeseries.append(ts_bytes)

    write_request = _build_write_request(timeseries)
    compressed = snappy.compress(write_request)

    resp = requests.post(
        f"{prometheus_url}/api/v1/write",
        data=compressed,
        headers={
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        },
        timeout=5,
    )

    if resp.status_code not in (200, 204):
        logger.warning(
            f"Remote write failed: {resp.status_code} {resp.text}"
        )
    else:
        logger.debug(
            f"Remote write ok: ts={timestamp_ms}, metrics={list(metrics.keys())}"
        )

def remote_write_batch(
    prometheus_url: str,
    samples: list[tuple[dict[str, float], float]],
    job: str = "vdbench",
):
    """
    Отправляет несколько точек в одном запросе.

    samples: список пар (metrics_dict, timestamp_sec)
    Пример: [
        ({"vdbench_iops": 3000.0, "vdbench_latency": 3.2}, 1716900000.0),
        ({"vdbench_iops": 3100.0, "vdbench_latency": 3.1}, 1716900001.0),
    ]
    """
    timeseries_by_name: dict[str, list[tuple[float, int]]] = {}

    for metrics, timestamp in samples:
        ts_ms = int(timestamp * 1000)
        for metric_name, value in metrics.items():
            if metric_name not in timeseries_by_name:
                timeseries_by_name[metric_name] = []
            timeseries_by_name[metric_name].append((value, ts_ms))

    timeseries = []
    for metric_name, metric_samples in timeseries_by_name.items():
        labels = {
            "__name__": metric_name,
            "job": job,
        }
        ts_bytes = _build_timeseries(labels, metric_samples)
        timeseries.append(ts_bytes)

    write_request = _build_write_request(timeseries)
    compressed = snappy.compress(write_request)

    resp = requests.post(
        f"{prometheus_url}/api/v1/write",
        data=compressed,
        headers={
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        },
        timeout=10,
    )

    if resp.status_code not in (200, 204):
        logger.warning(
            f"Remote write batch failed: {resp.status_code} {resp.text}"
        )
    else:
        logger.debug(
            f"Remote write batch ok: {len(samples)} samples"
        )