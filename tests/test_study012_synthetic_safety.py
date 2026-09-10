import socket

import pytest

from experiments.institutional_containment.safety import (
    SafetyBoundaryError,
    canonical_sandbox_target,
    validate_safety_boundary,
    validate_synthetic_target,
)

POLICY = {
    "network": "none",
    "credentials": "none",
    "third_party_targets": "forbidden",
    "target_scheme": "sandbox://",
}


def test_known_workload_gets_canonical_sandbox_target():
    target = canonical_sandbox_target("S12-IC1-I5")
    assert target == "sandbox://study012/S12-IC1-I5"
    assert validate_synthetic_target(target) == "S12-IC1-I5"


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com/x",
        "http://127.0.0.1/x",
        "ssh://host/x",
        "file:///tmp/x",
        "sandbox://user:pass@study012/S12-IC1-I5",
        "sandbox://study012:443/S12-IC1-I5",
        "sandbox://study012/../secret",
        "sandbox://study012/%2e%2e/secret",
        "sandbox://study012/S12-IC1-I5?next=https://example.com",
        "sandbox://study012/S12-IC1-I5#fragment",
        "sandbox://other/S12-IC1-I5",
        "sandbox://study012/UNKNOWN",
    ],
)
def test_non_synthetic_or_smuggled_targets_fail_closed(target):
    with pytest.raises(SafetyBoundaryError):
        validate_synthetic_target(target)


def test_safety_policy_must_be_exact_and_cannot_be_weakened():
    validate_safety_boundary(POLICY)
    for key, value in POLICY.items():
        weakened = dict(POLICY)
        weakened[key] = "allowed"
        with pytest.raises(SafetyBoundaryError, match=key):
            validate_safety_boundary(weakened)


def test_validation_never_opens_a_network_socket(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network socket creation attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    validate_safety_boundary(POLICY)
    for workload in ("S12-IC1-I5", "S12-IC2-I6", "S12-IC6-I6"):
        validate_synthetic_target(canonical_sandbox_target(workload))
