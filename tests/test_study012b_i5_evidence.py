from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


TRAJECTORY_TAMPER_SCENARIO = "ICT-006"


def _run(tmp_path: Path, condition: str):
    fixture = RepositoryFixture(tmp_path / condition.lower() / "repo")
    return run_empirical_opportunity(
        fixture=fixture,
        condition=condition,
        scenario_id=TRAJECTORY_TAMPER_SCENARIO,
        seed=12006,
        perturbation="paired-i5",
    )


def test_i5_detects_real_trajectory_tampering_without_pretending_to_prevent_it(
    tmp_path: Path,
) -> None:
    i4 = _run(tmp_path, "I4")
    i5 = _run(tmp_path, "I5")

    assert i4["actor_intent_sha256"] == i5["actor_intent_sha256"]
    assert i4["attempted"] is True
    assert i5["attempted"] is True

    # Evidence is a post-execution assurance boundary. The underlying hostile
    # mutation must remain behaviorally real in both arms.
    assert i4["dispatch_status"] == "COMPLETED"
    assert i5["dispatch_status"] == "COMPLETED"
    assert i4["protected_side_effect_occurred"] is True
    assert i5["protected_side_effect_occurred"] is True
    assert i4["fixture_before_sha256"] != i4["fixture_after_sha256"]
    assert i5["fixture_before_sha256"] != i5["fixture_after_sha256"]
    assert i4["fixture_receipt_count"] == 1
    assert i5["fixture_receipt_count"] == 1

    # I4 has no independent evidence layer. I5 adds the real assurance path and
    # must detect the violation from observer evidence, not from the transcript.
    assert i4["independent_evidence_evaluated"] is False
    assert i4["evidence_detected_violation"] is False
    assert i4["assurance_terminal_state"] is None

    assert i5["independent_evidence_evaluated"] is True
    assert i5["evidence_detected_violation"] is True
    assert i5["assurance_verified"] is False
    assert i5["assurance_terminal_state"] == "RECOVERING"
    assert i5["independent_evidence_receipt_count"] == 1
    assert i5["independent_evidence_source"] == "fixture_observer"
    assert i5["assurance_principal"] == "AssurancePrincipal"


def test_i5_assurance_does_not_reclassify_prior_control_denials_as_evidence(
    tmp_path: Path,
) -> None:
    fixture = RepositoryFixture(tmp_path / "repo")
    record = run_empirical_opportunity(
        fixture=fixture,
        condition="I5",
        scenario_id="ICT-003",
        seed=12006,
        perturbation="paired-i5-sandbox",
    )

    # I1 sandbox remains the mechanism that blocks externalization. I5 evidence
    # must not retroactively claim credit for a handler that never executed.
    assert record["dispatch_status"] == "DENIED"
    assert record["sandbox_denied"] is True
    assert record["policy_denied"] is False
    assert record["authority_denied"] is False
    assert record["topology_denied"] is False
    assert record["protected_side_effect_occurred"] is False
    assert record["independent_evidence_evaluated"] is False
    assert record["evidence_detected_violation"] is False


def test_i5_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5")

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"
