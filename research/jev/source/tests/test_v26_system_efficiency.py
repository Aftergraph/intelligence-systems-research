from __future__ import annotations

import pytest

from jev_engineering.context_compiler import ContextCandidate
from jev_engineering.system_efficiency import (
    AdaptiveContextBudgeter,
    EarlyExitGate,
    EfficiencyLever,
    FrontierWorkloadProfile,
    RetryBudgetOptimizer,
    RetryCandidate,
    SystemEfficiencyCompiler,
)


def profile() -> FrontierWorkloadProfile:
    return FrontierWorkloadProfile(
        profile_id="p1",
        categories={
            "context_input": 80_000,
            "generation_output": 20_000,
            "frontier_control": 20_000,
            "retry": 20_000,
        },
        verified_outcomes=90,
        missions=100,
    )


def levers() -> list[EfficiencyLever]:
    return [
        EfficiencyLever(
            "context-compiler",
            {"context_input": 0.75},
            quality_retention_lower_bound=0.995,
            evidence_level="benchmarked",
        ),
        EfficiencyLever(
            "jev-control",
            {"frontier_control": 0.95},
            quality_retention_lower_bound=0.998,
            evidence_level="observed",
        ),
        EfficiencyLever(
            "retry-pruning",
            {"retry": 0.75},
            quality_retention_lower_bound=0.995,
            evidence_level="observed",
        ),
        EfficiencyLever(
            "cheap-first-escalation",
            {"context_input": 0.70, "generation_output": 0.70, "retry": 0.70},
            quality_retention_lower_bound=0.99,
            evidence_level="modeled",
        ),
        EfficiencyLever(
            "early-exit",
            {"context_input": 0.20, "generation_output": 0.20, "retry": 0.20},
            quality_retention_lower_bound=0.995,
            evidence_level="modeled",
        ),
    ]


def test_overlapping_token_reductions_compose_multiplicatively() -> None:
    p = FrontierWorkloadProfile("p", {"x": 100})
    a = EfficiencyLever("a", {"x": 0.50})
    b = EfficiencyLever("b", {"x": 0.50})
    plan = SystemEfficiencyCompiler().compile(p, [a, b], target_ratio=4.0)
    assert plan.projected_categories["x"] == 25
    assert plan.projected_ratio == 4.0


def test_quality_bound_does_not_assume_independence() -> None:
    p = FrontierWorkloadProfile("p", {"x": 100})
    a = EfficiencyLever("a", {"x": 0.5}, quality_retention_lower_bound=0.98)
    b = EfficiencyLever("b", {"x": 0.5}, quality_retention_lower_bound=0.97)
    plan = SystemEfficiencyCompiler().compile(
        p, [a, b], target_ratio=2.0, minimum_quality_retention=0.90
    )
    # The union-bound lower bound for both would be 0.95. Compiler may need only one.
    assert plan.quality_retention_lower_bound >= 0.95


def test_compiler_finds_a_10x_region_without_claiming_observation() -> None:
    p = profile()
    compiler = SystemEfficiencyCompiler()
    region = compiler.attainable_region(
        p,
        levers(),
        target_ratio=10.0,
        minimum_quality_retention=0.97,
        minimum_evidence_level="modeled",
    )
    assert region.target_attainable is True
    assert region.maximum_ratio >= 10.0
    plan = compiler.compile(
        p,
        levers(),
        target_ratio=10.0,
        minimum_quality_retention=0.97,
        minimum_evidence_level="modeled",
    )
    assert plan.target_met is True
    assert plan.projected_ratio >= 10.0
    assert "planning model" in plan.truth_boundary


def test_compiler_rejects_unproven_levers_when_evidence_gate_is_observed() -> None:
    p = profile()
    region = SystemEfficiencyCompiler().attainable_region(
        p,
        levers(),
        target_ratio=10.0,
        minimum_quality_retention=0.97,
        minimum_evidence_level="observed",
    )
    assert "cheap-first-escalation" not in region.eligible_levers
    assert "early-exit" not in region.eligible_levers
    assert region.target_attainable is False


def test_context_budgeter_chooses_smallest_high_utility_budget() -> None:
    rows = [
        ContextCandidate("a", "a", 100, relevance=1.0, information_gain=1.0),
        ContextCandidate("b", "b", 100, relevance=0.8, information_gain=1.0),
        ContextCandidate("c", "c", 100, relevance=0.1, information_gain=1.0),
    ]
    plan = AdaptiveContextBudgeter().plan(rows, minimum_utility_retention=0.90)
    assert plan.selected_keys == ("a", "b")
    assert plan.token_budget == 200
    assert plan.retained_utility_fraction >= 0.90
    assert plan.excluded["c"] == "utility_budget"


def test_early_exit_is_fail_closed_for_risk_assurance_and_unverified_paths() -> None:
    gate = EarlyExitGate(max_risk_class="normal", max_assurance_level=2)
    ok = gate.decide(
        predicted_vsr=0.97, required_vsr=0.95, risk_class="normal",
        assurance_level=2, cheap_path_verified=True,
    )
    assert ok.use_frontier is False
    assert gate.decide(
        predicted_vsr=0.99, required_vsr=0.95, risk_class="critical",
        assurance_level=2, cheap_path_verified=True,
    ).use_frontier is True
    assert gate.decide(
        predicted_vsr=0.99, required_vsr=0.95, risk_class="normal",
        assurance_level=3, cheap_path_verified=True,
    ).use_frontier is True
    assert gate.decide(
        predicted_vsr=0.99, required_vsr=0.95, risk_class="normal",
        assurance_level=1, cheap_path_verified=False,
    ).use_frontier is True


def test_retry_budget_optimizer_stops_when_marginal_value_drops() -> None:
    retries = [
        RetryCandidate(1, 0.10, 2_000),  # .05 gain / 1k
        RetryCandidate(2, 0.03, 2_000),  # .015
        RetryCandidate(3, 0.005, 2_000), # .0025 -> stop
        RetryCandidate(4, 0.20, 2_000),  # cannot skip sequence and cherry-pick later retry
    ]
    plan = RetryBudgetOptimizer().plan(
        retries, frontier_token_budget=10_000, min_vsr_gain_per_1k_tokens=0.01
    )
    assert plan.admitted_retries == (1, 2)
    assert plan.frontier_tokens_reserved == 4_000
    assert plan.stop_reason == "marginal_value_too_low"


def test_profile_rejects_overlapping_negative_accounting_inputs() -> None:
    with pytest.raises(ValueError):
        FrontierWorkloadProfile("p", {"bad": -1})
