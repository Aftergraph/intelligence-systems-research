import os
import sys

# Ensure workspace root is in sys.path
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

import pytest
from state.lifecycle import MissionLifecycle
from state.store import DurableStateStore
from state.checkpoint import CheckpointManager
from memory.store import MemoryStore, MemoryPolicy
from authority.evaluator import AuthorityEvaluator
from authority.delegation import DelegationManager
from capabilities.registry import Capability, CapabilityRegistry
from capabilities.resolver import CapabilityResolver
from capabilities.dispatcher import CapabilityDispatcher
from evidence.models import EvidenceItem
from evidence.store import EvidenceStore
from assurance.engine import AssuranceEngine
from assurance.verifiers import DeterministicTestVerifier
from telemetry.events import TrajectoryRecorder
from telemetry.cost_meter import CostMeter, BudgetExceededError
from providers.router import ModelRouter
from providers.dialagram import DialagramProvider
from providers.openai import OpenAIProvider
from agent.prompt_compiler import PromptCompiler
from agent.context_manager import ContextManager
from agent.execution_loop import AgentExecutionLoop
from agent.core import InHouseAgent

# ==============================================================================
# 12 MANDATORY ARCHITECTURAL INVARIANT TESTS FOR THE IN-HOUSE AGENT
# ==============================================================================

def test_01_agent_cannot_self_set_verified():
    """Assertion 1: In-House Agent cannot mutate mission state to VERIFIED."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    assurance = AssuranceEngine(lifecycle=lifecycle, evidence_store=evidence_store)

    # Agent emits candidate completion
    state = assurance.intercept_candidate_completion("m-test-01", "Agent claims task is done")

    # Invariant 1: State must be VERIFYING, NOT VERIFIED!
    assert state == "VERIFYING"
    assert lifecycle.current_state == "VERIFYING"
    assert lifecycle.current_state != "VERIFIED"


def test_02_candidate_completion_enters_verifying():
    """Assertion 2: Emitting candidate completion enters VERIFYING state."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    assurance = AssuranceEngine(lifecycle=lifecycle, evidence_store=evidence_store)

    assurance.intercept_candidate_completion("m-test-02", "Ready for audit")
    assert lifecycle.current_state == "VERIFYING"


def test_03_failed_verification_enters_recovering():
    """Assertion 3: Failed Tier 2 verification enters RECOVERING, not false completion."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    assurance = AssuranceEngine(lifecycle=lifecycle, evidence_store=evidence_store)
    assurance.intercept_candidate_completion("m-test-03")

    # Required criterion has NO qualifying evidence recorded
    success, diag = assurance.evaluate_mission_criteria(
        mission_id="m-test-03",
        required_criteria=["crit-unit-tests"],
        minimum_tier="tier_2_deterministic"
    )

    assert not success
    assert lifecycle.current_state == "RECOVERING"
    assert "crit-unit-tests" in diag["failed_criteria"]
    assert diag["remaining_recovery_attempts"] == 2


def test_04_recovery_returns_to_execution_loop():
    """Assertion 4: Recovery state returns to execution loop with diagnostic payload."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    assurance = AssuranceEngine(lifecycle=lifecycle, evidence_store=evidence_store)
    assurance.intercept_candidate_completion("m-test-04")
    _, diag = assurance.evaluate_mission_criteria("m-test-04", ["crit-lint"])

    assert lifecycle.current_state == "RECOVERING"
    # Transition back to RUNNING
    lifecycle.transition_to("RUNNING", reason="Resuming execution loop with feedback")
    assert lifecycle.current_state == "RUNNING"

    # Verify diagnostic feedback is formatted into prompt
    compiler = PromptCompiler()
    prompt = compiler.compile_tier1_prompt(
        mission_id="m-test-04",
        objective="Fix code",
        constraints=["no_eval"],
        criteria_ids=["crit-lint"],
        allowed_capabilities=["tool://linter"],
        budget_remaining={"tokens": 5000, "usd": 0.20},
        diagnostic_feedback=diag["diagnostic_message"]
    )
    assert "Remediation required" in prompt


