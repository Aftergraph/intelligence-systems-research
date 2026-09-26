from __future__ import annotations

import pytest

from jev_engineering.intelligence_fabric import (
    CompetenceGraph,
    CompetenceKey,
    FrontierTokenBudget,
    IntelligenceBid,
    IntelligenceFabric,
    NoAdmissibleIntelligence,
)


def _bid(
    strategy_id: str,
    *,
    source: str,
    vsr: float,
    cost: float,
    latency: float,
    uncertainty: float = 0.05,
    risk: float = 0.05,
    input_tokens: int = 0,
    output_tokens: int = 0,
    capabilities: tuple[str, ...] = ("control",),
) -> IntelligenceBid:
    return IntelligenceBid(
        strategy_id=strategy_id,
        source=source,
        capabilities=capabilities,
        predicted_vsr=vsr,
        estimated_cost_usd=cost,
        estimated_latency_ms=latency,
        uncertainty=uncertainty,
        risk=risk,
        frontier_input_tokens=input_tokens,
        frontier_output_tokens=output_tokens,
    )


def test_same_bid_contract_routes_rule_jev_and_frontier_by_requirement() -> None:
    fabric = IntelligenceFabric(
        bids=[
            _bid("rule", source="rule", vsr=0.82, cost=0.0, latency=1),
            _bid("jev", source="jev", vsr=0.94, cost=0.0001, latency=60),
            _bid(
                "frontier",
                source="frontier",
                vsr=0.99,
                cost=0.15,
                latency=1200,
                input_tokens=4000,
                output_tokens=800,
            ),
        ],
        frontier_budget=FrontierTokenBudget(input_limit=10_000, output_limit=2_000),
    )

    assert fabric.select(capability="control", required_vsr=0.80).strategy_id == "rule"
    assert fabric.select(capability="control", required_vsr=0.90).strategy_id == "jev"
    assert fabric.select(capability="control", required_vsr=0.98).strategy_id == "frontier"


def test_frontier_budget_fails_closed_without_consuming_on_rejected_bid() -> None:
    budget = FrontierTokenBudget(input_limit=1000, output_limit=200)
    fabric = IntelligenceFabric(
        bids=[
            _bid(
                "frontier",
                source="frontier",
                vsr=0.99,
                cost=0.10,
                latency=100,
                input_tokens=1200,
                output_tokens=100,
            )
        ],
        frontier_budget=budget,
    )

    with pytest.raises(NoAdmissibleIntelligence, match="frontier budget"):
        fabric.select(capability="control", required_vsr=0.90)
    assert budget.input_used == 0
    assert budget.output_used == 0


def test_budget_consumption_is_explicit_and_never_charged_for_jev() -> None:
    budget = FrontierTokenBudget(input_limit=5000, output_limit=1000)
    jev = _bid("jev", source="jev", vsr=0.95, cost=0.0001, latency=40)
    frontier = _bid(
        "frontier",
        source="frontier",
        vsr=0.99,
        cost=0.15,
        latency=1000,
        input_tokens=2000,
        output_tokens=400,
    )

    budget.consume(jev)
    assert budget.input_used == 0
    assert budget.output_used == 0

    budget.consume(frontier)
    assert budget.input_used == 2000
    assert budget.output_used == 400
    assert budget.remaining == {"input_tokens": 3000, "output_tokens": 600}


def test_competence_graph_updates_posterior_without_collapsing_dimensions() -> None:
    graph = CompetenceGraph(prior_alpha=1.0, prior_beta=1.0)
    python_bugfix = CompetenceKey(
        strategy_id="qwen",
        task_family="bugfix",
        repo="repo-a",
        language="python",
        mission_phase="execute",
        risk_class="normal",
    )
    auth_change = CompetenceKey(
        strategy_id="qwen",
        task_family="auth-change",
        repo="repo-a",
        language="python",
        mission_phase="execute",
        risk_class="high",
    )

    for outcome in [True, True, True, False]:
        graph.observe(python_bugfix, success=outcome)
    graph.observe(auth_change, success=False)

    normal = graph.estimate(python_bugfix)
    auth = graph.estimate(auth_change)
    assert normal.observations == 4
    assert auth.observations == 1
    assert normal.mean > auth.mean
    assert 0 < normal.uncertainty < 1


