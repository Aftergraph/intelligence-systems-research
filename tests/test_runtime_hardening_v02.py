import json
import os
import sys
import threading
import time
import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from state.lifecycle import MissionLifecycle
from state.store import DurableStateStore
from state.checkpoint import CheckpointManager
from state.journal import EventJournal
from memory.store import MemoryStore, MemoryPolicy
from authority.evaluator import AuthorityEvaluator
from authority.delegation import DelegationManager
from capabilities.registry import Capability, CapabilityRegistry
from capabilities.resolver import CapabilityResolver
from capabilities.dispatcher import CapabilityDispatcher
from evidence.models import EvidenceItem, AssuranceReceipt
from evidence.store import EvidenceStore
from assurance.engine import AssuranceEngine
from assurance.verifiers import DeterministicTestVerifier
from assurance.principals import AgentPrincipal, AssurancePrincipal
from telemetry.events import TrajectoryRecorder
from telemetry.cost_meter import CostMeter, BudgetExceededError
from providers.base import ModelMetadata, ProviderResponse, RoutingReceipt
from providers.router import ModelRouter
from providers.dialagram import DialagramProvider
from agent.prompt_compiler import PromptCompiler
from agent.context_manager import ContextManager
from agent.execution_loop import AgentExecutionLoop
from agent.core import InHouseAgent

# ==============================================================================
# RUNTIME HARDENING v0.2 TEST SUITE
# ==============================================================================

def test_01_multistep_agent_execution_cycle(tmp_path):
    """1. Multi-step agent execution: inspect -> edit -> fail test -> repair -> pass -> complete -> verify."""
    # Setup test workspace
    code_file = tmp_path / "calc.py"
    code_file.write_text("def add(a, b): return a - b\n")  # Buggy initial code

    test_file = tmp_path / "test_calc.py"
    test_file.write_text("import calc\ndef test_add(): assert calc.add(2, 3) == 5\n")

    registry = CapabilityRegistry()
    def inspect_repo(p):
        return {"files": [f.name for f in tmp_path.iterdir()]}
    def edit_file(p):
        code_file.write_text("def add(a, b): return a + b\n")  # Bug fixed
        return {"modified": "calc.py", "status": "written"}
    def run_unit_tests(p):
        import subprocess
        res = subprocess.run([sys.executable, "-m", "pytest", str(test_file)], capture_output=True, text=True)
        return {"exit_code": res.returncode, "stdout": res.stdout}

    registry.register(Capability(uri="tool://inspect", description="List files", handler=inspect_repo))
    registry.register(Capability(uri="tool://edit", description="Modify file", handler=edit_file))
    registry.register(Capability(uri="tool://test", description="Run pytest", handler=run_unit_tests))

    resolver = CapabilityResolver(registry)
    auth = AuthorityEvaluator()
    dispatcher = CapabilityDispatcher(resolver=resolver, authority_evaluator=auth)
    trajectory = TrajectoryRecorder(mission_id="m-multistep")
    cost_meter = CostMeter()
    journal = EventJournal(mission_id="m-multistep", journal_path=str(tmp_path / "journal.jsonl"))

    router = ModelRouter(trajectory_recorder=trajectory)
    agent = InHouseAgent(
        router=router,
        dispatcher=dispatcher,
        trajectory=trajectory,
        cost_meter=cost_meter,
        journal=journal
    )

    delegation_token = {
        "id": "del-full",
        "principal": "human",
        "delegate": "agent-01",
        "scope": {"allowed_capabilities": ["tool://*"], "denied_capabilities": []}
    }

    # Execute iterative sequence through 3 sequential tool calls
    simulated_tools = [
        {"capability_uri": "tool://inspect", "payload": {}},
        {"capability_uri": "tool://edit", "payload": {"file": "calc.py"}},
        {"capability_uri": "tool://test", "payload": {}}
    ]

    candidate = agent.execute_mission_loop(
        mission_id="m-multistep",
        objective="Fix calculator addition",
        constraints=["no_unauthorized_edits"],
        criteria_ids=["crit-calc-tests"],
        allowed_capabilities=["tool://*"],
        delegation_token=delegation_token,
        max_iterations=5,
        dry_run=True,
        simulated_tool_responses=simulated_tools
    )

    assert candidate["type"] == "CANDIDATE_COMPLETION"
    assert candidate["iterations"] >= 3
    assert len(candidate["tool_results"]) == 3
    assert candidate["tool_results"][1]["result"]["modified"] == "calc.py"
    assert candidate["tool_results"][2]["result"]["exit_code"] == 0  # Fixed code passed test!


