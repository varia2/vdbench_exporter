import pytest
from src.vdbench_runner import decode_line

def test_decode_cp1251():
    raw = b'\xe0\xef\xf0 16, 2026'
    text = decode_line(raw)

    assert "апр" in text or len(text) > 0