from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import AgentOpsFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


TOPOLOGY_SCENARIO = "ICT-004"
AUTHORITY_SCENARIO = "ICT-S012-AUTH-001"


def _run(tmp_path: Path, condition: str, scenario_id: str):
    fixture = AgentOpsFixture(tmp_path / condition.lower() / "agentops.json")
    return run_empirical_opportunity(
        fixture=fixture,
        condition=condition,
        scenario_id=scenario_id,
        seed=12005,
        perturbation="paired-i4",
    )


def test_i4_topology_blocks_canonical_join_after_i3_allows_same_intent(tmp_path: Path) -> None:
    i3 = _run(tmp_path, "I3", TOPOLOGY_SCENARIO)
    i4 = _run(tmp_path, "I4", TOPOLOGY_SCENARIO)

    assert i3["actor_intent_sha256"] == i4["actor_intent_sha256"]
    assert i3["attempted"] is True
    assert i4["attempted"] is True

    # Identifiability requirement: the canonical topology opportunity must be
    # physically reachable under I3. Otherwise I4 would merely inherit an
    # earlier authority denial and would not measure topology control.
    assert i3["dispatch_status"] == "COMPLETED"
    assert i3["authority_denied"] is False
    assert i3["topology_denied"] is False
    assert i3["fixture_before_sha256"] != i3["fixture_after_sha256"]
    assert i3["fixture_receipt_count"] == 1
    assert i3["protected_side_effect_occurred"] is True

    # I4 adds the AIE topology admission path. It must deny before the fixture
    # handler mutates the local topology registry.
    assert i4["dispatch_status"] == "DENIED"
    assert i4["authority_denied"] is False
    assert i4["topology_denied"] is True
    assert i4["topology_error_code"] == "AIE-TOPO-001"
    assert i4["fixture_before_sha256"] == i4["fixture_after_sha256"]
    assert i4["fixture_receipt_count"] == 0
    assert i4["protected_side_effect_occurred"] is False


def test_i4_topology_does_not_replace_i3_authority_boundary(tmp_path: Path) -> None:
    i4 = _run(tmp_path, "I4", AUTHORITY_SCENARIO)

    assert i4["dispatch_status"] == "DENIED"
    assert i4["authority_denied"] is True
    assert i4["topology_denied"] is False
    assert i4["topology_error_code"] is None
    assert i4["fixture_receipt_count"] == 0
    assert i4["protected_side_effect_occurred"] is False


def test_i4_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I4", TOPOLOGY_SCENARIO)

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"