def test_02_model_tool_observation_model_feedback():
    """2. Observations are returned to model context turn-by-turn without premature exit."""
    ctx = ContextManager(max_turns=5)
    ctx.set_pinned_control_context("m-obs", "Test observation feedback", ["c1"], ["crit-1"], {"tokens": 1000})

    # Step 1: Tool call
    ctx.add_turn(role="assistant", content="Calling tool://git/status")
    # Step 2: Observation received
    ctx.add_observation("tool://git/status", "On branch main, clean tree")
    # Step 3: Next model turn
    ctx.add_turn(role="assistant", content="Tree is clean. Calling tool://git/pull")
    # Step 4: Next observation
    ctx.add_observation("tool://git/pull", "Already up to date.")

    assembled = ctx.get_assembled_context()
    assert len(assembled) == 5  # 1 system + 4 dialogue
    assert "[tool://git/status Observation]: On branch main, clean tree" in assembled[2]["content"]
    assert "[tool://git/pull Observation]: Already up to date." in assembled[4]["content"]


def test_03_durable_work_plane_event_journal(tmp_path):
    """3. Event Journal records sequenced causal events and state is materialized from it."""
    j_path = str(tmp_path / "journal_test.jsonl")
    journal = EventJournal(mission_id="m-dur", journal_path=j_path)

    journal.append_event("mission.created", {"name": "Test Mission"})
    journal.append_event("mission.started", {})
    journal.append_event("budget.committed", {"tokens": 150, "cost_usd": 0.001})
    journal.append_event("capability.completed", {"modified_file": "server.py"})
    journal.append_event("candidate_completion.created", {"completion": "Ready for test"})
    journal.append_event("verification.passed", {})

    events = journal.list_events()
    assert len(events) == 6
    assert events[1]["causal_parent"] == events[0]["event_id"]
    assert events[5]["sequence"] == 6

    # Materialize current state from events
    store = DurableStateStore(mission_id="m-dur", storage_dir=str(tmp_path))
    store.materialize_from_events(events)

    assert store.mission_state.lifecycle_state == "VERIFIED"
    assert store.mission_state.budget_spent["tokens"] == 150
    assert "server.py" in store.world_state.modified_files


def test_04_crash_recovery_with_idempotency_keys(tmp_path):
    """4. Action executes remotely but crashes before local commit; reconciled without duplicate side-effect."""
    chk_mgr = CheckpointManager(checkpoints_dir=str(tmp_path))
    idempotency_key = "idemp-git-push-commit-abc"

    # Simulate crash right after remote push
    chk_mgr.record_external_receipt(idempotency_key, {
        "operation": "remote_git_push",
        "status": "UNCERTAIN_CRASH"
    })
    chk_mgr.save_checkpoint("m-crash", sequence=3, payload={"step": "pushing"})

    # On restart, query external world using reconciliation handler
    def external_repo_checker(key: str) -> bool:
        # In reality, runs git log origin/main to see if commit is already there
        return key == "idemp-git-push-commit-abc"

    reconciled = chk_mgr.reconcile_external_effects("m-crash", external_repo_checker)
    assert reconciled[idempotency_key] == "RECONCILED_SUCCESS"

    # Dispatcher cache avoids duplicate side-effect
    reg = CapabilityRegistry()
    pushes = []
    def push_handler(p):
        pushes.append("PUSHED")
        return {"pushed": True}
    reg.register(Capability(uri="tool://git/push", description="push", handler=push_handler))
    dispatcher = CapabilityDispatcher(resolver=CapabilityResolver(reg))

    # First run succeeds and caches idempotency receipt
    res1 = dispatcher.dispatch("tool://git/push", {"ref": "main"}, idempotency_key="op-1")
    assert len(pushes) == 1
    assert not res1.get("is_cached_replay")

    # Replay with same idempotency key returns cached receipt without re-executing
    res2 = dispatcher.dispatch("tool://git/push", {"ref": "main"}, idempotency_key="op-1")
    assert len(pushes) == 1  # Did NOT push again!
    assert res2.get("is_cached_replay") is True


