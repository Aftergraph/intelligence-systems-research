"""Canonical G12-4: no silent simulation/fallback substitution.

TDD RED: these tests fail until the runner resolves experiment identity
through the G12-9 registry (canonical ICT-EXP-0001) and rejects the
accidental ICT-EXP-001 alias for new execution admissions.
"""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "study012_workload_manifest.json"
REGISTRY = ROOT / "data" / "study012_registry_alignment.json"
MANIFEST_SHA = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

BASE = dict(
    manifest_path=MANIFEST,
    declared_manifest_sha256=MANIFEST_SHA,
    requested_engine="synthetic_in_process_v1",
    actual_engine="synthetic_in_process_v1",
    execution_class="SYNTHETIC_CONFORMANCE_VALID",
    fallback_mode=None,
    confirmatory=False,
)


def _import_runner():
    from experiments.institutional_containment.runner import (
        ExecutionContractError,
        prepare_execution,
    )
    return ExecutionContractError, prepare_execution


def test_canonical_experiment_id_resolved_from_registry():
    """Runner admits the frozen v1.0.0 manifest whose experiment_id is
    ICT-EXP-001 only because the G12-9 registry records it as a valid
    historical alias of canonical ICT-EXP-0001."""
    ExecutionContractError, prepare_execution = _import_runner()
    receipt = prepare_execution(**BASE)
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert reg["canonical_experiment_id"] == "ICT-EXP-0001"
    assert receipt["experiment_id"] == "ICT-EXP-001"
    assert receipt["canonical_experiment_id"] == "ICT-EXP-0001"
    assert receipt["manifest_sha256"] == MANIFEST_SHA
    assert receipt["fallback_used"] is False
    assert receipt["confirmatory_eligible"] is False


@pytest.mark.parametrize("fallback", ["mock", "simulation", "local", "auto"])
def test_any_fallback_mode_is_rejected_fail_closed(fallback):
    ExecutionContractError, prepare_execution = _import_runner()
    with pytest.raises(ExecutionContractError, match="fallback"):
        prepare_execution(**{**BASE, "fallback_mode": fallback})


def test_engine_substitution_is_rejected():
    ExecutionContractError, prepare_execution = _import_runner()
    with pytest.raises(ExecutionContractError, match="engine substitution"):
        prepare_execution(**{**BASE, "actual_engine": "mock_engine_v1"})


def test_manifest_sha_mismatch_is_rejected():
    ExecutionContractError, prepare_execution = _import_runner()
    with pytest.raises(ExecutionContractError, match="manifest"):
        prepare_execution(**{**BASE, "declared_manifest_sha256": "0" * 64})


def test_unknown_execution_class_is_rejected():
    ExecutionContractError, prepare_execution = _import_runner()
    with pytest.raises(ExecutionContractError, match="execution class"):
        prepare_execution(**{**BASE, "execution_class": "UNKNOWN"})


def test_synthetic_engine_cannot_satisfy_confirmatory_request():
    ExecutionContractError, prepare_execution = _import_runner()
    with pytest.raises(ExecutionContractError, match="confirmatory"):
        prepare_execution(**{**BASE, "confirmatory": True})


def test_unregistered_experiment_id_is_rejected(tmp_path):
    """A manifest carrying an experiment_id not in the registry's canonical
    or alias set is rejected — no silent admission of unknown experiments."""
    ExecutionContractError, prepare_execution = _import_runner()
    bad_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad_manifest["experiment_id"] = "ICT-EXP-9999"
    bad_path = tmp_path / "bad_manifest.json"
    bad_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
    bad_sha = hashlib.sha256(bad_path.read_bytes()).hexdigest()
    with pytest.raises(ExecutionContractError, match="identity"):
        prepare_execution(**{**BASE, "manifest_path": bad_path,
                             "declared_manifest_sha256": bad_sha})
