from __future__ import annotations

from jev_engineering.agent import CodingAgent
from jev_engineering.decisions import DecisionEngine
from jev_engineering.model_registry import ModelRegistry
from jev_engineering.providers.mock import ScriptedProviderFactory
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import AgentStatus


def test_deterministically_consequential_action_waits_for_human_before_jev(tmp_path) -> None:
    (tmp_path / "x.py").write_text("x = 1\n")
    decisions = ScriptedDecisionBackend([
        {"answers": {"f0": {"type": "score", "score": 4.0}}},
        {"answers": {"model": {"type": "choice", "choice": "frontier", "confidence": 1.0}}},
    ])
    registry = ModelRegistry.from_dict({
        "models": {"frontier": {"provider": "mock", "model": "f", "tier": "frontier", "transport": "mock"}}
    })
    provider = ScriptedProviderFactory(turns=[
        {"tool_calls": [{"id": "1", "name": "run_command", "arguments": {"command": "git push origin main"}}]}
    ])
    result = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        max_turns=2,
        command_mode="full",
    ).run("push release")
    assert result.status == AgentStatus.NEEDS_APPROVAL
    # Only scope + model choice consumed decisions: authority gate ran before Jev risk prediction.
    assert len(decisions.requests) == 2
