"""G12-10: execution window definition tests for ICT-EXP-001 (Issue #52).

Asserts the execution window artifact is intact, references all prior gates,
remains unauthorized (clearance + freeze approval still pending), and defines
rollback/monitoring policy. This artifact DOES NOT grant execution authority.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))

WINDOW = Path(workspace) / "data" / "study012_execution_window.json"
WINDOW_SHA = Path(workspace) / "data" / "study012_execution_window.json.sha256"


@pytest.fixture
def window():
    with open(WINDOW) as f:
        return json.load(f)


def test_window_sha256_matches():
    h = hashlib.sha256()
    with open(WINDOW, "rb") as f:
        h.update(f.read())
    assert h.hexdigest() == WINDOW_SHA.read_text().strip()


def test_window_gate_identity(window):
    assert window["gate"].startswith("G12-10")
    assert window["experiment_id"] == "ICT-EXP-001"
    assert window["window_version"] == "v1.0.0"


def test_all_prior_gates_present(window):
    expected = [f"G12-{i}" for i in range(1, 10)]
    assert window["prior_gates_present"] == expected


def test_execution_not_authorized(window):
    ew = window["execution_window"]
    assert ew["authorized"] is False
    assert ew["earliest_start_utc"] is None
    assert ew["latest_end_utc"] is None


def test_clearance_prerequisite_documented(window):
    ew = window["execution_window"]
    assert "G12-8" in ew["clearance_prerequisite"]
    assert "NOT_GRANTED" in ew["clearance_prerequisite"] or "GRANTED" in ew["clearance_prerequisite"]


def test_freeze_prerequisite_documented(window):
    ew = window["execution_window"]
    assert "G12-9" in ew["freeze_prerequisite"]
    assert "APPROVED" in ew["freeze_prerequisite"]


def test_rollback_and_monitoring_policy(window):
    ew = window["execution_window"]
    assert "halt" in ew["rollback_policy"].lower() or "immediate" in ew["rollback_policy"].lower()
    assert "monitoring" in ew and len(ew["monitoring"]) > 0


def test_no_execution_authority_granted(window):
    notice = window["_notice"]
    assert "DOES NOT grant execution authority" in notice
