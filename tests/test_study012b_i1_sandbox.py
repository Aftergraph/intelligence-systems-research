from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


EXTERNALIZATION_SCENARIO = "ICT-003"
AUTHORITY_SCENARIO = "ICT-S012-AUTH-001"


def _run(tmp_path: Path, condition: str, scenario_id: str):
    fixture = RepositoryFixture(tmp_path / condition.lower() / "repo")
    return run_empirical_opportunity(
        fixture=fixture,
        condition=condition,
        scenario_id=scenario_id,
        seed=12003,
        perturbation="paired-i1",
    )


def test_i1_sandbox_blocks_real_externalization_before_handler(tmp_path: Path) -> None:
    i0 = _run(tmp_path, "I0", EXTERNALIZATION_SCENARIO)
    i1 = _run(tmp_path, "I1", EXTERNALIZATION_SCENARIO)

    assert i0["actor_intent_sha256"] == i1["actor_intent_sha256"]
    assert i0["attempted"] is True
    assert i1["attempted"] is True

    assert i0["dispatch_status"] == "COMPLETED"
    assert i0["sandbox_denied"] is False
    assert i0["fixture_before_sha256"] != i0["fixture_after_sha256"]
    assert i0["fixture_receipt_count"] == 1
    assert i0["protected_side_effect_occurred"] is True

    assert i1["dispatch_status"] == "DENIED"
    assert i1["sandbox_denied"] is True
    assert i1["fixture_before_sha256"] == i1["fixture_after_sha256"]
    assert i1["fixture_receipt_count"] == 0
    assert i1["protected_side_effect_occurred"] is False
    assert "sandbox boundary" in i1["dispatch_error"].lower()


def test_i1_sandbox_is_not_silent_authority_control(tmp_path: Path) -> None:
    i0 = _run(tmp_path, "I0", AUTHORITY_SCENARIO)
    i1 = _run(tmp_path, "I1", AUTHORITY_SCENARIO)

    assert i0["actor_intent_sha256"] == i1["actor_intent_sha256"]
    assert i1["dispatch_status"] == "COMPLETED"
    assert i1["sandbox_denied"] is False
    assert i1["authority_denied"] is False
    assert i1["protected_side_effect_occurred"] is True


def test_i1_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I1", EXTERNALIZATION_SCENARIO)

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"
