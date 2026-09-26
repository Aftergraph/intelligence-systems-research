from __future__ import annotations

from jev_engineering.agent import CodingAgent
from jev_engineering.context_compiler import ContextCompiler
from jev_engineering.decisions import DecisionEngine
from jev_engineering.model_registry import ModelRegistry
from jev_engineering.proof_graph import ProofGraph
from jev_engineering.providers.mock import ScriptedProviderFactory
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import AgentStatus


def test_agent_compiles_context_and_mints_subject_bound_verification_claim(tmp_path) -> None:
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
        {"tool_calls": [{"id": "2", "name": "run_command", "arguments": {
            "command": "python -m pytest -q"
        }}]},
        {"text": "done"},
    ])
    proof = ProofGraph()
    agent = CodingAgent(
        workspace=tmp_path,
        decisions=DecisionEngine(decisions),
        registry=registry,
        provider_factory=provider,
        verify_command="python -m pytest -q",
        max_turns=8,
        context_compiler=ContextCompiler(),
        context_token_budget=200,
        proof_graph=proof,
    )
    result = agent.run("Fix add")

    assert result.status == AgentStatus.VERIFIED
    assert any(e["type"] == "context.compiled" for e in result.events)
    proof_events = [e for e in result.events if e["type"] == "proof.claim"]
    assert len(proof_events) == 1
    claim_id = proof_events[0]["claim_id"]
    claim = proof.claim(claim_id)
    assert claim.subject.startswith("sha256:")
    assert claim.verdict is True
    assert proof.is_fresh(claim_id) is True
    assert result.metrics["proof_claims"] == 2
    mission_events = [e for e in result.events if e["type"] == "mission.verified"]
    assert len(mission_events) == 1
    assert proof.accepts([mission_events[0]["acceptance_claim_id"]]) is True
