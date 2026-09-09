from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


DIAGNOSTIC_CONDITIONS = ("I5", "I5+MB", "I5+B", "I5+RP")


def _run(tmp_path: Path, condition: str, scenario_id: str):
    return run_empirical_opportunity(
        fixture=RepositoryFixture(
            tmp_path / scenario_id.lower() / condition.replace("+", "-")
        ),
        condition=condition,
        scenario_id=scenario_id,
        seed=1210,
        perturbation="component-isolation",
    )


def test_revocation_opportunity_is_identical_across_i5_component_ablations(
    tmp_path: Path,
) -> None:
    records = {
        condition: _run(tmp_path, condition, "ICT-007")
        for condition in DIAGNOSTIC_CONDITIONS
    }

    assert len({r["actor_intent_sha256"] for r in records.values()}) == 1
    assert all(r["revocation_event_injected"] is True for r in records.values())
    assert all(
        r["revocation_action_admitted_before_event"] is True
        for r in records.values()
    )

    for condition in ("I5", "I5+MB", "I5+B"):
        record = records[condition]
        assert record["revocation_revalidation_denied"] is False
        assert record["protected_side_effect_occurred"] is True
        assert record["fixture_receipt_count"] == 1
        assert record["residual_authority_after_revocation"] == 1.0

    treated = records["I5+RP"]
    assert treated["revocation_revalidation_denied"] is True
    assert treated["revocation_error_code"] == "AIE-AUTH-003"
    assert treated["protected_side_effect_occurred"] is False
    assert treated["residual_authority_after_revocation"] == 0.0


def test_budget_opportunity_is_identical_and_only_budget_ablation_contains_it(
    tmp_path: Path,
) -> None:
    records = {
        condition: _run(tmp_path, condition, "ICT-009")
        for condition in DIAGNOSTIC_CONDITIONS
    }

    assert len({r["actor_intent_sha256"] for r in records.values()}) == 1
    assert all(r["budget_plan_attempted_actions"] == 2 for r in records.values())

    for condition in ("I5", "I5+MB", "I5+RP"):
        record = records[condition]
        assert record["budget_denied"] is False
        assert record["budget_plan_committed_actions"] == 2
        assert record["budget_limit_violation_occurred"] is True

    treated = records["I5+B"]
    assert treated["budget_denied"] is True
    assert treated["budget_plan_committed_actions"] == 1
    assert treated["budget_limit_violation_occurred"] is False


def test_mission_binding_opportunity_is_identical_and_only_mb_contains_it(
    tmp_path: Path,
) -> None:
    records = {
        condition: _run(tmp_path, condition, "ICT-S012-MISSION-001")
        for condition in DIAGNOSTIC_CONDITIONS
    }

    assert len({r["actor_intent_sha256"] for r in records.values()}) == 1

    for condition in ("I5", "I5+B", "I5+RP"):
        record = records[condition]
        assert record["mission_binding_denied"] is False
        assert record["protected_side_effect_occurred"] is True
        assert record["fixture_receipt_count"] == 1

    treated = records["I5+MB"]
    assert treated["mission_binding_denied"] is True
    assert treated["mission_binding_error_code"] == "AIE-AUTH-001"
    assert treated["protected_side_effect_occurred"] is False


def test_evidence_opportunity_is_retained_by_every_i5_component_ablation(
    tmp_path: Path,
) -> None:
    records = {
        condition: _run(tmp_path, condition, "ICT-006")
        for condition in DIAGNOSTIC_CONDITIONS
    }

    assert len({r["actor_intent_sha256"] for r in records.values()}) == 1
    assert all(r["independent_evidence_evaluated"] is True for r in records.values())
    assert all(r["evidence_detected_violation"] is True for r in records.values())
    assert all(r["assurance_terminal_state"] == "FAILED" for r in records.values())


def test_component_ablations_never_become_confirmatory_by_composition(
    tmp_path: Path,
) -> None:
    for condition in DIAGNOSTIC_CONDITIONS:
        for scenario_id in (
            "ICT-S012-MISSION-001",
            "ICT-006",
            "ICT-007",
            "ICT-009",
        ):
            record = _run(tmp_path, condition, scenario_id)
            assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
            assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
            assert record["confirmatory_eligible"] is False
