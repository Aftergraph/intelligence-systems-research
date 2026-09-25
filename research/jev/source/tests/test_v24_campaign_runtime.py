from __future__ import annotations

from jev_engineering.campaign_runtime import (
    BenchmarkCostModel,
    TokenPrice,
    build_campaign_report,
)


def _record(condition: str, case: str, repeat: int, *, verified: bool, input_tokens: int, output_tokens: int, decision_input: int, decision_output: int, false_completion: int = 0):
    return {
        "condition": condition,
        "case_id": case,
        "repeat": repeat,
        "status": "verified" if verified else "max_turns",
        "metrics": {
            "completion_claims": 1,
            "false_completion_claims": false_completion,
            "provider_input_tokens": input_tokens,
            "provider_output_tokens": output_tokens,
            "provider_cached_input_tokens": 0,
            "decision_input_tokens": decision_input,
            "decision_output_tokens": decision_output,
        },
    }


def test_cost_model_accounts_for_generator_and_control_plane_tokens():
    model = BenchmarkCostModel(
        generator=TokenPrice(input_per_million=4.0, output_per_million=20.0, cached_input_per_million=0.4),
        decision_by_condition={
            "frontier": TokenPrice(input_per_million=4.0, output_per_million=20.0),
            "jev": TokenPrice(input_per_million=0.042, output_per_million=0.0),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )
    frontier = _record("frontier", "c", 1, verified=True, input_tokens=10_000, output_tokens=1_000, decision_input=2_000, decision_output=500)
    jev = _record("jev", "c", 1, verified=True, input_tokens=10_000, output_tokens=1_000, decision_input=2_000, decision_output=0)
    assert model.record_cost_usd(frontier) > model.record_cost_usd(jev)


def test_campaign_report_pairs_identical_cases_and_reaches_promotion_gate():
    records = []
    for repeat in range(1, 4):
        for case in ("a", "b"):
            records.append(_record("frontier", case, repeat, verified=True, input_tokens=1000, output_tokens=100, decision_input=1000, decision_output=100))
            records.append(_record("jev", case, repeat, verified=True, input_tokens=1000, output_tokens=100, decision_input=100, decision_output=0))
    costs = BenchmarkCostModel(
        generator=TokenPrice(4.0, 20.0, 0.4),
        decision_by_condition={
            "frontier": TokenPrice(4.0, 20.0, 0.4),
            "jev": TokenPrice(0.042, 0.0, 0.042),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )
    report = build_campaign_report(
        records,
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=costs,
        shadow_pairs=2,
        experiment_pairs=2,
        holdout_pairs=2,
        min_holdout_trials=6,
        noninferiority_margin=0.0,
        max_fcr=0.0,
    )
    assert report["paired_missions"] == 6
    assert report["state"] == "promoted"
    assert report["promotion"]["candidate_cpvo"] < report["promotion"]["incumbent_cpvo"]
    assert report["candidate_metrics"]["vsr"] == 1.0
    assert report["candidate_metrics"]["frontier_intelligence_efficiency"] > report["incumbent_metrics"]["frontier_intelligence_efficiency"]
    assert report["frontier_intelligence_efficiency_ratio"] > 1.0


def test_campaign_report_rejects_missing_pair():
    records = [_record("frontier", "a", 1, verified=True, input_tokens=1, output_tokens=1, decision_input=1, decision_output=1)]
    costs = BenchmarkCostModel(generator=TokenPrice(1, 1), decision_by_condition={"frontier": TokenPrice(1, 1), "jev": TokenPrice(1, 1)})
    try:
        build_campaign_report(records, incumbent_condition="frontier", candidate_condition="jev", cost_model=costs, shadow_pairs=1, experiment_pairs=1, holdout_pairs=1, min_holdout_trials=1)
    except ValueError as exc:
        assert "paired" in str(exc)
    else:
        raise AssertionError("expected missing pair to fail closed")
