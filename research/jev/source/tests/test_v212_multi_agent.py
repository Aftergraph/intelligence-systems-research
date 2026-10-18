from __future__ import annotations

import time
from collections import defaultdict

import pytest

from jev_engineering.multi_agent import (
    JoinMode,
    JoinPolicy,
    MultiAgentOrchestrator,
    MultiAgentPlan,
    SubagentOutcome,
    SubagentSpec,
    SubagentStatus,
    SubagentTask,
)


def agent(agent_id: str, *, tools=(), ctx=(), retries=0, fallback=None):
    return SubagentSpec(
        agent_id=agent_id,
        role=agent_id,
        allowed_tools=frozenset(tools),
        context_keys=frozenset(ctx),
        max_retries=retries,
        fallback_agent_id=fallback,
    )


def task(task_id: str, agent_id: str, *, deps=(), tools=(), ctx=(), payload=None):
    return SubagentTask(
        task_id=task_id,
        agent_id=agent_id,
        payload=payload or {},
        dependencies=tuple(deps),
        required_tools=frozenset(tools),
        required_context_keys=frozenset(ctx),
    )


def plan(*, agents, tasks, policy=JoinPolicy(), parallel=4, budget=64):
    return MultiAgentPlan(
        mission_id="m1",
        orchestrator_id="orch",
        agents=tuple(agents),
        tasks=tuple(tasks),
        join_policy=policy,
        max_parallelism=parallel,
        max_total_attempts=budget,
    )


def success_executor(spec, t, context, trace_id, span_id):
    return {"status": "success", "confidence": 0.9, "output": {"task": t.task_id, "agent": spec.agent_id}}


def test_single_task_success():
    result = MultiAgentOrchestrator(executor=success_executor).run(
        plan(agents=[agent("a")], tasks=[task("t", "a")]), context={}
    )
    assert result.accepted
    assert result.selected_task_ids == ("t",)
    assert result.outcomes[0].trace_id == result.trace_id


def test_duplicate_agent_rejected():
    with pytest.raises(ValueError, match="duplicate agent_id"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a"), agent("a")], tasks=[task("t", "a")]), context={}
        )


def test_duplicate_task_rejected():
    with pytest.raises(ValueError, match="duplicate task_id"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a")], tasks=[task("t", "a"), task("t", "a")]), context={}
        )


def test_unknown_agent_rejected():
    with pytest.raises(ValueError, match="unknown agent"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a")], tasks=[task("t", "b")]), context={}
        )


def test_unknown_dependency_rejected():
    with pytest.raises(ValueError, match="unknown dependencies"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a")], tasks=[task("t", "a", deps=("missing",))]), context={}
        )


def test_cycle_rejected():
    with pytest.raises(ValueError, match="cycle"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a")], tasks=[task("a", "a", deps=("b",)), task("b", "a", deps=("a",))]), context={}
        )


def test_tool_scope_is_fail_closed():
    with pytest.raises(PermissionError, match="tools outside agent scope"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a", tools=("read",))], tasks=[task("t", "a", tools=("write",))]), context={}
        )


def test_context_scope_is_fail_closed():
    with pytest.raises(PermissionError, match="context outside agent scope"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a", ctx=("public",))], tasks=[task("t", "a", ctx=("secret",))]), context={"secret": "x"}
        )


def test_missing_required_context_is_fail_closed():
    with pytest.raises(KeyError, match="missing required context"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(agents=[agent("a", ctx=("x",))], tasks=[task("t", "a", ctx=("x",))]), context={}
        )


def test_context_projection_excludes_unscoped_fields():
    seen = {}
    def executor(spec, t, context, trace_id, span_id):
        seen.update(context)
        return {"status": "success", "confidence": 1.0, "output": {}}
    MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a", ctx=("allowed",))], tasks=[task("t", "a", ctx=("allowed",))]),
        context={"allowed": 1, "secret": 2},
    )
    assert seen == {"allowed": 1}


def test_nested_context_is_immutable():
    def executor(spec, t, context, trace_id, span_id):
        with pytest.raises(TypeError):
            context["cfg"]["x"] = 2
        return {"status": "success", "confidence": 1.0, "output": {}}
    MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a", ctx=("cfg",))], tasks=[task("t", "a", ctx=("cfg",))]), context={"cfg": {"x": 1}}
    )


def test_dependencies_execute_after_parent_success():
    order = []
    def executor(spec, t, context, trace_id, span_id):
        order.append(t.task_id)
        return {"status": "success", "confidence": 1.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[task("root", "a"), task("child", "a", deps=("root",))]), context={}
    )
    assert result.accepted
    assert order == ["root", "child"]


def test_failed_dependency_blocks_descendant():
    def executor(spec, t, context, trace_id, span_id):
        if t.task_id == "root":
            return {"status": "failure", "confidence": 0.0, "output": {}}
        raise AssertionError("blocked child must not run")
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[task("root", "a"), task("child", "a", deps=("root",))]), context={}
    )
    assert not result.accepted
    assert result.outcomes[1].status is SubagentStatus.BLOCKED


