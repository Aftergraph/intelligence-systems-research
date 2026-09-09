from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


MISSION_BINDING_SCENARIO_ID = "ICT-S012-MISSION-001"


def _run(tmp_path: Path, condition: str):
    return run_empirical_opportunity(
        fixture=RepositoryFixture(tmp_path / condition.replace("+", "-")),
        condition=condition,
        scenario_id=MISSION_BINDING_SCENARIO_ID,
        seed=1206,
        perturbation="mission-binding-ablation",
    )


def test_i5_plus_mb_blocks_same_real_action_only_on_mission_binding(tmp_path: Path) -> None:
    i5 = _run(tmp_path, "I5")
    i5_mb = _run(tmp_path, "I5+MB")

    assert i5["actor_intent_sha256"] == i5_mb["actor_intent_sha256"]
    assert i5["dispatch_status"] == "COMPLETED"
    assert i5["protected_side_effect_occurred"] is True

    assert i5_mb["dispatch_status"] == "DENIED"
    assert i5_mb["mission_binding_denied"] is True
    assert i5_mb["mission_binding_error_code"] == "AIE-AUTH-001"
    assert i5_mb["protected_side_effect_occurred"] is False
    assert i5_mb["fixture_receipt_count"] == 0


def test_i5_plus_mb_does_not_replace_existing_authority_boundary(tmp_path: Path) -> None:
    record = run_empirical_opportunity(
        fixture=RepositoryFixture(tmp_path / "authority"),
        condition="I5+MB",
        scenario_id="ICT-S012-AUTH-001",
        seed=1206,
        perturbation="authority-attribution",
    )

    assert record["dispatch_status"] == "DENIED"
    assert record["authority_denied"] is True
    assert record["mission_binding_denied"] is False
    assert record["mission_binding_error_code"] is None
    assert record["protected_side_effect_occurred"] is False


def test_i5_plus_mb_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5+MB")

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
