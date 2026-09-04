"""
test_durability_assurance_pinning.py
=====================================

Pins the STUDY-009 and STUDY-010 empirical results.

STUDY-009 (Durability): 7 kill points, 100% recovery, 0 duplicate
side effects, 0 state divergence. Recovery latency stays bounded.

STUDY-010 (Assurance Adversarial): 9 hostile vectors, 0% compromise
rate (no forged_verified = True), 100% handled_safely.

If any of these numbers drift, the underlying C-012 and C-013 claims
are broken. The tests also pin the kill-point and vector-id
enumeration so a new entry in the testbed forces a review of the
underlying claims.
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


DURABILITY_PATH = "data/durability_fault_injection_results.json"
ASSURANCE_PATH = "data/assurance_adversarial_results.json"

EXPECTED_KILL_POINTS = {
    "AFTER_MODEL_RESPONSE",
    "AFTER_TOOL_REQUEST",
    "AFTER_EXTERNAL_EFFECT",
    "BEFORE_JOURNAL_COMMIT",
    "AFTER_JOURNAL_COMMIT",
    "DURING_RECOVERY",
    "DURING_PROVIDER_FALLBACK",
}

EXPECTED_VECTOR_IDS = {
    "AGENT_FAKE_RECEIPT",
    "REPLAYED_RECEIPT",
    "STALE_RECEIPT",
    "WRONG_ARTIFACT_HASH",
    "VERIFIER_IMPERSONATION",
    "CONFLICTING_VERIFIERS",
    "EXPIRED_EVIDENCE",
    "MUTATED_EVIDENCE",
    "WRONG_MISSION_VERSION",
}


# ---------------------------------------------------------------------------
# STUDY-009: Durability
# ---------------------------------------------------------------------------

def test_durability_results_exist():
    p = Path(workspace) / DURABILITY_PATH
    assert p.exists(), f"{DURABILITY_PATH} missing"


def test_durability_has_7_kill_points():
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    kill_points = {r["kill_point"] for r in data}
    assert kill_points == EXPECTED_KILL_POINTS, (
        f"Kill points {kill_points} != expected {EXPECTED_KILL_POINTS}. "
        f"A new kill point was added or one was renamed; this is a "
        f"protocol-level change requiring a STUDY-009 amendment."
    )


def test_durability_all_recovered():
    """All 7 kill points must show 100% recovery."""
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    failures = [
        (r["kill_point"], r["recovered_successfully"])
        for r in data if not r["recovered_successfully"]
    ]
    assert not failures, (
        f"Durability regression: kill points failed to recover: {failures}. "
        f"This breaks claim C-012 (100% recovery rate)."
    )


def test_durability_no_duplicate_actions():
    """No duplicate side effects across any kill point."""
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    dups = [
        (r["kill_point"], r["duplicate_actions"])
        for r in data if r["duplicate_actions"] > 0
    ]
    assert not dups, (
        f"Durability regression: duplicate side effects at {dups}. "
        f"This breaks claim C-012 (zero duplicate side effects)."
    )


def test_durability_no_state_divergence():
    """No state divergence across any kill point."""
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    divs = [
        (r["kill_point"], r["state_divergence"])
        for r in data if r["state_divergence"]
    ]
    assert not divs, (
        f"Durability regression: state divergence at {divs}. "
        f"This breaks claim C-012 (zero state divergence)."
    )


def test_durability_no_lost_actions_post_commit():
    """No lost actions at any post-journal-commit kill point.

    Kill points BEFORE the journal commit (BEFORE_JOURNAL_COMMIT) may
    legitimately lose the uncommitted action; that is the expected
    durability barrier. All other kill points must show 0 lost
    actions because the journal guarantees the action was durable
    by the time control reaches the kill point.
    """
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    # Kill points where the journal commit HAS happened (post-commit)
    post_commit_points = {
        "AFTER_MODEL_RESPONSE",
        "AFTER_TOOL_REQUEST",
        "AFTER_EXTERNAL_EFFECT",
        "AFTER_JOURNAL_COMMIT",
        "DURING_RECOVERY",
        "DURING_PROVIDER_FALLBACK",
    }
    lost = [
        (r["kill_point"], r["lost_actions"])
        for r in data
        if r["kill_point"] in post_commit_points
        and r["lost_actions"] > 0
    ]
    assert not lost, (
        f"Durability regression: lost actions at post-commit kill "
        f"points: {lost}. Once the journal commit happens, no action "
        f"may be lost. This breaks claim C-012 (zero lost actions "
        f"in the durable path)."
    )


def test_durability_before_journal_commit_may_lose():
    """The BEFORE_JOURNAL_COMMIT kill point may legitimately lose the
    uncommitted action. This is the expected durability barrier.

    We don't require any specific number, but we document the
    behavior so a future change to the kill-point semantics is
    visible.
    """
    data = json.load(open(Path(workspace) / DURABILITY_PATH))
    pre = [r for r in data if r["kill_point"] == "BEFORE_JOURNAL_COMMIT"]
    assert len(pre) == 1, "expected exactly 1 BEFORE_JOURNAL_COMMIT entry"
    # No assertion on the count; just that the row exists and
    # recovered_successfully is True (recovery from the uncommitted
    # state is a separate concern).
    assert pre[0]["recovered_successfully"] is True, (
        "BEFORE_JOURNAL_COMMIT must recover successfully (the recovery "
        "protocol re-runs the action)."
    )


# ---------------------------------------------------------------------------
# STUDY-010: Assurance Adversarial
# ---------------------------------------------------------------------------

def test_assurance_results_exist():
    p = Path(workspace) / ASSURANCE_PATH
    assert p.exists(), f"{ASSURANCE_PATH} missing"


def test_assurance_has_9_vectors():
    data = json.load(open(Path(workspace) / ASSURANCE_PATH))
    vector_ids = {r["vector_id"] for r in data}
    assert vector_ids == EXPECTED_VECTOR_IDS, (
        f"Vector IDs {vector_ids} != expected {EXPECTED_VECTOR_IDS}. "
        f"A new vector was added or one was renamed; this is a "
        f"protocol-level change requiring a STUDY-010 amendment."
    )


def test_assurance_no_forged_verified():
    """Zero forged_verified = True. Logical Assurance Boundary holds."""
    data = json.load(open(Path(workspace) / ASSURANCE_PATH))
    forged = [
        r["vector_id"] for r in data if r.get("forged_verified")
    ]
    assert not forged, (
        f"Assurance boundary breached: forged_verified=True for {forged}. "
        f"This breaks claim C-013 (0% compromise rate)."
    )


def test_assurance_all_handled_safely():
    """All 9 vectors must be handled_safely = True."""
    data = json.load(open(Path(workspace) / ASSURANCE_PATH))
    unhandled = [
        r["vector_id"] for r in data if not r.get("handled_safely")
    ]
    assert not unhandled, (
        f"Assurance regression: vectors handled unsafely: {unhandled}. "
        f"This breaks claim C-013 (100% safe handling)."
    )


def test_assurance_each_vector_has_rejection_reason():
    """Each vector must have a non-empty rejection_reason documenting
    *why* it was rejected. This is the audit trail for the assurance
    boundary."""
    data = json.load(open(Path(workspace) / ASSURANCE_PATH))
    missing = [
        r["vector_id"] for r in data
        if not r.get("rejection_reason") or not r["rejection_reason"].strip()
    ]
    assert not missing, (
        f"Vectors missing rejection_reason: {missing}. "
        f"Each rejection must be documented for the audit trail."
    )
