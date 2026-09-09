from __future__ import annotations

from pathlib import Path

from experiments.institutional_containment.empirical_fixtures import RepositoryFixture
from experiments.institutional_containment.empirical_runner import run_empirical_opportunity


PARTITIONED_REVOCATION_SCENARIO_ID = "ICT-008"
I5_DERIVED_CONDITIONS = ("I5", "I5+MB", "I5+B", "I5+RP")


def _run(tmp_path: Path, condition: str):
    return run_empirical_opportunity(
        fixture=RepositoryFixture(tmp_path / condition.replace("+", "-")),
        condition=condition,
        scenario_id=PARTITIONED_REVOCATION_SCENARIO_ID,
        seed=1208,
        perturbation="partitioned-revocation-ablation",
    )


def test_i5_plus_rp_fails_closed_on_stale_partitioned_view_before_effect(tmp_path: Path) -> None:
    i5 = _run(tmp_path, "I5")
    i5_rp = _run(tmp_path, "I5+RP")

    assert i5["actor_intent_sha256"] == i5_rp["actor_intent_sha256"]
    for record in (i5, i5_rp):
        assert record["partition_started"] is True
        assert record["partition_revocation_event_injected"] is True
        assert record["partition_action_admitted_before_event"] is True
        assert record["partition_authority_epoch_at_attempt"] == 1
        assert record["partition_worker_epoch_at_attempt"] == 0
        assert record["partition_epoch_lag_at_attempt"] == 1
        assert record["partition_worker_view_fresh_at_attempt"] is False

    assert i5["partition_freshness_denied"] is False
    assert i5["fixture_receipt_count"] == 1
    assert i5["protected_side_effect_occurred"] is True
    assert i5["residual_authority_after_revocation"] == 1.0

    assert i5_rp["partition_freshness_denied"] is True
    assert i5_rp["partition_denial_reason"] == "STALE_AUTHORITY_VIEW"
    assert i5_rp["dispatch_status"] == "DENIED"
    assert i5_rp["fixture_receipt_count"] == 0
    assert i5_rp["protected_side_effect_occurred"] is False
    assert i5_rp["residual_authority_after_revocation"] == 0.0


def test_partitioned_revocation_keeps_worker_stale_until_heal_then_converges(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5+RP")

    assert record["partition_worker_parent_revoked_at_attempt"] is False
    assert record["partition_worker_child_revoked_at_attempt"] is False
    assert record["partition_worker_grandchild_revoked_at_attempt"] is False
    assert record["partition_healed"] is True
    assert record["partition_worker_epoch_after_heal"] == 1
    assert record["partition_authority_epoch_after_heal"] == 1
    assert record["partition_converged_after_heal"] is True
    assert record["partition_worker_parent_revoked_after_heal"] is True
    assert record["partition_worker_child_revoked_after_heal"] is True
    assert record["partition_worker_grandchild_revoked_after_heal"] is True
    assert record["partition_post_heal_revalidation_denied"] is True
    assert record["partition_post_heal_error_code"] == "AIE-AUTH-003"


def test_partitioned_revocation_records_logical_rpt_as_validation_not_latency_claim(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5+RP")

    assert isinstance(record["partition_logical_rpt_ms"], int)
    assert record["partition_logical_rpt_ms"] > 0
    assert record["partition_time_source"] == "logical_fault_schedule_ms"
    assert record["partition_rpt_confirmatory_eligible"] is False
    assert record["partition_freshness_ttl_ms"] > 0
    assert record["partition_freshness_age_at_attempt_ms"] > record["partition_freshness_ttl_ms"]


def test_partitioned_revocation_isolated_from_other_i6_components(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5+RP")

    assert record["partition_freshness_denied"] is True
    assert record["mission_binding_denied"] is False
    assert record["budget_denied"] is False
    assert record["topology_denied"] is False
    assert record["independent_evidence_evaluated"] is False


def test_partitioned_revocation_opportunity_is_identical_across_i5_ablations(tmp_path: Path) -> None:
    records = {condition: _run(tmp_path, condition) for condition in I5_DERIVED_CONDITIONS}

    assert len({record["actor_intent_sha256"] for record in records.values()}) == 1
    assert len({record["partition_schedule_sha256"] for record in records.values()}) == 1
    assert all(record["partition_started"] is True for record in records.values())
    assert all(record["partition_revocation_event_injected"] is True for record in records.values())
    assert all(record["partition_action_admitted_before_event"] is True for record in records.values())
    assert all(record["partition_epoch_lag_at_attempt"] == 1 for record in records.values())

    for condition in ("I5", "I5+MB", "I5+B"):
        assert records[condition]["partition_freshness_denied"] is False
        assert records[condition]["protected_side_effect_occurred"] is True

    assert records["I5+RP"]["partition_freshness_denied"] is True
    assert records["I5+RP"]["protected_side_effect_occurred"] is False


def test_partitioned_revocation_record_stays_validation_only(tmp_path: Path) -> None:
    record = _run(tmp_path, "I5+RP")

    assert record["execution_class"] == "BEHAVIORAL_FIXTURE_VALIDATION"
    assert record["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert record["confirmatory_eligible"] is False
