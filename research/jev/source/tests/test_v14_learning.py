from __future__ import annotations

import pytest

from jev_engineering.intelligence_fabric import CompetenceGraph, CompetenceKey
from jev_engineering.learning import (
    CounterfactualReplay,
    DecisionObservation,
    DecisionDistillationCompiler,
    LearningCandidate,
    LearningRatchet,
    LearningState,
    PromotionPolicy,
    ShadowObservation,
)


def test_learning_ratchet_requires_ordered_evidence_before_promotion() -> None:
    candidate = LearningCandidate(
        candidate_id="cand-1",
        decision_family="safe_to_run",
        incumbent_strategy="frontier-sol",
        candidate_strategy="jev-safe",
    )
    ratchet = LearningRatchet(candidate)

    with pytest.raises(RuntimeError, match="illegal learning transition"):
        ratchet.transition(LearningState.PROMOTED)

    for state in (
        LearningState.REPLAYED,
        LearningState.SHADOWED,
        LearningState.EXPERIMENTAL,
        LearningState.HOLDOUT_VERIFIED,
        LearningState.PROMOTED,
    ):
        ratchet.transition(state)
    assert ratchet.candidate.state is LearningState.PROMOTED


def test_promotion_policy_requires_noninferior_vsr_and_lower_cpvo() -> None:
    policy = PromotionPolicy(vsr_noninferiority_margin=0.02, max_fcr=0.01)
    candidate = LearningCandidate(
        candidate_id="cand-2",
        decision_family="scope",
        incumbent_strategy="frontier-sol",
        candidate_strategy="jev-scope",
        state=LearningState.HOLDOUT_VERIFIED,
        replay_runs=100,
        shadow_runs=100,
        experimental_runs=100,
        holdout_runs=100,
        incumbent_vsr=0.94,
        candidate_vsr=0.93,
        candidate_fcr=0.0,
        incumbent_cpvo=0.20,
        candidate_cpvo=0.05,
    )
    decision = policy.evaluate(candidate)
    assert decision.promote is True

    worse = candidate.with_metrics(candidate_vsr=0.89)
    assert policy.evaluate(worse).promote is False


def test_distillation_compiler_emits_candidate_only_after_repeated_verified_observations() -> None:
    compiler = DecisionDistillationCompiler(min_observations=4, min_teacher_vsr=0.75)
    for i, ok in enumerate([True, True, True]):
        compiler.observe(DecisionObservation(
            observation_id=f"o{i}",
            decision_family="scope",
            teacher_strategy="frontier-sol",
            teacher_decision="src/a.py",
            verified_outcome=ok,
            estimated_cost_usd=0.01,
        ))
    assert compiler.compile_candidate(
        decision_family="scope",
        candidate_strategy="jev-scope",
        candidate_cost_usd=0.0001,
    ) is None

    compiler.observe(DecisionObservation(
        observation_id="o3",
        decision_family="scope",
        teacher_strategy="frontier-sol",
        teacher_decision="src/a.py",
        verified_outcome=True,
        estimated_cost_usd=0.01,
    ))
    candidate = compiler.compile_candidate(
        decision_family="scope",
        candidate_strategy="jev-scope",
        candidate_cost_usd=0.0001,
    )
    assert candidate is not None
    assert candidate.incumbent_strategy == "frontier-sol"
    assert candidate.candidate_strategy == "jev-scope"
    assert candidate.state is LearningState.OBSERVED
    assert candidate.incumbent_vsr == 1.0
    assert candidate.candidate_cpvo < candidate.incumbent_cpvo


def test_counterfactual_replay_uses_only_observed_shadow_outcomes() -> None:
    replay = CounterfactualReplay()
    replay.record(ShadowObservation(
        decision_id="d1",
        incumbent_strategy="frontier-sol",
        candidate_strategy="jev",
        incumbent_decision="allow",
        candidate_decision="allow",
        incumbent_verified_outcome=True,
        candidate_verified_outcome=True,
        incumbent_cost_usd=0.10,
        candidate_cost_usd=0.001,
    ))
    replay.record(ShadowObservation(
        decision_id="d2",
        incumbent_strategy="frontier-sol",
        candidate_strategy="jev",
        incumbent_decision="block",
        candidate_decision="allow",
        incumbent_verified_outcome=True,
        candidate_verified_outcome=None,
        incumbent_cost_usd=0.10,
        candidate_cost_usd=0.001,
    ))

    result = replay.evaluate(candidate_strategy="jev")
    assert result.total_shadow_runs == 2
    assert result.observable_counterfactual_runs == 1
    assert result.coverage == 0.5
    assert result.candidate_vsr == 1.0
    assert result.candidate_cpvo == pytest.approx(0.001)


def test_promoted_learning_can_update_competence_graph_only_from_observed_holdout() -> None:
    graph = CompetenceGraph()
    key = CompetenceKey(strategy_id="jev-scope", task_family="scope")
    candidate = LearningCandidate(
        candidate_id="cand-3",
        decision_family="scope",
        incumbent_strategy="frontier-sol",
        candidate_strategy="jev-scope",
        state=LearningState.PROMOTED,
        holdout_runs=3,
        holdout_successes=2,
    )
    LearningRatchet(candidate).promote_competence(graph, key)
    estimate = graph.estimate(key)
    assert estimate.observations == 3
    assert estimate.mean == pytest.approx((1 + 2) / (2 + 3))


