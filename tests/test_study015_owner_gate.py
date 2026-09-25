import json
from pathlib import Path

import pytest

from experiments.study015.owner_gate import OwnerGateError, assert_owner_approved

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data" / "study015_owner_gate.json"


def test_repository_gate_is_intentionally_not_approved():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    assert gate["status"] == "NOT_APPROVED"
    with pytest.raises(OwnerGateError):
        assert_owner_approved(gate)


def test_explicit_complete_owner_gate_passes():
    gate = {
        "status":"APPROVED",
        "authorize_confirmatory_execution":True,
        "approved_by":"Jonas Abde",
        "approved_at":"2026-09-25T00:00:00Z",
        "protocol_sha256":"a"*64,
    }
    assert_owner_approved(gate)