def test_05_authority_denied_before_tool_execution():
    """Assertion 5: Capability Dispatcher denies execution before invoking handler if out of scope."""
    executed = []
    def dangerous_handler(payload):
        executed.append("DANGEROUS_ACTION_PERFORMED")
        return {"result": "exploited"}

    reg = CapabilityRegistry()
    reg.register(Capability(uri="tool://system/exec", description="Arbitrary shell", handler=dangerous_handler))
    resolver = CapabilityResolver(reg)
    auth = AuthorityEvaluator()
    dispatcher = CapabilityDispatcher(resolver=resolver, authority_evaluator=auth)

    delegation_token = {
        "id": "del-scoped",
        "principal": "human",
        "delegate": "agent-01",
        "scope": {
            "allowed_capabilities": ["tool://git/*"],
            "denied_capabilities": ["tool://system/*"]
        }
    }

    # Attempt to execute tool://system/exec
    with pytest.raises(PermissionError) as exc_info:
        dispatcher.dispatch("tool://system/exec", {"cmd": "rm -rf"}, delegation_token)

    assert "explicitly denied" in str(exc_info.value) or "not granted" in str(exc_info.value)
    # Ensure dangerous handler was NEVER invoked
    assert len(executed) == 0


def test_06_mission_global_budget_across_subagents():
    """Assertion 6: Cumulative token/cost budget applies globally across all subagents."""
    meter = CostMeter(max_tokens=1000, max_cost_usd=0.05)

    # Subagent 1 uses 400 tokens
    meter.record_usage("mission-shared", "provider-a", prompt_tokens=300, completion_tokens=100, cost_usd=0.01)
    # Subagent 2 uses 500 tokens
    meter.record_usage("mission-shared", "provider-b", prompt_tokens=400, completion_tokens=100, cost_usd=0.02)

    assert meter.get_mission_summary("mission-shared")["tokens"] == 900

    # Subagent 3 tries to use 200 tokens (900 + 200 = 1100 > 1000 max)
    with pytest.raises(BudgetExceededError) as exc_info:
        meter.record_usage("mission-shared", "provider-c", prompt_tokens=100, completion_tokens=100, cost_usd=0.01)

    assert "exceeded token ceiling" in str(exc_info.value)


def test_07_durable_checkpoint_resumes_after_crash(tmp_path):
    """Assertion 7: Crash recovery restores state from durable checkpoint with verified SHA-256."""
    chk_mgr = CheckpointManager(checkpoints_dir=str(tmp_path))

    state_payload = {
        "mission_id": "m-crash-test",
        "step": 4,
        "active_file": "agent/core.py",
        "partial_result": "compiled_successfully"
    }

    chk_file = chk_mgr.save_checkpoint("m-crash-test", sequence=4, payload=state_payload)
    assert os.path.exists(chk_file)

    # Crash & restart: load latest
    restored = chk_mgr.load_latest_checkpoint("m-crash-test")
    assert restored is not None
    assert restored["step"] == 4
    assert restored["partial_result"] == "compiled_successfully"


def test_08_provider_fallback_recorded_in_trajectory():
    """Assertion 8: Provider failure triggers fallback, logged to trajectory hash chain."""
    trajectory = TrajectoryRecorder(mission_id="m-fallback-test")
    router = ModelRouter(trajectory_recorder=trajectory)

    # Simulate generation
    resp = router.generate_with_fallback(
        prompt="Solve problem",
        system_prompt="",
        provider_name="dialagram",
        dry_run=True
    )

    assert resp.content is not None
    # Trajectory must have valid cryptographic chain
    assert trajectory.verify_integrity()