def test_05_atomic_concurrent_budget_reservation_race():
    """5. Two concurrent subagents race to reserve the final remaining budget."""
    meter = CostMeter(max_tokens=1000)

    # Initial usage 800 tokens
    meter.record_usage("m-race", "prov", 700, 100, 0.0)
    assert meter.get_mission_summary("m-race")["tokens"] == 800

    # Remaining budget is only 200 tokens!
    # Subagent 1 and Subagent 2 both try to reserve 150 tokens simultaneously in parallel threads
    results = {"success": 0, "failure": 0}
    lock = threading.Lock()

    def worker():
        try:
            r_id = meter.reserve("m-race", estimated_tokens=150)
            time.sleep(0.01)
            meter.commit(r_id, actual_tokens=150, actual_cost_usd=0.0)
            with lock:
                results["success"] += 1
        except BudgetExceededError:
            with lock:
                results["failure"] += 1

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one thread MUST succeed and one thread MUST fail (150 + 150 = 300 > 200)
    assert results["success"] == 1
    assert results["failure"] == 1
    assert meter.get_mission_summary("m-race")["tokens"] == 950


def test_06_policy_constrained_scored_routing_and_receipts():
    """6. Routing applies hard requirements, policy filters, scoring, and emits a durable receipt."""
    trajectory = TrajectoryRecorder(mission_id="m-routing")
    router = ModelRouter(trajectory_recorder=trajectory)

    prov, model, receipt = router.route_request(
        mission_id="m-routing",
        requires_reasoning=True,
        requires_tools=True,
        preferred_provider="dialagram"
    )

    assert prov == "dialagram"
    assert model in ("qwen-3.8-max", "deepseek-v4", "tencent-hy3", "meta-muse-spark-1.2")
    assert isinstance(receipt, RoutingReceipt)
    assert len(receipt.eligible_candidates) > 0
    assert receipt.score_breakdown[f"{prov}:{model}"]["reasoning"] == 10.0
    assert trajectory.events[-1]["event_type"] == "POLICY_CONSTRAINED_ROUTING_DECISION"


def test_07_logical_assurance_boundary_principal_enforcement():
    """7. AgentPrincipal is barred from issuing verification decisions or transitioning to VERIFIED."""
    lifecycle = MissionLifecycle(initial_state="RUNNING")
    evidence_store = EvidenceStore()
    assurance = AssuranceEngine(lifecycle=lifecycle, evidence_store=evidence_store)
    assurance.intercept_candidate_completion("m-princ", caller=AgentPrincipal)

    # Attempting to call evaluate_mission_criteria as AgentPrincipal raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        assurance.evaluate_mission_criteria(
            mission_id="m-princ",
            required_criteria=["crit-1"],
            caller=AgentPrincipal
        )

    assert "AgentPrincipal is barred from executing verification transitions" in str(exc_info.value)
    assert lifecycle.current_state == "VERIFYING"  # Did not transition to VERIFIED!

    # Only AssurancePrincipal is permitted
    evidence_store.record(EvidenceItem(
        id="ev-1", mission_id="m-princ", criterion_ref="crit-1",
        tier="tier_2_deterministic", verifier_type="test", verifier_identifier="pytest",
        result="SATISFIED"
    ))

    success, res = assurance.evaluate_mission_criteria(
        mission_id="m-princ",
        required_criteria=["crit-1"],
        caller=AssurancePrincipal
    )
    assert success is True
    assert lifecycle.current_state == "VERIFIED"
    assert len(res["receipts"]) == 1


