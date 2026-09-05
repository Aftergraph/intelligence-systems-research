"""Conformance tests for mission-state/1.0 contract.

Validates that the ISR MissionLifecycle FSM and the AIE Mission dataclass both
conform to after-graph-governance/docs/contracts/mission-state/1.0.json.

Run: PYTHONPATH=src python -m pytest tests/test_mission_state_contract.py -q
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

CONTRACT_PATH = Path(__file__).resolve().parent.parent.parent / "after-graph-governance" / "docs" / "contracts" / "mission-state" / "1.0.json"


@pytest.fixture(scope="module")
def contract():
    with open(CONTRACT_PATH) as f:
        return json.load(f)


def test_contract_exists_and_is_valid_json(contract):
    assert contract["$id"].endswith("mission-state/1.0.json")
    assert contract["properties"]["state"]["type"] == "string"


def test_isr_fsm_states_match_contract_enum(contract):
    from state.lifecycle import VALID_LIFECYCLE_STATES
    enum_states = set(contract["properties"]["state"]["enum"])
    assert VALID_LIFECYCLE_STATES == enum_states, (
        f"ISR states {sorted(VALID_LIFECYCLE_STATES)} != contract enum {sorted(enum_states)}"
    )


def test_isr_fsm_transitions_match_contract_state_machine(contract):
    from state.lifecycle import ALLOWED_TRANSITIONS
    sm = contract["mission_state_machine"]
    for state, spec in sm.items():
        expected = set(spec["to"])
        actual = set(ALLOWED_TRANSITIONS.get(state, set()))
        assert actual == expected, (
            f"State {state}: ISR transitions {sorted(actual)} != contract {sorted(expected)}"
        )


def test_aie_mission_dataclass_has_id_and_state(contract):
    from aie_runtime.engine import Mission
    fields = Mission.__dataclass_fields__
    assert "id" in fields, "AIE Mission missing 'id' (required by contract)"
    assert "state" in fields, "AIE Mission missing 'state' (required by contract)"


def test_aie_mission_default_state_is_contract_valid(contract):
    from aie_runtime.engine import Mission
    enum_states = set(contract["properties"]["state"]["enum"])
    # AIE's default should be a valid contract state
    import dataclasses
    state_field = Mission.__dataclass_fields__["state"]
    default = state_field.default if state_field.default is not dataclasses.MISSING else None
    if default is not None:
        assert default in enum_states, f"AIE Mission default state '{default}' not in contract enum"


def test_contract_invariants_present(contract):
    invariants = contract["mission_invariants"]
    assert len(invariants) >= 4
    text = " ".join(invariants)
    assert "Complete != Verified" in text, "ISR Invariant 1 missing"
    assert "Evidence Gated" in text, "ISR Invariant 2 missing"
    assert "TH-12" in text, "AIE revalidation invariant missing"
    assert "HMAC" in text, "AIE persistence invariant missing"
