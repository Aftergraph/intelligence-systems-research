"""G12-3: I0–I6 condition-conformance tests for ICT-EXP-001 (Issue #52).

Static conformance declarations against data/study012_condition_ladder.json.
No execution, no empirical conclusions. Falsification-first: the primary
comparison is I6 vs I5, and I6-vs-I0 alone is rejected as support.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

LADDER = Path(workspace) / "data" / "study012_condition_ladder.json"
LADDER_SHA = Path(workspace) / "data" / "study012_condition_ladder.json.sha256"


@pytest.fixture
def ladder():
    with open(LADDER) as f:
        return json.load(f)


def test_ladder_sha256_matches():
    h = hashlib.sha256()
    with open(LADDER, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == LADDER_SHA.read_text().strip()


def test_ladder_gate_identity(ladder):
    assert ladder["gate"].startswith("G12-3")
    assert ladder["experiment_id"] == "ICT-EXP-001"
    assert ladder["freeze_version"] == "DRAFT"


def test_ladder_has_seven_ordered_conditions(ladder):
    ids = [c["id"] for c in ladder["conditions"]]
    assert ids == ["I0", "I1", "I2", "I3", "I4", "I5", "I6"]


def test_mechanisms_accumulate_monotonically(ladder):
    prev: set = set()
    for cond in ladder["conditions"]:
        cur = set(cond["cumulative_mechanisms"])
        assert prev <= cur, f"{cond['id']} drops a mechanism"
        prev = cur


def test_i0_empty_i6_full(ladder):
    conds = {c["id"]: c for c in ladder["conditions"]}
    assert conds["I0"]["cumulative_mechanisms"] == []
    assert set(conds["I6"]["cumulative_mechanisms"]) == {
        "sandbox", "policy", "authority", "topology",
        "evidence", "mission", "budget", "revocation",
    }


def test_primary_comparison_is_i6_vs_i5(ladder):
    assert ladder["primary_comparison"].startswith("I6")
    assert "I5" in ladder["primary_comparison"]
    rules = " ".join(ladder["conformance_rules"])
    assert "not merely over I0" in rules


def test_null_hypothesis_present(ladder):
    assert "no material containment benefit" in ladder["null_hypothesis"]


def test_no_empirical_conclusions(ladder):
    assert "No execution" in ladder["_freeze_notice"]
    assert "no empirical conclusions" in ladder["_freeze_notice"]