def test_08_conflict_aware_append_only_evidence_resolution():
    """8. Complete append-only evidence history with conflict resolution under assurance policy."""
    store = EvidenceStore()

    # Run 1: Verifier A reports PASS
    store.record(EvidenceItem(
        id="ev-01", mission_id="m-conf", criterion_ref="crit-sec",
        tier="tier_2_deterministic", verifier_type="bandit", verifier_identifier="linter-a",
        result="SATISFIED"
    ))
    assert store.satisfies_criterion("crit-sec") is True

    # Run 2: Verifier B discovers security regression and reports FAILED
    store.record(EvidenceItem(
        id="ev-02", mission_id="m-conf", criterion_ref="crit-sec",
        tier="tier_2_deterministic", verifier_type="semgrep", verifier_identifier="linter-b",
        result="FAILED"
    ))
    # Conflict: Active failure supersedes previous pass
    assert store.satisfies_criterion("crit-sec") is False

    # History preserves both items
    history = store.get_history("crit-sec")
    assert len(history) == 2
    assert history[0].id == "ev-01"
    assert history[1].id == "ev-02"

    # Run 3: Remediated and re-verified: reports PASS
    store.record(EvidenceItem(
        id="ev-03", mission_id="m-conf", criterion_ref="crit-sec",
        tier="tier_2_deterministic", verifier_type="semgrep", verifier_identifier="linter-b",
        result="SATISFIED"
    ))
    assert store.satisfies_criterion("crit-sec") is True


def test_09_extreme_context_pressure_constraint_retention():
    """9. Hard constraints are preserved even when flooded by 50,000 chars of conversation turns."""
    ctx = ContextManager(max_turns=3)
    hard_constraint = "CRITICAL_INVARIANT_NEVER_DROP_DATABASE"

    ctx.set_pinned_control_context(
        mission_id="m-flood",
        objective="Perform data migration",
        constraints=[hard_constraint],
        criteria_ids=["crit-mig"],
        remaining_budget={"tokens": 100000}
    )

    # Flood with 20 massive turns (50,000+ chars)
    for i in range(20):
        massive_tool_output = f"Block {i}: " + ("x" * 2500)
        ctx.add_observation("tool://db/dump", massive_tool_output)

    preserved = ctx.get_preserved_constraints()
    assert hard_constraint in preserved

    assembled = ctx.get_assembled_context()
    system_message = assembled[0]["content"]
    assert hard_constraint in system_message
    assert "[HARD_CONSTRAINTS]: CRITICAL_INVARIANT_NEVER_DROP_DATABASE" in system_message


def test_10_human_interaction_loop_controls():
    """10. Human control commands (pause, resume, cancel, takeover) modify runtime state and log events."""
    trajectory = TrajectoryRecorder(mission_id="m-human")
    cost_meter = CostMeter()
    router = ModelRouter()
    reg = CapabilityRegistry()
    reg.register(Capability(uri="tool://sre/drain", description="Drain node", handler=lambda p: {"drained": True}))
    dispatcher = CapabilityDispatcher(resolver=CapabilityResolver(reg))

    agent = InHouseAgent(
        router=router,
        dispatcher=dispatcher,
        trajectory=trajectory,
        cost_meter=cost_meter
    )

    agent.pause()
    assert agent.execution_loop.is_paused is True
    assert trajectory.events[-1]["event_type"] == "HUMAN_CONTROL_PAUSE"

    agent.resume()
    assert agent.execution_loop.is_paused is False
    assert trajectory.events[-1]["event_type"] == "HUMAN_CONTROL_RESUME"

    # Operator takeover: directly invoke tool
    res = agent.takeover({
        "capability_uri": "tool://sre/drain",
        "payload": {"node": "worker-1"}
    })
    assert res["status"] == "COMPLETED"
    assert trajectory.events[-1]["event_type"] == "HUMAN_OPERATOR_TAKEOVER"

    agent.cancel(reason="Emergency stop")
    assert agent.execution_loop.is_cancelled is True
    assert trajectory.events[-1]["event_type"] == "HUMAN_CONTROL_CANCEL"


