import os


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


#
# Micro benchmark thresholds
#
MICRO_P95_LATENCY_SEC = env_float(
    "TEST_MICRO_P95_LATENCY_SEC",
    0.25
)

#
# Lab detection latency thresholds
#
LAB_AVG_DETECTION_LATENCY_SEC = env_float(
    "TEST_LAB_AVG_DETECTION_LATENCY_SEC",
    0.20
)

LAB_P95_DETECTION_LATENCY_SEC = env_float(
    "TEST_LAB_P95_DETECTION_LATENCY_SEC",
    0.30
)

#
# Timeouts
#
TRACE_WAIT_TIMEOUT_SEC = env_int(
    "TEST_TRACE_WAIT_TIMEOUT_SEC",
    10
)

LAB_SAMPLE_WAIT_TIMEOUT_SEC = env_int(
    "TEST_LAB_SAMPLE_WAIT_TIMEOUT_SEC",
    60
)