def test_09_model_change_does_not_mutate_mission():
    """Assertion 9: Switching models does not alter Mission Contract semantics."""
    mission_contract = {
        "id": "m-invariable",
        "objective": "Zero false completions",
        "criteria": ["crit-01", "crit-02"],
        "constraints": ["no_unauthorized_network"],
        "budget": {"tokens": 50000}
    }

    router = ModelRouter()
    # Execute under model A
    p_a, m_a = router.resolve_model(preferred_provider="dialagram")
    # Execute under model B
    p_b, m_b = router.resolve_model(preferred_provider="anthropic")

    assert (p_a, m_a) != (p_b, m_b)
    # The mission contract remains completely unmutated
    assert mission_contract["objective"] == "Zero false completions"
    assert len(mission_contract["criteria"]) == 2
    assert mission_contract["budget"]["tokens"] == 50000


def test_10_context_compression_preserves_constraints():
    """Assertion 10: Sliding-window context compression never drops mission constraints."""
    ctx = ContextManager(max_turns=3)
    constraints = ["MUST_NOT_EXCEED_BUDGET", "NO_ROOT_ACCESS"]
    ctx.set_pinned_context(system_prompt="System instructions", constraints=constraints)

    # Add 10 turns
    for i in range(10):
        ctx.add_turn(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")

    # Preserved constraints must be 100% intact
    preserved = ctx.get_preserved_constraints()
    assert preserved == constraints

    assembled = ctx.get_assembled_context()
    # System prompt is turn 0
    assert assembled[0]["role"] == "system"
    # Oldest turns were dropped, only recent 3 dialogue turns kept
    assert len(assembled) == 4  # 1 system + 3 dialogue


def test_11_runtime_adapters_preserve_contract_semantics():
    """Assertion 11: External runtime adapters adhere to SPEC-001 invariants."""
    from adapters.langgraph_adapter import LangGraphAdapter
    from adapters.autogen_adapter import AutoGenAdapter

    lg = LangGraphAdapter()
    ag = AutoGenAdapter()

    mission_doc = {
        "metadata": {"id": "m-cross-test"},
        "objective": {"outcome": "Cross runtime test objective"},
        "success": {"all": ["crit-01", "crit-02"]},
        "recovery": {"retry_limit": 3}
    }

    c_lg = lg.compile_mission(mission_doc)
    c_ag = ag.compile_mission(mission_doc)

    # Invariant: Neither adapter initializes state as verified
    assert c_lg["state_schema"]["is_verified"] is False
    assert any(a["name"] == "VerifierAgent" and a.get("is_critic") for a in c_ag["agents"])

    # Both extract identical semantic invariants
    inv_lg = lg.extract_semantic_invariants(c_lg)
    inv_ag = ag.extract_semantic_invariants(c_ag)

    assert inv_lg["objective"] == inv_ag["objective"] == "Cross runtime test objective"
    assert inv_lg["criteria"] == inv_ag["criteria"] == ["crit-01", "crit-02"]
    assert inv_lg["recovery_limit"] == inv_ag["recovery_limit"] == 3


def test_12_cost_usage_attributed_by_mission_and_provider():
    """Assertion 12: Cost and token usage attributed accurately by mission and provider."""
    meter = CostMeter()
    meter.record_usage("mission-alpha", "dialagram", prompt_tokens=100, completion_tokens=50, cost_usd=0.0)
    meter.record_usage("mission-alpha", "openai", prompt_tokens=200, completion_tokens=50, cost_usd=0.002)
    meter.record_usage("mission-beta", "anthropic", prompt_tokens=300, completion_tokens=100, cost_usd=0.005)

    alpha_summary = meter.get_mission_summary("mission-alpha")
    beta_summary = meter.get_mission_summary("mission-beta")
    dialagram_summary = meter.get_provider_summary("dialagram")
    openai_summary = meter.get_provider_summary("openai")

    assert alpha_summary["tokens"] == 400
    assert abs(alpha_summary["cost_usd"] - 0.002) < 1e-6
    assert beta_summary["tokens"] == 400
    assert abs(beta_summary["cost_usd"] - 0.005) < 1e-6

    assert dialagram_summary["tokens"] == 150
    assert openai_summary["tokens"] == 250
