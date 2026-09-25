from __future__ import annotations

from jev_engineering.campaign_runtime import BenchmarkCostModel, TokenPrice
from jev_engineering.evidence_campaign import (
    EvidenceCampaignPolicy,
    analyze_frontier_efficiency_target,
    evaluate_evidence_campaign,
)


def _record(
    condition: str,
    case: str,
    repeat: int,
    *,
    verified: bool = True,
    provider_input: int = 1000,
    provider_output: int = 100,
    decision_input: int = 100,
    decision_output: int = 0,
    false_completion: int = 0,
    wall_ms: int = 1000,
):
    return {
        "condition": condition,
        "case_id": case,
        "repeat": repeat,
        "status": "verified" if verified else "max_turns",
        "metrics": {
            "completion_claims": 1,
            "false_completion_claims": false_completion,
            "provider_input_tokens": provider_input,
            "provider_output_tokens": provider_output,
            "provider_cached_input_tokens": 0,
            "decision_input_tokens": decision_input,
            "decision_output_tokens": decision_output,
            "wall_time_ms": wall_ms,
        },
    }


def _costs():
    return BenchmarkCostModel(
        generator=TokenPrice(4.0, 20.0, 0.4),
        decision_by_condition={
            "frontier": TokenPrice(4.0, 20.0, 0.4),
            "jev": TokenPrice(0.042, 0.0, 0.042),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )


def test_efficiency_target_reports_when_10x_is_impossible_from_control_plane_only():
    rows = []
    for repeat in range(1, 3):
        for case in ("a", "b"):
            rows += [
                _record("frontier", case, repeat, decision_input=1000, decision_output=100),
                _record("jev", case, repeat, decision_input=100, decision_output=0),
            ]
    analysis = analyze_frontier_efficiency_target(
        rows,
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=_costs(),
        target_ratio=10.0,
    )
    assert analysis["target_ratio"] == 10.0
    assert analysis["control_plane_only_ceiling_ratio"] < 10.0
    assert analysis["target_attainable_by_control_plane_only"] is False
    assert analysis["requires_generator_or_context_reduction"] is True


def test_promotion_uses_holdout_only_and_rejects_bad_holdout():
    # Shadow/experiment are perfect. Holdout candidate fails all pairs.
    rows = []
    pairs = [(1, "a"), (1, "b"), (2, "a"), (2, "b"), (3, "a"), (3, "b")]
    for index, (repeat, case) in enumerate(pairs):
        rows.append(_record("frontier", case, repeat, verified=True, decision_input=1000, decision_output=100))
        rows.append(_record("jev", case, repeat, verified=index < 4, decision_input=100, decision_output=0))
    report = evaluate_evidence_campaign(
        rows,
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=_costs(),
        shadow_pairs=2,
        experiment_pairs=2,
        holdout_pairs=2,
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=2,
            noninferiority_margin=0.0,
            max_fcr=0.0,
            min_fie_ratio=1.0,
            target_fie_ratio=10.0,
            bootstrap_samples=1000,
            bootstrap_seed=7,
        ),
    )
    assert report["holdout"]["candidate"]["vsr"] == 0.0
    assert report["promotion"]["promote"] is False
    assert any("holdout" in reason.lower() or "non-inferiority" in reason.lower() for reason in report["promotion"]["reasons"])


def test_report_exposes_control_plane_tax_and_paired_vsr_delta_interval():
    rows = []
    for repeat in range(1, 4):
        for case in ("a", "b"):
            rows += [
                _record("frontier", case, repeat, decision_input=1000, decision_output=100),
                _record("jev", case, repeat, decision_input=100, decision_output=0),
            ]
    report = evaluate_evidence_campaign(
        rows,
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=_costs(),
        shadow_pairs=2,
        experiment_pairs=2,
        holdout_pairs=2,
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=2,
            noninferiority_margin=0.05,
            max_fcr=0.0,
            min_fie_ratio=1.0,
            target_fie_ratio=10.0,
            bootstrap_samples=1000,
            bootstrap_seed=9,
        ),
    )
    assert report["all"]["incumbent"]["control_plane_token_tax"] > report["all"]["candidate"]["control_plane_token_tax"]
    assert report["all"]["incumbent"]["control_plane_cost_tax"] > report["all"]["candidate"]["control_plane_cost_tax"]
    assert report["holdout"]["paired_vsr_delta"]["estimate"] == 0.0
    assert len(report["holdout"]["paired_vsr_delta"]["bootstrap_ci"]) == 2
    assert report["promotion"]["promote"] is True