def test_independent_tasks_run_in_parallel():
    started = []
    def executor(spec, t, context, trace_id, span_id):
        started.append(time.perf_counter())
        time.sleep(0.08)
        return {"status": "success", "confidence": 1.0, "output": {}}
    before = time.perf_counter()
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a"), agent("b")], tasks=[task("t1", "a"), task("t2", "b")], parallel=2), context={}
    )
    elapsed = time.perf_counter() - before
    assert result.accepted
    assert elapsed < 0.15
    assert abs(started[0] - started[1]) < 0.05


def test_parallelism_limit_is_respected():
    active = 0
    peak = 0
    import threading
    lock = threading.Lock()
    def executor(spec, t, context, trace_id, span_id):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return {"status": "success", "confidence": 1.0, "output": {}}
    MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent(str(i)) for i in range(4)],
            tasks=[task(f"t{i}", str(i)) for i in range(4)],
            parallel=2,
        ), context={}
    )
    assert peak == 2


def test_retry_then_success():
    calls = defaultdict(int)
    def executor(spec, t, context, trace_id, span_id):
        calls[spec.agent_id] += 1
        if calls[spec.agent_id] == 1:
            return {"status": "failure", "confidence": 0.0, "output": {}}
        return {"status": "success", "confidence": 0.8, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a", retries=1)], tasks=[task("t", "a")]), context={}
    )
    assert result.accepted
    assert calls["a"] == 2


def test_fallback_agent_runs_after_primary_exhausted():
    calls = []
    def executor(spec, t, context, trace_id, span_id):
        calls.append(spec.agent_id)
        if spec.agent_id == "primary":
            return {"status": "failure", "confidence": 0.0, "output": {}}
        return {"status": "success", "confidence": 0.7, "output": {"fallback": True}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("primary", fallback="fallback"), agent("fallback")],
            tasks=[task("t", "primary")],
        ), context={}
    )
    assert result.accepted
    assert calls == ["primary", "fallback"]
    assert result.outcomes[0].fallback_from == "primary"


def test_fallback_must_have_tool_scope():
    with pytest.raises(PermissionError, match="fallback agent lacks required tools"):
        MultiAgentOrchestrator(executor=success_executor).run(
            plan(
                agents=[agent("primary", tools=("read",), fallback="fallback"), agent("fallback")],
                tasks=[task("t", "primary", tools=("read",))],
            ), context={}
        )


def test_global_attempt_budget_escalates():
    def executor(spec, t, context, trace_id, span_id):
        return {"status": "failure", "confidence": 0.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a", retries=5)], tasks=[task("t", "a")], budget=2), context={}
    )
    assert not result.accepted
    assert result.total_attempts == 2
    assert result.outcomes[0].status is SubagentStatus.ESCALATED


def test_custom_evaluator_can_reject_success():
    def evaluator(outcome):
        return False, "schema invalid"
    result = MultiAgentOrchestrator(executor=success_executor, evaluator=evaluator).run(
        plan(agents=[agent("a")], tasks=[task("t", "a")]), context={}
    )
    assert not result.accepted


def test_all_join_requires_every_task():
    def executor(spec, t, context, trace_id, span_id):
        ok = t.task_id != "bad"
        return {"status": "success" if ok else "failure", "confidence": 0.9 if ok else 0.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[task("good", "a"), task("bad", "a")]), context={}
    )
    assert not result.accepted


def test_any_join_accepts_one_success_and_marks_degraded():
    def executor(spec, t, context, trace_id, span_id):
        ok = t.task_id == "good"
        return {"status": "success" if ok else "failure", "confidence": 0.9 if ok else 0.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("a")], tasks=[task("good", "a"), task("bad", "a")],
            policy=JoinPolicy(JoinMode.ANY),
        ), context={}
    )
    assert result.accepted and result.degraded
    assert result.selected_task_ids == ("good",)


def test_quorum_join_enforces_threshold():
    def executor(spec, t, context, trace_id, span_id):
        ok = t.task_id != "bad"
        return {"status": "success" if ok else "failure", "confidence": 0.8 if ok else 0.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("a")], tasks=[task("g1", "a"), task("g2", "a"), task("bad", "a")],
            policy=JoinPolicy(JoinMode.QUORUM, quorum=2),
        ), context={}
    )
    assert result.accepted and result.degraded
    assert len(result.selected_task_ids) == 2


def test_best_n_prefers_highest_confidence():
    scores = {"a": 0.2, "b": 0.9, "c": 0.7}
    def executor(spec, t, context, trace_id, span_id):
        return {"status": "success", "confidence": scores[t.task_id], "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("x")], tasks=[task("a", "x"), task("b", "x"), task("c", "x")],
            policy=JoinPolicy(JoinMode.BEST_N, best_n=2),
        ), context={}
    )
    assert result.selected_task_ids == ("b", "c")


def test_min_confidence_filters_join_candidates():
    def executor(spec, t, context, trace_id, span_id):
        return {"status": "success", "confidence": 0.4, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("a")], tasks=[task("t", "a")],
            policy=JoinPolicy(JoinMode.ANY, min_confidence=0.5),
        ), context={}
    )
    assert not result.accepted