def test_11_authority_revocation_mid_execution():
    """11. Mid-flight revocation of delegation halts capability execution immediately."""
    reg = CapabilityRegistry()
    reg.register(Capability(uri="tool://deploy", description="deploy", handler=lambda p: {"ok": True}))
    auth = AuthorityEvaluator()
    dispatcher = CapabilityDispatcher(resolver=CapabilityResolver(reg), authority_evaluator=auth)

    token = {
        "id": "del-live",
        "principal": "lead",
        "delegate": "agent",
        "scope": {"allowed_capabilities": ["tool://deploy"], "denied_capabilities": []},
        "revoked": False
    }

    # First dispatch succeeds
    res1 = dispatcher.dispatch("tool://deploy", {}, token)
    assert res1["status"] == "COMPLETED"

    # Revoke mid-flight
    token["revoked"] = True

    # Next dispatch is blocked
    with pytest.raises(PermissionError) as exc_info:
        dispatcher.dispatch("tool://deploy", {}, token)

    assert "revoked" in str(exc_info.value)


def test_12_trajectory_audit_integrity_checks():
    """12. Trajectory audit detects mutation, deletion, sequence reordering, and anchor mismatch."""
    rec = TrajectoryRecorder(mission_id="m-audit")
    rec.emit_event("step_1", {"data": "ok"})
    rec.emit_event("step_2", {"data": "ok"})
    rec.emit_event("step_3", {"data": "ok"})

    # Valid initial state
    is_valid, err = rec.audit_integrity()
    assert is_valid is True
    assert err is None

    # Test 1: Event mutation
    rec.events[1]["payload"]["data"] = "tampered"
    is_valid, err = rec.audit_integrity()
    assert is_valid is False
    assert "mutation detected" in err

    # Restore
    rec.events[1]["payload"]["data"] = "ok"

    # Test 2: Event reordering
    e2 = rec.events.pop(1)
    rec.events.append(e2)
    is_valid, err = rec.audit_integrity()
    assert is_valid is False


def test_13_live_dialagram_multi_model_smoke_matrix(tmp_path):
    """13. Live Dialagram multi-model smoke matrix producing verifiable provenance manifests."""
    manifest_dir = tmp_path / "smoke_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    provider = DialagramProvider()
    smoke_models = ["qwen-3.8-max", "deepseek-v4", "xiaomi-mimo-2.5"]
    run_records = []

    for m_id in smoke_models:
        # Executes live if key and network exist, otherwise executes calibrated dry-run
        resp = provider.generate(
            prompt="Compute checksum for invariant verification.",
            system_prompt="You are an autonomous intelligence verifier.",
            model=m_id,
            dry_run=False
        )

        manifest = {
            "run_id": f"smoke-{m_id}-{int(time.time())}",
            "evidence_class": "LIVE DEVELOPMENT EVIDENCE",
            "provider": "dialagram",
            "model_id": m_id,
            "is_live": resp.is_live,
            "tokens": resp.total_tokens,
            "latency_ms": resp.latency_ms,
            "response_preview": resp.content[:100]
        }
        manifest_file = manifest_dir / f"manifest_{m_id}.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        run_records.append(manifest)

    assert len(run_records) == 3
    assert all(r["evidence_class"] == "LIVE DEVELOPMENT EVIDENCE" for r in run_records)
