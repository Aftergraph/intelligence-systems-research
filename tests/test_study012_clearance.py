"""G12-8: destructive-test clearance tests for ICT-EXP-001 (Issue #52).

Asserts the clearance checklist is intact AND that the verdict is currently
NOT_GRANTED (human approval outstanding), so adversarial instantiation stays
forbidden. Fail-closed by design. No execution, no empirical conclusions.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

CLEAR = Path(workspace) / "data" / "study012_destructive_test_clearance.json"
CLEAR_SHA = Path(workspace) / "data" / "study012_destructive_test_clearance.json.sha256"


@pytest.fixture
def clearance():
    with open(CLEAR) as f:
        return json.load(f)


def test_clearance_sha256_matches():
    h = hashlib.sha256()
    with open(CLEAR, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == CLEAR_SHA.read_text().strip()


def test_clearance_gate_identity(clearance):
    assert clearance["gate"].startswith("G12-8")
    assert clearance["experiment_id"] == "ICT-EXP-001"
    assert clearance["freeze_version"] == "DRAFT"


def test_clearance_checklist_complete(clearance):
    conds = clearance["clearance_conditions"]
    assert len(conds) == 5
    assert all("condition" in c and "met" in c for c in conds)


def test_clearance_fail_closed(clearance):
    """Verdict must be NOT_GRANTED while any condition is unmet — fail closed."""
    unmet = [c for c in clearance["clearance_conditions"] if not c["met"]]
    assert unmet, "checklist must contain at least one unmet condition at this stage"
    assert clearance["clearance_verdict"] == "NOT_GRANTED"
    assert "FORBIDDEN" in clearance["instantiation_forbidden_until"] or "GRANTED" in clearance["instantiation_forbidden_until"]


def test_clearance_human_approval_outstanding(clearance):
    human = [c for c in clearance["clearance_conditions"] if "Human approval" in c["condition"]]
    assert len(human) == 1
    assert human[0]["met"] is False


def test_no_empirical_conclusions(clearance):
    assert "necessary but not sufficient" in clearance["_notice"]