def test_competence_can_materialize_a_bid_and_change_routing() -> None:
    graph = CompetenceGraph(prior_alpha=1.0, prior_beta=1.0)
    qwen_key = CompetenceKey(strategy_id="qwen", task_family="bugfix")
    sol_key = CompetenceKey(strategy_id="sol", task_family="bugfix")
    for outcome in [True] * 8 + [False]:
        graph.observe(qwen_key, success=outcome)
    for outcome in [True, False, False, False]:
        graph.observe(sol_key, success=outcome)

    qwen = graph.bid(
        qwen_key,
        source="frontier",
        capabilities=("generation",),
        estimated_cost_usd=0.05,
        estimated_latency_ms=400,
        frontier_input_tokens=1000,
        frontier_output_tokens=200,
    )
    sol = graph.bid(
        sol_key,
        source="frontier",
        capabilities=("generation",),
        estimated_cost_usd=0.10,
        estimated_latency_ms=500,
        frontier_input_tokens=1000,
        frontier_output_tokens=200,
    )
    fabric = IntelligenceFabric(
        bids=[qwen, sol],
        frontier_budget=FrontierTokenBudget(input_limit=5000, output_limit=1000),
    )
    selected = fabric.select(capability="generation", required_vsr=0.60)
    assert selected.strategy_id == "qwen"


def test_fabric_reports_frontier_efficiency_inputs() -> None:
    fabric = IntelligenceFabric(
        bids=[_bid("jev", source="jev", vsr=0.95, cost=0.0001, latency=50)],
        frontier_budget=FrontierTokenBudget(input_limit=10_000, output_limit=2_000),
    )
    bid = fabric.select(capability="control", required_vsr=0.90)
    fabric.record_selection(bid)
    metrics = fabric.telemetry()
    assert metrics["selections"] == 1
    assert metrics["frontier_selections"] == 0
    assert metrics["frontier_input_tokens_reserved"] == 0
    assert metrics["frontier_output_tokens_reserved"] == 0


def test_app_config_builds_enabled_fabric_from_yaml(tmp_path) -> None:
    from jev_engineering.config import AppConfig

    config = tmp_path / "fabric.yaml"
    config.write_text(
        '''
intelligence_fabric:
  enabled: true
  required_vsr:
    generation: 0.91
  frontier_budget:
    input_tokens: 120000
    output_tokens: 25000
  weights:
    cost: 1.0
    latency: 0.0001
    uncertainty: 0.2
    risk: 0.5
    frontier_tokens: 0.000001
  strategies:
    - id: jev-control
      source: jev
      capabilities: [control]
      predicted_vsr: 0.94
      estimated_cost_usd: 0.0001
      estimated_latency_ms: 60
    - id: qwen-generation
      source: frontier
      capabilities: [generation]
      model_alias: qwen
      predicted_vsr: 0.96
      estimated_cost_usd: 0.05
      estimated_latency_ms: 500
      frontier_input_tokens: 10000
      frontier_output_tokens: 2000
models:
  qwen:
    provider: mock
    model: qwen
    tier: frontier
    transport: mock
''',
        encoding="utf-8",
    )
    cfg = AppConfig.load(config)
    fabric = cfg.intelligence_fabric()
    assert fabric is not None
    assert cfg.required_vsr("generation") == 0.91
    selected = fabric.select(capability="generation", required_vsr=cfg.required_vsr("generation"))
    assert selected.strategy_id == "qwen-generation"
    assert selected.metadata["model_alias"] == "qwen"
    assert fabric.frontier_budget.remaining == {
        "input_tokens": 120000,
        "output_tokens": 25000,
    }


