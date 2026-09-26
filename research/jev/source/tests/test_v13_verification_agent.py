from __future__ import annotations

from jev_engineering.agent import CodingAgent
from jev_engineering.decisions import DecisionEngine
from jev_engineering.model_registry import ModelRegistry
from jev_engineering.providers.mock import ScriptedProviderFactory
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import AgentStatus
from jev_engineering.verification_portfolio import (
    VerificationMethod,
    VerificationPortfolioOptimizer,
    VerificationRequirement,
)


def test_agent_executes_adaptive_verification_plan_and_requires_all_methods(tmp_path) -> None:
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    decisions = ScriptedDecisionBackend([
        {"answers": {
            "f0": {"type": "score", "score": 4, "confidence": 1},
            "f1": {"type": "score", "score": 3, "confidence": 1},
        }},
        {"answers": {"model": {"type": "choice", "choice": "mock"}}},
        {"answers": {
            "destructive": {"type": "noul", "noul": 0.01},
            "needs_human": {"type": "noul", "noul": 0.01},
        }},
        {"answers": {
            "done": {"type": "noul", "noul": 0.99},
            "judgeable": {"type": "noul", "noul": 0.99},
        }},
    ])
    registry = ModelRegistry.from_dict({"models": {
        "mock": {"provider": "mock", "model": "mock", "tier": "frontier", "transport": "mock"}
    }})
    provider = ScriptedProviderFactory(turns=[
        {"tool_calls": [{"id": "1", "name": "write_file", "arguments": {
            "path": "calc.py", "content": "def add(a, b):\n    return a + b\n"
        }}]},
        {"text": "done"},
    ])
    optimizer = VerificationPortfolioOptimizer([
        VerificationMethod("unit", 1, 0.75, 0.01, 100, "python -m pytest -q"),
        VerificationMethod("compile", 2, 0.70, 0.01, 50, "python -m compileall -q ."),
    ])
    requirement = VerificationRequirement(required_assurance=2, required_detection=0.90)
    result = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        verification_optimizer=optimizer,
        verification_requirement=requirement,
        max_turns=5,
    ).run("Fix add")
    assert result.status == AgentStatus.VERIFIED
    assert result.metrics["verifier_runs"] == 2
    plans = [event for event in result.events if event["type"] == "verification.plan"]
    assert len(plans) == 1
    assert plans[0]["methods"] == ["unit", "compile"]
