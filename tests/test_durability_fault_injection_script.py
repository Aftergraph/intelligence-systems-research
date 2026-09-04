"""
test_durability_fault_injection_script.py
=========================================

Pins the output of experiments/test_durability_fault_injection.py
(STUDY-009) as proper pytest tests. The script has 7 kill points
and measures recovered_successfully, duplicate_actions, lost_actions,
and state_divergence.

The 7 kill points span the full mission execution lifecycle:
- AFTER_MODEL_RESPONSE, AFTER_TOOL_REQUEST, AFTER_EXTERNAL_EFFECT
- BEFORE_JOURNAL_COMMIT, AFTER_JOURNAL_COMMIT
- DURING_RECOVERY, DURING_PROVIDER_FALLBACK

This test pins:
- 7 kill points covered
- All 7 recover successfully
- Zero duplicate actions (idempotency invariant)
- 0 lost actions in post-journal-commit path
- 1 lost action expected at BEFORE_JOURNAL_COMMIT (pre-commit, by design)
- Zero state divergence
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

experiments_path = os.path.join(workspace, "experiments")
if experiments_path not in sys.path:
    sys.path.insert(0, experiments_path)

spec = importlib.util.spec_from_file_location(
    "durability_fault_injection_module",
    os.path.join(experiments_path, "test_durability_fault_injection.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


KILL_POINTS = [
    "AFTER_MODEL_RESPONSE",
    "AFTER_TOOL_REQUEST",
    "AFTER_EXTERNAL_EFFECT",
    "BEFORE_JOURNAL_COMMIT",
    "AFTER_JOURNAL_COMMIT",
    "DURING_RECOVERY",
    "DURING_PROVIDER_FALLBACK",
]


@pytest.fixture(scope="module")
def durability_results():
    return mod.run_durability_experiment()


def test_seven_kill_points_covered(durability_results):
    assert len(durability_results) == 7
    actual = {r["kill_point"] for r in durability_results}
    assert actual == set(KILL_POINTS)


@pytest.mark.parametrize("kill_point", KILL_POINTS)
def test_each_kill_point_recovers(durability_results, kill_point):
    matching = [r for r in durability_results if r["kill_point"] == kill_point]
    assert len(matching) == 1
    r = matching[0]
    assert r["recovered_successfully"] is True, (
        f"Kill point {kill_point} did NOT recover successfully. "
        f"Duplicate={r['duplicate_actions']}, Lost={r['lost_actions']}, "
        f"Divergence={r['state_divergence']}"
    )


def test_zero_duplicate_actions(durability_results):
    """Idempotency invariant: the recovery path must not produce
    duplicate side effects."""
    for r in durability_results:
        assert r["duplicate_actions"] == 0, (
            f"Kill point {r['kill_point']} produced "
            f"{r['duplicate_actions']} duplicate actions. "
            f"Idempotency invariant violated."
        )


def test_zero_lost_actions_post_commit(durability_results):
    """The durability claim is "zero lost actions in the
    post-journal-commit path". The single BEFORE_JOURNAL_COMMIT
    lost action is expected (pre-commit, by design)."""
    post_commit_kill_points = [
        kp for kp in KILL_POINTS if kp != "BEFORE_JOURNAL_COMMIT"
    ]
    for kp in post_commit_kill_points:
        matching = [r for r in durability_results if r["kill_point"] == kp]
        assert matching[0]["lost_actions"] == 0, (
            f"Kill point {kp} (post-commit) lost "
            f"{matching[0]['lost_actions']} actions. "
            f"Durability invariant violated."
        )


def test_before_journal_commit_lost_action_is_expected(durability_results):
    """The single BEFORE_JOURNAL_COMMIT lost action is by design:
    the process died before fsync, so the in-memory mutation
    was not durably committed. This is the *correct* behavior."""
    matching = [r for r in durability_results if r["kill_point"] == "BEFORE_JOURNAL_COMMIT"]
    assert matching[0]["lost_actions"] == 1, (
        f"Expected 1 lost action at BEFORE_JOURNAL_COMMIT (pre-commit, by design); "
        f"got {matching[0]['lost_actions']}."
    )


def test_zero_state_divergence(durability_results):
    """No kill point should cause state divergence (state-on-disk
    should match state-after-recovery)."""
    for r in durability_results:
        assert r["state_divergence"] is False, (
            f"Kill point {r['kill_point']} caused state divergence."
        )


def test_recovery_latency_recorded(durability_results):
    for r in durability_results:
        assert "recovery_latency_ms" in r
        assert r["recovery_latency_ms"] >= 0


def test_results_persisted_to_json(durability_results):
    json_path = Path(workspace) / "data" / "durability_fault_injection_results.json"
    assert json_path.exists()
    saved = json.load(open(json_path, encoding="utf-8"))
    assert len(saved) == len(durability_results)
    # Pin the headline: zero duplicate actions in persisted data
    total_dup = sum(r["duplicate_actions"] for r in saved)
    assert total_dup == 0