def test_audit_has_shared_trace_and_distinct_spans():
    orch = MultiAgentOrchestrator(executor=success_executor)
    result = orch.run(
        plan(agents=[agent("a")], tasks=[task("t1", "a"), task("t2", "a")]), context={}
    )
    starts = [e for e in orch.audit.events if e["type"] == "subagent.started"]
    assert {e["trace_id"] for e in starts} == {result.trace_id}
    assert len({e["span_id"] for e in starts}) == 2


def test_state_hash_is_stable_for_same_semantic_results():
    r1 = MultiAgentOrchestrator(executor=success_executor).run(
        plan(agents=[agent("a")], tasks=[task("t", "a")]), context={}
    )
    r2 = MultiAgentOrchestrator(executor=success_executor).run(
        plan(agents=[agent("a")], tasks=[task("t", "a")]), context={}
    )
    assert r1.state_sha256 == r2.state_sha256


def test_outcome_trace_and_span_from_executor_are_rebound_to_orchestrator():
    def executor(spec, t, context, trace_id, span_id):
        return SubagentOutcome(
            task_id="wrong", agent_id="wrong", trace_id="wrong", span_id="wrong",
            status=SubagentStatus.SUCCESS, output={"ok": True}, confidence=1.0,
        )
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[task("t", "a")]), context={}
    )
    out = result.outcomes[0]
    assert out.task_id == "t" and out.agent_id == "a"
    assert out.trace_id == result.trace_id and out.span_id != "wrong"


def test_join_policy_validates_parameters():
    with pytest.raises(ValueError):
        JoinPolicy(JoinMode.QUORUM, quorum=0)
    with pytest.raises(ValueError):
        JoinPolicy(JoinMode.BEST_N, best_n=0)
    with pytest.raises(ValueError):
        JoinPolicy(JoinMode.ANY, min_confidence=1.1)


def test_dependency_outputs_are_available_only_when_scoped():
    seen = {}
    def executor(spec, t, context, trace_id, span_id):
        if t.task_id == "root":
            return {"status": "success", "confidence": 1.0, "output": {"value": 7}}
        seen.update(context["dependency_outputs"])
        return {"status": "success", "confidence": 1.0, "output": {}}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(
            agents=[agent("root"), agent("child", ctx=("dependency_outputs",))],
            tasks=[task("root", "root"), task("child", "child", deps=("root",))],
        ), context={}
    )
    assert result.accepted
    assert seen == {"root": {"value": 7}}


def test_unscoped_dependency_outputs_are_not_visible():
    def executor(spec, t, context, trace_id, span_id):
        if t.task_id == "root":
            return {"status": "success", "confidence": 1.0, "output": {"secret": 7}}
        assert "dependency_outputs" not in context
        return {"status": "success", "confidence": 1.0, "output": {}}
    MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[task("root", "a"), task("child", "a", deps=("root",))]), context={}
    )


def test_unauthorized_reported_tool_call_fails_closed():
    def executor(spec, t, context, trace_id, span_id):
        return {"status": "success", "confidence": 1.0, "output": {}, "tools_called": ["write"]}
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a", tools=("read",))], tasks=[task("t", "a")]), context={}
    )
    assert not result.accepted
    assert "unauthorized_tools:write" in result.outcomes[0].errors


def test_soft_timeout_fails_outcome_after_return():
    def executor(spec, t, context, trace_id, span_id):
        time.sleep(0.02)
        return {"status": "success", "confidence": 1.0, "output": {}}
    slow_task = SubagentTask("t", "a", {}, timeout_seconds=0.005)
    result = MultiAgentOrchestrator(executor=executor).run(
        plan(agents=[agent("a")], tasks=[slow_task]), context={}
    )
    assert not result.accepted
    assert any("soft_timeout_exceeded" in e for e in result.outcomes[0].errors)


def test_join_can_scope_to_terminal_tasks_only():
    def executor(spec, t, context, trace_id, span_id):
        confidence = 0.1 if t.task_id == "prep" else 0.9
        return {"status": "success", "confidence": confidence, "output": {}}
    p = MultiAgentPlan(
        mission_id="m1", orchestrator_id="orch",
        agents=(agent("a"),),
        tasks=(task("prep", "a"), task("final", "a", deps=("prep",))),
        join_policy=JoinPolicy(JoinMode.ANY, min_confidence=0.5),
        join_task_ids=("final",),
    )
    result = MultiAgentOrchestrator(executor=executor).run(p, context={})
    assert result.accepted
    assert result.selected_task_ids == ("final",)


def test_unknown_join_task_is_rejected():
    p = MultiAgentPlan(
        mission_id="m1", orchestrator_id="orch",
        agents=(agent("a"),), tasks=(task("t", "a"),), join_task_ids=("missing",),
    )
    with pytest.raises(ValueError, match="join references unknown task"):
        MultiAgentOrchestrator(executor=success_executor).run(p, context={})