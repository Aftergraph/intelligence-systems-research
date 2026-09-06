import pytest

from experiments.runtime_acceleration.verification.negative_controls import assert_negative_control_failed


def test_negative_control_must_fail_for_expected_assertion():
    with pytest.raises(AssertionError):
        assert_negative_control_failed({"failed": False, "assertion": "native_read"}, "native_read")


def test_negative_control_rejects_wrong_failure_reason():
    with pytest.raises(AssertionError):
        assert_negative_control_failed({"failed": True, "assertion": "search"}, "native_read")


def test_negative_control_accepts_intended_failure():
    assert_negative_control_failed({"failed": True, "assertion": "native_read"}, "native_read")
