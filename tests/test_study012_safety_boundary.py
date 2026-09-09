import json
import socket
from copy import deepcopy

import pytest

from experiments.institutional_containment.runner import DEFAULT_MANIFEST, run_condition
from experiments.institutional_containment.safety import (
    assert_safe_target,
    validate_manifest_safety,
)
from experiments.institutional_containment.scenarios import SCENARIOS


def _manifest():
    return json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))


def test_every_canonical_scenario_target_passes_synthetic_boundary():
    assert SCENARIOS
    for scenario in SCENARIOS:
        assert assert_safe_target(scenario.synthetic_target) == scenario.synthetic_target


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com/action",
        "http://127.0.0.1:8080/action",
        "file:///etc/passwd",
        "ssh://host/action",
        "sandbox://user:pass@coordination/message-board",
        "sandbox://coordination/../external",
        "sandbox://coordination/%2e%2e/external",
        "sandbox://coordination/message-board?next=https://example.com",
        "sandbox://coordination/message-board#external",
        "sandbox://unknown-namespace/action",
    ],
)
def test_non_synthetic_or_ambiguous_targets_fail_closed(target):
    with pytest.raises(ValueError, match="sandbox|synthetic|target|namespace"):
        assert_safe_target(target)


def test_manifest_safety_requires_all_four_preregistered_fail_closed_fields():
    manifest = _manifest()
    validate_manifest_safety(manifest)

    mutations = (
        ("network", "loopback"),
        ("credentials", "synthetic"),
        ("third_party_targets", "allowed"),
        ("target_scheme", "https://"),
    )
    for field, unsafe_value in mutations:
        changed = deepcopy(manifest)
        changed["safety_boundary"][field] = unsafe_value
        with pytest.raises(ValueError, match="safety boundary"):
            validate_manifest_safety(changed)


def test_runner_rejects_manifest_target_drift_even_when_scenario_ids_match():
    manifest = _manifest()
    manifest["scenarios"][0]["target"] = "https://example.com/not-allowed"

    with pytest.raises(ValueError, match="target"):
        run_condition("I6", manifest=manifest, seed=1206)


def test_runner_creates_no_network_socket(monkeypatch):
    calls = []

    def forbidden_socket(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("STUDY-012 attempted to create a network socket")

    monkeypatch.setattr(socket, "socket", forbidden_socket)
    records = run_condition("I6", seed=1206)

    assert records
    assert calls == []
    assert all(record["synthetic_target"].startswith("sandbox://") for record in records)


def test_manifest_cannot_hide_credentials_inside_safety_metadata():
    manifest = _manifest()
    manifest["safety_boundary"]["credentials"] = {"token": "synthetic-secret"}

    with pytest.raises(ValueError, match="safety boundary"):
        validate_manifest_safety(manifest)
