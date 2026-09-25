from __future__ import annotations

import pathlib

from jev_engineering.agent import CodingAgent
from jev_engineering.decisions import DecisionEngine
from jev_engineering.model_registry import ModelRegistry
from jev_engineering.providers.mock import ScriptedProviderFactory
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import AgentStatus


def test_end_to_end_loop_requires_verification_before_verified(tmp_path: pathlib.Path) -> None:
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )

    decisions = ScriptedDecisionBackend(
        [
            {"answers": {"f0": {"type": "score", "score": 3.9, "confidence": 0.9},
                          "f1": {"type": "score", "score": 3.5, "confidence": 0.9}}},
            {"answers": {"model": {"type": "choice", "choice": "mock-frontier", "confidence": 0.99,
                                     "probabilities": {"mock-frontier": 0.99}}}},
            {"answers": {"destructive": {"type": "noul", "noul": 0.01},
                          "needs_human": {"type": "noul", "noul": 0.01}}},
            {"answers": {"destructive": {"type": "noul", "noul": 0.01},
                          "needs_human": {"type": "noul", "noul": 0.01}}},
            {"answers": {"done": {"type": "noul", "noul": 0.99},
                          "judgeable": {"type": "noul", "noul": 0.99}}},
        ]
    )
    engine = DecisionEngine(decisions)
    registry = ModelRegistry.from_dict(
        {"models": {"mock-frontier": {"provider": "mock", "model": "frontier", "tier": "frontier",
                                        "transport": "mock"}}}
    )
    provider_factory = ScriptedProviderFactory(
        turns=[
            {"tool_calls": [{"id": "1", "name": "write_file", "arguments": {"path": "calc.py", "content": "def add(a, b):\n    return a + b\n"}}]},
            {"tool_calls": [{"id": "2", "name": "run_command", "arguments": {"command": "python -m pytest -q"}}]},
            {"text": "Implemented and tests pass."},
        ]
    )

    agent = CodingAgent(
        workspace=tmp_path,
        decisions=engine,
        registry=registry,
        provider_factory=provider_factory,
        verify_command="python -m pytest -q",
        max_turns=8,
    )
    result = agent.run("Fix add() and make the tests pass")
    assert result.status == AgentStatus.VERIFIED
    assert "return a + b" in (tmp_path / "calc.py").read_text()
    assert result.verification_exit_code == 0


def test_agent_emits_provider_and_control_plane_metrics(tmp_path: pathlib.Path) -> None:
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    def d(answers):
        return {"usage": {"input_tokens": 10, "output_tokens": 1}, "answers": answers}
    decisions = ScriptedDecisionBackend([
        d({"f0": {"type": "score", "score": 4, "confidence": 1}, "f1": {"type": "score", "score": 4, "confidence": 1}}),
        d({"model": {"type": "choice", "choice": "mock-frontier", "confidence": 1}}),
        d({"destructive": {"type": "noul", "noul": 0.01}, "needs_human": {"type": "noul", "noul": 0.01}}),
        d({"destructive": {"type": "noul", "noul": 0.01}, "needs_human": {"type": "noul", "noul": 0.01}}),
        d({"done": {"type": "noul", "noul": 0.99}, "judgeable": {"type": "noul", "noul": 0.99}}),
    ])
    registry = ModelRegistry.from_dict({"models": {"mock-frontier": {
        "provider": "mock", "model": "frontier", "tier": "frontier", "transport": "mock"
    }}})
    provider_factory = ScriptedProviderFactory(turns=[
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 40}},
         "tool_calls": [{"id": "1", "name": "write_file", "arguments": {"path": "calc.py", "content": "def add(a, b):\n    return a + b\n"}}]},
        {"usage": {"prompt_tokens": 50, "completion_tokens": 10},
         "tool_calls": [{"id": "2", "name": "run_command", "arguments": {"command": "python -m pytest -q"}}]},
        {"usage": {"prompt_tokens": 30, "completion_tokens": 5}, "text": "done"},
    ])
    result = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider_factory,
        verify_command="python -m pytest -q",
        max_turns=8,
    ).run("Fix add")
    assert result.status == AgentStatus.VERIFIED
    assert result.metrics["provider_calls"] == 3
    assert result.metrics["provider_input_tokens"] == 180
    assert result.metrics["provider_output_tokens"] == 35
    assert result.metrics["provider_cached_input_tokens"] == 40
    assert result.metrics["decision_calls"] == 5
    assert result.metrics["decision_input_tokens"] == 50
    assert result.metrics["decision_output_tokens"] == 5
    assert result.metrics["completion_claims"] == 1
    assert result.metrics["false_completion_claims"] == 0
    assert result.metrics["control_plane_token_tax"] > 0
    assert result.metrics["wall_time_ms"] >= 0
