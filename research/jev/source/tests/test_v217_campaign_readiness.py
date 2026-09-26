from __future__ import annotations

import json
from pathlib import Path

from jev_engineering.campaign_readiness import (
    CompletionReadinessPolicy,
    analyze_completion_readiness,
    plan_powered_campaign,
    recommend_turn_budgets,
)

ROOT = Path(__file__).resolve().parents[1]


def _v216_records():
    evidence = json.loads((ROOT / "evidence/v216-lineage-proof/evidence.json").read_text())
    return evidence["execution"]["records"], evidence


def test_v216_live_proof_is_not_completion_ready() -> None:
    records, _ = _v216_records()
    report = analyze_completion_readiness(
        records,
        incumbent_condition="qwen-frontier-control",
        candidate_condition="qwen-jev-control",
        policy=CompletionReadinessPolicy(),
    )
    assert report.ready is False
    assert report.paired_missions == 1
    assert any("requires at least 3" in reason for reason in report.reasons)
    assert all(c.verified_rate == 0.0 for c in report.conditions)
    assert all(c.max_turn_rate == 1.0 for c in report.conditions)
    assert all(c.baseline_valid is False for c in report.conditions)


def test_v216_invalid_baseline_blocks_turn_budget_inflation() -> None:
    records, _ = _v216_records()
    report = analyze_completion_readiness(records, incumbent_condition="qwen-frontier-control", candidate_condition="qwen-jev-control")
    recs = recommend_turn_budgets(report, current_max_turns=4)
    assert len(recs) == 2
    assert all(r.action == "repair_verifier_first" for r in recs)
    assert all(r.recommended_max_turns == 4 for r in recs)


def test_power_plan_is_fail_closed_until_readiness_and_preregistration() -> None:
    records, evidence = _v216_records()
    report = analyze_completion_readiness(records, incumbent_condition="qwen-frontier-control", candidate_condition="qwen-jev-control")
    plan = plan_powered_campaign(
        readiness=report,
        baseline_vsr_assumption=0.90,
        live_lineage_proven=evidence["live_provider_measurement"],
        pricing_reviewed=False,
        preregistered=False,
    )
    assert plan.executable is False
    assert "completion_readiness_not_met" in plan.blockers
    assert "pricing_not_reviewed" in plan.blockers
    assert "campaign_not_preregistered" in plan.blockers
    assert plan.holdout_pairs >= 20
    assert plan.total_pairs > plan.holdout_pairs


def test_ready_synthetic_pilot_can_produce_executable_preregistered_plan() -> None:
    rows=[]
    for repeat in range(1,4):
        for condition in ("frontier","jev"):
            rows.append({
                "condition":condition,"case_id":"clamp","repeat":repeat,"status":"verified",
                "baseline_verification_exit_code":1,
                "metrics":{"verifier_runs":1,"completion_claims":1,"false_completion_claims":0},
            })
    report=analyze_completion_readiness(rows,incumbent_condition="frontier",candidate_condition="jev")
    assert report.ready is True
    plan=plan_powered_campaign(readiness=report,baseline_vsr_assumption=.9,live_lineage_proven=True,pricing_reviewed=True,preregistered=True)
    assert plan.executable is True
    assert plan.blockers == ()