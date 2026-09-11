"""G12-9: freeze approval + first-look embargo tests for ICT-EXP-0001 (Issue #52).

Asserts the freeze approval artifact is intact, records all prior gates as
present, keeps embargo locked (no first-look date), and does NOT grant
execution authority. Human approval remains PENDING. No execution, no
empirical conclusions.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

APPROVAL = Path(workspace) / "data" / "study012_freeze_approval.json"
APPROVAL_SHA = Path(workspace) / "data" / "study012_freeze_approval.json.sha256"


@pytest.fixture
def approval():
    with open(APPROVAL) as f:
        return json.load(f)


def test_approval_sha256_matches():
    h = hashlib.sha256()
    with open(APPROVAL, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == APPROVAL_SHA.read_text().strip()


def test_approval_gate_identity(approval):
    assert approval["gate"].startswith("G12-9")
    assert approval["experiment_id"] == "ICT-EXP-0001"
    assert approval["freeze_version"] == "DRAFT"


def test_all_prior_gates_present(approval):
    expected = [f"G12-{i}" for i in range(1, 9)]
    assert approval["prior_gates_present"] == expected


def test_embargo_locked(approval):
    emb = approval["embargo"]
    assert emb["lifted"] is False
    assert emb["first_look_date_utc"] is None
    assert "G12-10" in emb["policy"]


def test_approval_status_pending(approval):
    fa = approval["freeze_approval"]
    assert fa["status"] == "PENDING_HUMAN_APPROVAL"
    assert fa["approved_by"] is None
    assert fa["approved_utc"] is None


def test_checklist_all_met(approval):
    checklist = approval["freeze_approval"]["checklist"]
    assert len(checklist) == 5
    assert all(c["met"] is True for c in checklist)


def test_no_execution_authority_granted(approval):
    notice = approval["_notice"]
    assert "does NOT grant execution authority" in notice
