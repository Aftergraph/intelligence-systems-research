"""
test_assurance_adversarial_script.py
====================================

Pins the output of experiments/test_assurance_adversarial.py
(STUDY-010) as proper pytest tests. The script has 9 attack vectors
that each must be safely rejected (handled_safely=True,
forged_verified=False). The script writes its output to
data/assurance_adversarial_results.json.

This test:
- imports the script's `run_assurance_adversarial_suite` function
- runs it
- pins each vector's result
- pins the on-disk JSON file's content

ponytail: a pytest wrapper is the minimum viable test for an
existing experiment script. We don't rewrite the script's logic;
we just verify it produces the right output and that each
attack vector is contained.
"""

import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

# Add experiments/ to path so we can import the script
experiments_path = os.path.join(workspace, "experiments")
if experiments_path not in sys.path:
    sys.path.insert(0, experiments_path)

# The script is named test_assurance_adversarial.py; importing it
# under a clean name avoids the pytest "imported test file" auto-collection.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "assurance_adversarial_module",
    os.path.join(experiments_path, "test_assurance_adversarial.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


ATTACK_VECTORS = [
    "AGENT_FAKE_RECEIPT",
    "REPLAYED_RECEIPT",
    "STALE_RECEIPT",
    "WRONG_ARTIFACT_HASH",
    "VERIFIER_IMPERSONATION",
    "CONFLICTING_VERIFIERS",
    "EXPIRED_EVIDENCE",
    "MUTATED_EVIDENCE",
    "WRONG_MISSION_VERSION",
]


@pytest.fixture(scope="module")
def adversarial_results():
    """Run the assurance adversarial suite once per module."""
    return mod.run_assurance_adversarial_suite()


def test_attack_vector_count(adversarial_results):
    """There must be exactly 9 attack vectors (the documented STUDY-010 set)."""
    assert len(adversarial_results) == 9, (
        f"Got {len(adversarial_results)} vectors; expected 9. "
        f"Adding/removing vectors requires updating this test."
    )
    actual = [r["vector_id"] for r in adversarial_results]
    assert set(actual) == set(ATTACK_VECTORS), (
        f"Vector ID mismatch. Missing: {set(ATTACK_VECTORS) - set(actual)}. "
        f"Extra: {set(actual) - set(ATTACK_VECTORS)}"
    )


@pytest.mark.parametrize("vector_id", ATTACK_VECTORS)
def test_each_vector_safely_rejected(adversarial_results, vector_id):
    """Each attack vector must be safely rejected (handled_safely=True,
    forged_verified=False)."""
    matching = [r for r in adversarial_results if r["vector_id"] == vector_id]
    assert len(matching) == 1, (
        f"Vector {vector_id} not found or duplicated: {len(matching)} matches"
    )
    r = matching[0]
    assert r["handled_safely"] is True, (
        f"Vector {vector_id} was NOT safely handled. "
        f"rejection_reason={r.get('rejection_reason')!r}. "
        f"forged_verified={r['forged_verified']}."
    )
    assert r["forged_verified"] is False, (
        f"Vector {vector_id} produced a forged VERIFIED state! "
        f"LAB bypass. rejection_reason={r.get('rejection_reason')!r}"
    )


def test_each_vector_has_rejection_reason(adversarial_results):
    """A safely-rejected vector must have a non-empty rejection reason
    (so the audit trail can be reconstructed)."""
    for r in adversarial_results:
        assert r.get("rejection_reason"), (
            f"Vector {r['vector_id']} has no rejection_reason. "
            f"The audit trail must record why the attack was rejected."
        )


def test_results_json_persisted(adversarial_results):
    """The script must persist its results to
    data/assurance_adversarial_results.json."""
    json_path = Path(workspace) / "data" / "assurance_adversarial_results.json"
    assert json_path.exists(), f"Missing {json_path}"
    saved = json.load(open(json_path, encoding="utf-8"))
    assert len(saved) == len(adversarial_results)
    # Pin the persisted result for AGENT_FAKE_RECEIPT (the most security-critical)
    matching = [r for r in saved if r["vector_id"] == "AGENT_FAKE_RECEIPT"]
    assert matching[0]["handled_safely"] is True


def test_zero_compromise_rate(adversarial_results):
    """The assurance adversarial suite must achieve 0% compromise rate
    (this is the STUDY-010 headline result pinned by the audit)."""
    n = len(adversarial_results)
    compromised = sum(1 for r in adversarial_results if r["forged_verified"])
    rate = compromised / n
    assert rate == 0.0, (
        f"Compromise rate {rate:.0%} ({compromised}/{n}) > 0. "
        f"STUDY-010 headline result violated."
    )


def test_latency_recorded_per_vector(adversarial_results):
    """Each vector must record its evaluation latency for the audit trail."""
    for r in adversarial_results:
        assert "latency_ms" in r, (
            f"Vector {r['vector_id']} has no latency_ms field"
        )
        assert r["latency_ms"] >= 0, (
            f"Vector {r['vector_id']} has negative latency: {r['latency_ms']}"
        )