def test_intelligence_fabric_can_learn_observed_competence_and_persist(tmp_path) -> None:
    from jev_engineering.intelligence_fabric import FrontierTokenBudget, IntelligenceBid, IntelligenceFabric

    graph_path = tmp_path / "competence.json"
    graph = CompetenceGraph()
    fabric = IntelligenceFabric(
        bids=[IntelligenceBid(
            strategy_id="jev-scope",
            source="jev",
            capabilities=("control",),
            predicted_vsr=0.95,
            estimated_cost_usd=0.001,
            estimated_latency_ms=10,
            metadata={"competence_key": {"task_family": "scope"}},
        )],
        frontier_budget=FrontierTokenBudget(input_limit=0, output_limit=0),
        competence_graph=graph,
        competence_graph_path=graph_path,
    )
    bid = fabric.select(capability="control", required_vsr=0.9)
    fabric.record_outcome(bid, success=True)
    assert graph_path.exists()
    key = CompetenceKey(strategy_id="jev-scope", task_family="scope")
    assert graph.estimate(key).observations == 1


def test_agent_records_verified_generation_outcome_into_competence_graph(tmp_path) -> None:
    from jev_engineering.agent import CodingAgent
    from jev_engineering.decisions import DecisionEngine
    from jev_engineering.intelligence_fabric import FrontierTokenBudget, IntelligenceBid, IntelligenceFabric
    from jev_engineering.model_registry import ModelRegistry
    from jev_engineering.providers.mock import ScriptedProviderFactory
    from jev_engineering.testing import ScriptedDecisionBackend
    from jev_engineering.types import AgentStatus

    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )
    decisions = ScriptedDecisionBackend([
        {"answers": {"f0": {"type": "score", "score": 4, "confidence": 1}, "f1": {"type": "score", "score": 4, "confidence": 1}}},
        {"answers": {"destructive": {"type": "noul", "noul": 0.01}, "needs_human": {"type": "noul", "noul": 0.01}}},
        {"answers": {"destructive": {"type": "noul", "noul": 0.01}, "needs_human": {"type": "noul", "noul": 0.01}}},
        {"answers": {"done": {"type": "noul", "noul": 0.99}, "judgeable": {"type": "noul", "noul": 0.99}}},
    ])
    registry = ModelRegistry.from_dict({"models": {
        "mock": {"provider": "mock", "model": "m", "tier": "frontier", "transport": "mock"}
    }})
    graph = CompetenceGraph()
    fabric = IntelligenceFabric(
        bids=[IntelligenceBid(
            strategy_id="mock-generation",
            source="frontier",
            capabilities=("generation",),
            predicted_vsr=0.95,
            estimated_cost_usd=0.01,
            estimated_latency_ms=10,
            frontier_input_tokens=100,
            frontier_output_tokens=20,
            metadata={
                "model_alias": "mock",
                "competence_key": {"task_family": "coding", "mission_phase": "execute"},
            },
        )],
        frontier_budget=FrontierTokenBudget(input_limit=1000, output_limit=200),
        competence_graph=graph,
    )
    provider = ScriptedProviderFactory(turns=[
        {"tool_calls": [{"id": "1", "name": "write_file", "arguments": {"path": "calc.py", "content": "def add(a, b):\n    return a + b\n"}}]},
        {"tool_calls": [{"id": "2", "name": "run_command", "arguments": {"command": "python -m pytest -q"}}]},
        {"text": "done"},
    ])
    result = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        intelligence_fabric=fabric,
        generation_required_vsr=0.9,
        max_turns=8,
    ).run("Fix add")
    assert result.status is AgentStatus.VERIFIED
    key = CompetenceKey(strategy_id="mock-generation", task_family="coding", mission_phase="execute")
    assert graph.estimate(key).observations == 1
    assert result.metrics["fabric_competence_outcomes_recorded"] == 1


def test_config_resolves_competence_graph_path_relative_to_config_file(tmp_path) -> None:
    from jev_engineering.config import AppConfig

    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "fabric.yaml"
    config_path.write_text('''
intelligence_fabric:
  enabled: true
  competence_graph_path: state/competence.json
  frontier_budget:
    input_tokens: 0
    output_tokens: 0
  strategies:
    - id: jev-scope
      source: jev
      capabilities: [control]
      predicted_vsr: 0.95
      estimated_cost_usd: 0.001
      estimated_latency_ms: 10
      competence_key:
        task_family: scope
models: {}
''', encoding="utf-8")
    fabric = AppConfig.load(config_path).intelligence_fabric()
    assert fabric is not None
    bid = fabric.select(capability="control", required_vsr=0.9)
    fabric.record_outcome(bid, success=True)
    assert (config_dir / "state" / "competence.json").exists()
