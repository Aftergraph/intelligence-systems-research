from __future__ import annotations

from jev_engineering.agent import CodingAgent
from jev_engineering.decisions import DecisionEngine
from jev_engineering.model_registry import ModelRegistry
from jev_engineering.providers.mock import ScriptedProviderFactory
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import ToolCall


def test_run_command_safety_decision_keeps_semantics_but_redacts_secret_literals(tmp_path) -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "destructive": {"type": "noul", "noul": 0.01},
                    "needs_human": {"type": "noul", "noul": 0.01},
                }
            }
        ]
    )
    agent = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(backend),
        registry=ModelRegistry(),
        provider_factory=ScriptedProviderFactory(turns=[]),
        verify_command="python -m pytest -q",
        command_mode="full",
    )
    call = ToolCall(
        "1",
        "run_command",
        {"command": "python -c 'print(1)' --token sk-abcdefghijklmnopqrstuvwxyz123456"},
    )
    decision = agent._gate_action("inspect command", call)
    assert decision.action == "allow"
    state = backend.requests[0]["state"]
    forwarded = state["command"]
    assert "python -c" in forwarded
    assert "--token" in forwarded
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in forwarded
    assert "[REDACTED]" in forwarded
