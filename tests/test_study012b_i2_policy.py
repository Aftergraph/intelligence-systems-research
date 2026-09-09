from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


POLICY_SCENARIO = "ICT-S012-POLICY-001"
AUTHORITY_SCENARIO = "ICT-S012-AUTH-001"
EXTERNALIZATION_SCENARIO = "ICT-003"


def _run(tmp_path: Path, condition: str, scenario_id: str):
    fixture = RepositoryFixture(tmp_path / condition.lower() / "repo")
    return run_empirical_opportunity(
        fixture=fixture,
        condition=condition,
        scenario_id=scenario_id,
        seed=12004,
        perturbation="paired-i2",
    )


def test_i2_policy_blocks_real_in_sandbox_operation_before_handler(tmp_path: Path) -> None:
    i1 = _run(tmp_path, "I1", POLICY_SCENARIO)
    i2 = _run(tmp_path, "I2", POLICY_SCENARIO)

    assert i1["actor_intent_sha256"] == i2["actor_intent_sha256"]
    assert i1["attempted"] is True
    assert i2["attempted"] is True

    # I1 proves the operation is physically reachable while remaining inside
    # the sandbox. It must create a real fixture-side effect.
    assert i1["dispatch_status"] == "COMPLETED"
    assert i1["sandbox_denied"] is False
    assert i1["policy_denied"] is False
    assert i1["authority_denied"] is False
    assert i1["fixture_before_sha256"] != i1["fixture_after_sha256"]
    assert i1["fixture_receipt_count"] == 1
    assert i1["protected_side_effect_occurred"] is True

    # I2 adds only policy. The same in-sandbox action must be rejected before
    # the handler mutates fixture state.
    assert i2["dispatch_status"] == "DENIED"
    assert i2["sandbox_denied"] is False
    assert i2["policy_denied"] is True
    assert i2["authority_denied"] is False
    assert i2["fixture_before_sha256"] == i2["fixture_after_sha256"]
    assert i2["fixture_receipt_count"] == 0
    assert i2["protected_side_effect_occurred"] is False
    assert "policy violation" in i2["dispatch_error"].lower()


def test_i2_policy_does_not_silently_add_authority(tmp_path: Path) -> None:
    i1 = _run(tmp_path, "I1", AUTHORITY_SCENARIO)
    i2 = _run(tmp_path, "I2", AUTHORITY_SCENARIO)

    assert i1["actor_intent_sha256"] == i2["actor_intent_sha256"]
    assert i2["dispatch_status"] == "COMPLETED"
    assert i2["sandbox_denied"] is False
    assert i2["policy_denied"] is False
    assert i2["authority_denied"] is False
    assert i2["protected_side_effect_occurred"] is True


def test_i2_retains_i1_sandbox_without_reclassifying_it_as_policy(tmp_path: Path) -> None:
    i1 = _run(tmp_path, "I1", EXTERNALIZATION_SCENARIO)
    i2 = _run(tmp_path, "I2", EXTERNALIZATION_SCENARIO)

    assert i1["actor_intent_sha256"] == i2["actor_intent_sha256"]
    assert i2["dispatch_status"] == "DENIED"
    assert i2["sandbox_denied"] is True
    assert i2["policy_denied"] is False
    assert i2["authority_denied"] is False
    assert i2["protected_side_effect_occurred"] is False


def test_i2_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I2", POLICY_SCENARIO)

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"