def test_agent_uses_generation_fabric_instead_of_frontier_decision_call(tmp_path) -> None:
    from jev_engineering.agent import CodingAgent
    from jev_engineering.decisions import DecisionEngine
    from jev_engineering.model_registry import ModelRegistry
    from jev_engineering.providers.mock import ScriptedProviderFactory
    from jev_engineering.testing import ScriptedDecisionBackend
    from jev_engineering.types import AgentStatus

    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )

    decisions = ScriptedDecisionBackend(
        [
            {"answers": {
                "f0": {"type": "score", "score": 4, "confidence": 1},
                "f1": {"type": "score", "score": 4, "confidence": 1},
            }},
            {"answers": {
                "destructive": {"type": "noul", "noul": 0.01},
                "needs_human": {"type": "noul", "noul": 0.01},
            }},
            {"answers": {
                "destructive": {"type": "noul", "noul": 0.01},
                "needs_human": {"type": "noul", "noul": 0.01},
            }},
            {"answers": {
                "done": {"type": "noul", "noul": 0.99},
                "judgeable": {"type": "noul", "noul": 0.99},
            }},
        ]
    )
    registry = ModelRegistry.from_dict(
        {"models": {
            "mock-a": {"provider": "mock", "model": "a", "tier": "frontier", "transport": "mock"},
            "mock-b": {"provider": "mock", "model": "b", "tier": "frontier", "transport": "mock"},
        }}
    )
    fabric = IntelligenceFabric(
        bids=[
            IntelligenceBid(
                strategy_id="a",
                source="frontier",
                capabilities=("generation",),
                predicted_vsr=0.80,
                estimated_cost_usd=0.01,
                estimated_latency_ms=10,
                frontier_input_tokens=100,
                frontier_output_tokens=20,
                metadata={"model_alias": "mock-a"},
            ),
            IntelligenceBid(
                strategy_id="b",
                source="frontier",
                capabilities=("generation",),
                predicted_vsr=0.96,
                estimated_cost_usd=0.02,
                estimated_latency_ms=20,
                frontier_input_tokens=200,
                frontier_output_tokens=40,
                metadata={"model_alias": "mock-b"},
            ),
        ],
        frontier_budget=FrontierTokenBudget(input_limit=1000, output_limit=200),
    )
    provider = ScriptedProviderFactory(turns=[
        {"tool_calls": [{"id": "1", "name": "write_file", "arguments": {
            "path": "calc.py", "content": "def add(a, b):\n    return a + b\n"
        }}]},
        {"tool_calls": [{"id": "2", "name": "run_command", "arguments": {
            "command": "python -m pytest -q"
        }}]},
        {"text": "done"},
    ])

    result = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        max_turns=8,
        intelligence_fabric=fabric,
        generation_required_vsr=0.90,
    ).run("Fix add")

    assert result.status == AgentStatus.VERIFIED
    assert provider.created_profiles[0].alias == "mock-b"
    assert len(decisions.requests) == 4  # scope + two safety gates + done; no model-choice call
    assert result.metrics["fabric_selections"] == 1
    assert result.metrics["fabric_frontier_selections"] == 1
    assert result.metrics["fabric_frontier_input_tokens_reserved"] == 200
    assert result.metrics["fabric_frontier_output_tokens_reserved"] == 40


def test_decision_request_authority_is_independent_of_cognitive_bid() -> None:
    from jev_engineering.intelligence_fabric import DecisionRequest

    fabric = IntelligenceFabric(
        bids=[_bid("jev", source="jev", vsr=0.99, cost=0.0001, latency=10)],
        frontier_budget=FrontierTokenBudget(input_limit=0, output_limit=0),
    )
    request = DecisionRequest(
        request_id="risk-1",
        capability="control",
        required_vsr=0.8,
        authority_granted=False,
    )
    with pytest.raises(NoAdmissibleIntelligence, match="no authority"):
        fabric.select_request(request)


def test_frontier_contract_schemas_are_valid_json_and_versioned() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parents[1] / "schemas"
    expected = {
        "decision-request.v1.schema.json",
        "intelligence-bid.v1.schema.json",
        "frontier-token-budget.v1.schema.json",
        "competence-observation.v1.schema.json",
    }
    assert expected <= {p.name for p in root.glob("*.json")}
    for name in expected:
        payload = json.loads((root / name).read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["type"] == "object"
        assert payload["required"]


def test_contract_schemas_are_packaged_with_python_module() -> None:
    import json
    from importlib.resources import files

    payload = json.loads(
        files("jev_engineering").joinpath("schemas/intelligence-bid.v1.schema.json").read_text()
    )
    assert payload["title"] == "Aftergraph IntelligenceBid v1"


def test_competence_graph_round_trips_persistent_observations(tmp_path) -> None:
    path = tmp_path / "competence.json"
    key = CompetenceKey(
        strategy_id="qwen",
        task_family="bugfix",
        repo="repo-a",
        language="python",
        mission_phase="execute",
        risk_class="normal",
    )
    graph = CompetenceGraph(prior_alpha=2.0, prior_beta=1.0)
    graph.observe(key, success=True)
    graph.observe(key, success=False, weight=0.5)
    graph.save(path)

    loaded = CompetenceGraph.load(path)
    estimate = loaded.estimate(key)
    assert estimate.observations == 2
    assert estimate.alpha == 3.0
    assert estimate.beta == 1.5
    assert loaded.prior_alpha == 2.0
    assert loaded.prior_beta == 1.0
