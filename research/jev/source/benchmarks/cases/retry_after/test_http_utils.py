from http_utils import parse_retry_after

def test_positive_seconds(): assert parse_retry_after("15") == 15
def test_zero_allowed(): assert parse_retry_after("0") == 0
def test_negative_rejected(): assert parse_retry_after("-1") is None
def test_invalid_rejected(): assert parse_retry_after("later") is None
