from __future__ import annotations

import pytest

from jev_engineering.campaign_runtime import BenchmarkCostModel, TokenPrice
from jev_engineering.evidence_campaign import EvidenceCampaignPolicy
from jev_engineering.paired_holdout import PairedHoldoutCampaignRunner, PairedMission


def _missions():
    return [
        PairedMission("a", 1, "shadow", {"prompt": "A"}),
        PairedMission("b", 1, "experiment", {"prompt": "B"}),
        PairedMission("c", 1, "holdout", {"prompt": "C"}),
        PairedMission("d", 1, "holdout", {"prompt": "D"}),
    ]


def _costs():
    return BenchmarkCostModel(
        generator=TokenPrice(4.0, 20.0, 0.4),
        decision_by_condition={
            "frontier": TokenPrice(4.0, 20.0, 0.4),
            "jev": TokenPrice(0.042, 0.0, 0.042),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )


def _record(verified=True, *, provider_input=1000, decision_input=100):
    return {
        "status": "verified" if verified else "unverified",
        "metrics": {
            "completion_claims": 1,
            "false_completion_claims": 0,
            "provider_input_tokens": provider_input,
            "provider_output_tokens": 100,
            "decision_input_tokens": decision_input,
            "decision_output_tokens": 0,
            "wall_time_ms": 1000,
        },
    }


def test_runner_hides_phase_from_callback_and_binds_identical_payload():
    seen = []
    runner = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev", seed=7)

    def run(inp, condition):
        assert not hasattr(inp, "phase")
        seen.append((inp.case_id, condition, inp.payload_sha256))
        return _record(provider_input=1000 if condition == "frontier" else 100, decision_input=100)

    result = runner.run(missions=_missions(), run_condition=run)
    assert len(result.records) == 8
    for case in {row[0] for row in seen}:
        digests = {row[2] for row in seen if row[0] == case}
        assert len(digests) == 1
    assert result.holdout_pairs == 2
    assert result.live_provider_measurement is False


def test_counterbalanced_order_is_deterministic_for_seed():
    r1 = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev", seed=11)
    r2 = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev", seed=11)
    out1 = r1.run(missions=_missions(), run_condition=lambda i, c: _record())
    out2 = r2.run(missions=_missions(), run_condition=lambda i, c: _record())
    assert out1.pair_execution_order == out2.pair_execution_order


def test_holdout_evaluator_rejects_bad_candidate_holdout_even_when_development_passes():
    runner = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev", seed=3)

    def run(inp, condition):
        candidate_bad = condition == "jev" and inp.case_id in {"c", "d"}
        return _record(
            verified=not candidate_bad,
            provider_input=1000 if condition == "frontier" else 100,
            decision_input=1000 if condition == "frontier" else 100,
        )

    result = runner.run(missions=_missions(), run_condition=run)
    report = result.evaluate(
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=_costs(),
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=2,
            noninferiority_margin=0.0,
            max_fcr=0.0,
            min_fie_ratio=1.0,
            target_fie_ratio=10.0,
            bootstrap_samples=100,
            bootstrap_seed=7,
        ),
    )
    assert report["shadow"]["candidate"]["vsr"] == 1.0
    assert report["experiment"]["candidate"]["vsr"] == 1.0
    assert report["holdout"]["candidate"]["vsr"] == 0.0
    assert report["promotion"]["promote"] is False


def test_missing_metrics_fail_closed():
    runner = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev")
    with pytest.raises(ValueError, match="missing metrics"):
        runner.run(
            missions=[PairedMission("a", 1, "holdout", {})],
            run_condition=lambda i, c: {"status": "verified", "metrics": {}},
        )


def test_noncontiguous_phase_schedule_rejected():
    runner = PairedHoldoutCampaignRunner(incumbent_condition="frontier", candidate_condition="jev")
    missions = [
        PairedMission("a", 1, "holdout", {}),
        PairedMission("b", 1, "experiment", {}),
    ]
    with pytest.raises(ValueError, match="contiguous"):
        runner.run(missions=missions, run_condition=lambda i, c: _record())
