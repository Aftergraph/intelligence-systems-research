from __future__ import annotations

import hashlib
import json
import time
import uuid
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

from .audit import AuditLog
from .circuit_breaker import CircuitBreakerRegistry


class SubagentStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


class JoinMode(str, Enum):
    ALL = "all"
    QUORUM = "quorum"
    ANY = "any"
    BEST_N = "best_n"


@dataclass(frozen=True, slots=True)
class SubagentSpec:
    agent_id: str
    role: str
    allowed_tools: frozenset[str] = frozenset()
    context_keys: frozenset[str] = frozenset()
    max_retries: int = 1
    fallback_agent_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.agent_id.strip() or not self.role.strip():
            raise ValueError("agent_id and role must be non-empty")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")


@dataclass(frozen=True, slots=True)
class SubagentTask:
    task_id: str
    agent_id: str
    payload: Mapping[str, Any]
    dependencies: tuple[str, ...] = ()
    required_tools: frozenset[str] = frozenset()
    required_context_keys: frozenset[str] = frozenset()
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.agent_id.strip():
            raise ValueError("task_id and agent_id must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class SubagentOutcome:
    task_id: str
    agent_id: str
    trace_id: str
    span_id: str
    status: SubagentStatus
    output: Mapping[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    attempts: int = 1
    latency_ms: float = 0.0
    errors: tuple[str, ...] = ()
    tools_called: tuple[str, ...] = ()
    fallback_from: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class JoinPolicy:
    mode: JoinMode = JoinMode.ALL
    quorum: int | None = None
    best_n: int | None = None
    min_confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if self.mode is JoinMode.QUORUM and (self.quorum is None or self.quorum < 1):
            raise ValueError("quorum mode requires quorum >= 1")
        if self.mode is JoinMode.BEST_N and (self.best_n is None or self.best_n < 1):
            raise ValueError("best_n mode requires best_n >= 1")


@dataclass(frozen=True, slots=True)
class MultiAgentPlan:
    mission_id: str
    orchestrator_id: str
    agents: tuple[SubagentSpec, ...]
    tasks: tuple[SubagentTask, ...]
    join_policy: JoinPolicy = JoinPolicy()
    join_task_ids: tuple[str, ...] = ()
    max_parallelism: int = 4
    max_total_attempts: int = 64

    def __post_init__(self) -> None:
        if not self.mission_id.strip() or not self.orchestrator_id.strip():
            raise ValueError("mission_id and orchestrator_id must be non-empty")
        if self.max_parallelism < 1:
            raise ValueError("max_parallelism must be >= 1")
        if self.max_total_attempts < 1:
            raise ValueError("max_total_attempts must be >= 1")


@dataclass(frozen=True, slots=True)
class MultiAgentRunResult:
    mission_id: str
    trace_id: str
    accepted: bool
    degraded: bool
    outcomes: tuple[SubagentOutcome, ...]
    selected_task_ids: tuple[str, ...]
    failed_task_ids: tuple[str, ...]
    total_attempts: int
    latency_ms: float
    state_sha256: str


Executor = Callable[[SubagentSpec, SubagentTask, Mapping[str, Any], str, str], SubagentOutcome | Mapping[str, Any]]
Evaluator = Callable[[SubagentOutcome], tuple[bool, str]]


class _AttemptBudget:
    def __init__(self, value: int) -> None:
        self.remaining = value
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            if self.remaining <= 0:
                return False
            self.remaining -= 1
            return True


class MultiAgentOrchestrator:
    """Hierarchical orchestrator with bounded parallel fan-out and fail-closed joins.

    The orchestrator owns decomposition/scheduling/merge state. Subagents receive
    immutable, least-privilege context projections and cannot mutate shared state.
    """

    def __init__(
        self,
        *,
        executor: Executor,
        evaluator: Evaluator | None = None,
        audit: AuditLog | None = None,
        circuit_breakers: CircuitBreakerRegistry | None = None,
    ) -> None:
        self.executor = executor
        self.evaluator = evaluator or self._default_evaluator
        self.audit = audit or AuditLog()
        self.circuit_breakers = circuit_breakers or CircuitBreakerRegistry()

    @staticmethod
    def _default_evaluator(outcome: SubagentOutcome) -> tuple[bool, str]:
        ok = outcome.status is SubagentStatus.SUCCESS and outcome.confidence > 0.0
        return ok, "accepted" if ok else "outcome not successful/confident"

    @staticmethod
    def _hash_state(value: Any) -> str:
        blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    @staticmethod
    def _validate_plan(plan: MultiAgentPlan) -> tuple[dict[str, SubagentSpec], dict[str, SubagentTask]]:
        agents = {a.agent_id: a for a in plan.agents}
        tasks = {t.task_id: t for t in plan.tasks}
        if len(agents) != len(plan.agents):
            raise ValueError("duplicate agent_id")
        if len(tasks) != len(plan.tasks):
            raise ValueError("duplicate task_id")
        for join_task_id in plan.join_task_ids:
            if join_task_id not in tasks:
                raise ValueError(f"join references unknown task {join_task_id}")
        for task in plan.tasks:
            if task.agent_id not in agents:
                raise ValueError(f"task {task.task_id} references unknown agent {task.agent_id}")
            missing = [d for d in task.dependencies if d not in tasks]
            if missing:
                raise ValueError(f"task {task.task_id} has unknown dependencies: {missing}")
            spec = agents[task.agent_id]
            if not task.required_tools.issubset(spec.allowed_tools):
                raise PermissionError(f"task {task.task_id} requests tools outside agent scope")
            if not task.required_context_keys.issubset(spec.context_keys):
                raise PermissionError(f"task {task.task_id} requests context outside agent scope")
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError("task graph contains a cycle")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dep in tasks[task_id].dependencies:
                visit(dep)
            visiting.remove(task_id)
            visited.add(task_id)
        for task_id in tasks:
            visit(task_id)
        return agents, tasks

    @staticmethod
    def _freeze(value: Any) -> Any:
        if isinstance(value, Mapping):
            return MappingProxyType({str(k): MultiAgentOrchestrator._freeze(v) for k, v in value.items()})
        if isinstance(value, list):
            return tuple(MultiAgentOrchestrator._freeze(v) for v in value)
        if isinstance(value, tuple):
            return tuple(MultiAgentOrchestrator._freeze(v) for v in value)
        if isinstance(value, set):
            return frozenset(MultiAgentOrchestrator._freeze(v) for v in value)
        return value

    @staticmethod
    def _project_context(spec: SubagentSpec, task: SubagentTask, context: Mapping[str, Any]) -> Mapping[str, Any]:
        allowed = spec.context_keys.intersection(task.required_context_keys or spec.context_keys)
        projected = {key: context[key] for key in allowed if key in context}
        missing = task.required_context_keys.difference(projected)
        if missing:
            raise KeyError(f"missing required context for {task.task_id}: {sorted(missing)}")
        return MultiAgentOrchestrator._freeze(projected)

    def _normalize_outcome(
        self,
        raw: SubagentOutcome | Mapping[str, Any],
        *,
        task: SubagentTask,
        agent_id: str,
        trace_id: str,
        span_id: str,
        attempts: int,
        latency_ms: float,
        fallback_from: str | None,
    ) -> SubagentOutcome:
        if isinstance(raw, SubagentOutcome):
            return SubagentOutcome(
                task_id=task.task_id,
                agent_id=agent_id,
                trace_id=trace_id,
                span_id=span_id,
                status=raw.status,
                output=dict(raw.output),
                confidence=raw.confidence,
                attempts=attempts,
                latency_ms=latency_ms,
                errors=tuple(raw.errors),
                tools_called=tuple(raw.tools_called),
                fallback_from=fallback_from,
            )
        status = SubagentStatus(str(raw.get("status", "success")))
        return SubagentOutcome(
            task_id=task.task_id,
            agent_id=agent_id,
            trace_id=trace_id,
            span_id=span_id,
            status=status,
            output=dict(raw.get("output", {})),
            confidence=float(raw.get("confidence", 0.0)),
            attempts=attempts,
            latency_ms=latency_ms,
            errors=tuple(str(x) for x in raw.get("errors", ())),
            tools_called=tuple(str(x) for x in raw.get("tools_called", ())),
            fallback_from=fallback_from,
        )

    def _execute_task(
        self,
        *,
        task: SubagentTask,
        primary: SubagentSpec,
        agents: Mapping[str, SubagentSpec],
        context: Mapping[str, Any],
        trace_id: str,
        attempt_budget: _AttemptBudget,
    ) -> SubagentOutcome:
        route = primary.agent_id
        chain = [primary]
        if primary.fallback_agent_id:
            fallback = agents.get(primary.fallback_agent_id)
            if fallback is None:
                raise ValueError(f"unknown fallback agent {primary.fallback_agent_id}")
            if not task.required_tools.issubset(fallback.allowed_tools):
                raise PermissionError("fallback agent lacks required tools")
            if not task.required_context_keys.issubset(fallback.context_keys):
                raise PermissionError("fallback agent lacks required context scope")
            chain.append(fallback)

        last: SubagentOutcome | None = None
        fallback_from: str | None = None
        for spec in chain:
            if not self.circuit_breakers.allow(spec.agent_id):
                fallback_from = primary.agent_id
                continue
            projected = self._project_context(spec, task, context)
            for local_attempt in range(spec.max_retries + 1):
                if not attempt_budget.take():
                    return SubagentOutcome(
                        task.task_id, spec.agent_id, trace_id, str(uuid.uuid4()),
                        SubagentStatus.ESCALATED, confidence=0.0,
                        errors=("global attempt budget exhausted",), fallback_from=fallback_from,
                    )
                span_id = str(uuid.uuid4())
                started = time.perf_counter()
                self.audit.append(
                    "subagent.started", trace_id=trace_id, span_id=span_id,
                    task_id=task.task_id, agent_id=spec.agent_id, role=spec.role,
                    attempt=local_attempt + 1,
                    context_keys=sorted(projected.keys()), tools=sorted(task.required_tools),
                )
                try:
                    raw = self.executor(spec, task, projected, trace_id, span_id)
                    latency = (time.perf_counter() - started) * 1000.0
                    outcome = self._normalize_outcome(
                        raw, task=task, agent_id=spec.agent_id, trace_id=trace_id,
                        span_id=span_id, attempts=local_attempt + 1, latency_ms=latency,
                        fallback_from=fallback_from,
                    )
                except Exception as exc:
                    latency = (time.perf_counter() - started) * 1000.0
                    outcome = SubagentOutcome(
                        task_id=task.task_id, agent_id=spec.agent_id, trace_id=trace_id,
                        span_id=span_id, status=SubagentStatus.FAILURE, confidence=0.0,
                        attempts=local_attempt + 1, latency_ms=latency, errors=(str(exc),),
                        fallback_from=fallback_from,
                    )
                scope_errors: list[str] = []
                if latency > task.timeout_seconds * 1000.0:
                    scope_errors.append(f"soft_timeout_exceeded:{task.timeout_seconds}s")
                unauthorized_tools = sorted(set(outcome.tools_called).difference(spec.allowed_tools))
                if unauthorized_tools:
                    scope_errors.append(f"unauthorized_tools:{','.join(unauthorized_tools)}")
                if scope_errors:
                    outcome = SubagentOutcome(
                        task_id=outcome.task_id, agent_id=outcome.agent_id, trace_id=outcome.trace_id,
                        span_id=outcome.span_id, status=SubagentStatus.FAILURE, output=dict(outcome.output),
                        confidence=outcome.confidence, attempts=outcome.attempts, latency_ms=outcome.latency_ms,
                        errors=tuple(outcome.errors) + tuple(scope_errors), tools_called=outcome.tools_called,
                        fallback_from=outcome.fallback_from,
                    )
                valid, reason = self.evaluator(outcome)
                self.audit.append(
                    "subagent.completed", trace_id=trace_id, span_id=span_id,
                    task_id=task.task_id, agent_id=spec.agent_id,
                    status=outcome.status.value, confidence=outcome.confidence,
                    accepted=valid, evaluator_reason=reason,
                    output_sha256=self._hash_state(dict(outcome.output)),
                )
                if valid:
                    self.circuit_breakers.record_success(spec.agent_id)
                    return outcome
                self.circuit_breakers.record_failure(spec.agent_id)
                outcome = SubagentOutcome(
                    task_id=outcome.task_id, agent_id=outcome.agent_id, trace_id=outcome.trace_id,
                    span_id=outcome.span_id, status=SubagentStatus.FAILURE, output=dict(outcome.output),
                    confidence=outcome.confidence, attempts=outcome.attempts, latency_ms=outcome.latency_ms,
                    errors=tuple(outcome.errors) + (f"evaluator_rejected: {reason}",),
                    tools_called=outcome.tools_called, fallback_from=outcome.fallback_from,
                )
                last = outcome
            fallback_from = spec.agent_id
        assert last is not None
        return last

    @staticmethod
    def _select(outcomes: Iterable[SubagentOutcome], policy: JoinPolicy) -> tuple[bool, tuple[str, ...]]:
        candidates = [o for o in outcomes if o.status is SubagentStatus.SUCCESS and o.confidence >= policy.min_confidence]
        ranked = sorted(candidates, key=lambda o: (-o.confidence, o.task_id))
        if policy.mode is JoinMode.ALL:
            all_rows = list(outcomes)
            accepted = len(ranked) == len(all_rows) and bool(all_rows)
            return accepted, tuple(o.task_id for o in ranked) if accepted else ()
        if policy.mode is JoinMode.ANY:
            return bool(ranked), tuple([ranked[0].task_id]) if ranked else ()
        if policy.mode is JoinMode.QUORUM:
            assert policy.quorum is not None
            return len(ranked) >= policy.quorum, tuple(o.task_id for o in ranked[: policy.quorum])
        assert policy.best_n is not None
        return len(ranked) >= policy.best_n, tuple(o.task_id for o in ranked[: policy.best_n])

    def run(self, plan: MultiAgentPlan, *, context: Mapping[str, Any]) -> MultiAgentRunResult:
        started = time.perf_counter()
        trace_id = str(uuid.uuid4())
        agents, tasks = self._validate_plan(plan)
        pending = set(tasks)
        completed: dict[str, SubagentOutcome] = {}
        attempt_budget = _AttemptBudget(plan.max_total_attempts)
        self.audit.append(
            "multi_agent.started", mission_id=plan.mission_id, trace_id=trace_id,
            orchestrator_id=plan.orchestrator_id, task_count=len(tasks),
            max_parallelism=plan.max_parallelism, join_mode=plan.join_policy.mode.value,
        )

        while pending:
            ready = sorted(
                task_id for task_id in pending
                if all(dep in completed and completed[dep].status is SubagentStatus.SUCCESS for dep in tasks[task_id].dependencies)
            )
            if not ready:
                blocked = sorted(pending)
                for task_id in blocked:
                    task = tasks[task_id]
                    completed[task_id] = SubagentOutcome(
                        task_id, task.agent_id, trace_id, str(uuid.uuid4()),
                        SubagentStatus.BLOCKED, confidence=0.0,
                        errors=("dependency did not complete successfully",),
                    )
                break
            wave = ready[: plan.max_parallelism]
            with ThreadPoolExecutor(max_workers=min(plan.max_parallelism, len(wave))) as pool:
                futures = {}
                for task_id in wave:
                    task_obj = tasks[task_id]
                    task_context = dict(context)
                    if "dependency_outputs" in agents[task_obj.agent_id].context_keys:
                        task_context["dependency_outputs"] = {
                            dep: dict(completed[dep].output) for dep in task_obj.dependencies if dep in completed
                        }
                    future = pool.submit(
                        self._execute_task,
                        task=task_obj, primary=agents[task_obj.agent_id], agents=agents,
                        context=task_context, trace_id=trace_id, attempt_budget=attempt_budget,
                    )
                    futures[future] = task_id
                for future in as_completed(futures):
                    task_id = futures[future]
                    completed[task_id] = future.result()
                    pending.remove(task_id)

        ordered = tuple(completed[t.task_id] for t in plan.tasks if t.task_id in completed)
        join_ids = plan.join_task_ids or tuple(t.task_id for t in plan.tasks)
        join_outcomes = tuple(completed[task_id] for task_id in join_ids if task_id in completed)
        accepted, selected = self._select(join_outcomes, plan.join_policy)
        failed = tuple(o.task_id for o in ordered if o.status is not SubagentStatus.SUCCESS)
        degraded = bool(failed) and accepted
        state_sha = self._hash_state([
            {
                "task_id": o.task_id,
                "agent_id": o.agent_id,
                "status": o.status.value,
                "confidence": o.confidence,
                "output": dict(o.output),
                "fallback_from": o.fallback_from,
            }
            for o in ordered
        ])
        total_attempts = plan.max_total_attempts - attempt_budget.remaining
        latency = (time.perf_counter() - started) * 1000.0
        self.audit.append(
            "multi_agent.completed", mission_id=plan.mission_id, trace_id=trace_id,
            accepted=accepted, degraded=degraded, selected_task_ids=list(selected),
            failed_task_ids=list(failed), total_attempts=total_attempts, state_sha256=state_sha,
        )
        return MultiAgentRunResult(
            mission_id=plan.mission_id,
            trace_id=trace_id,
            accepted=accepted,
            degraded=degraded,
            outcomes=ordered,
            selected_task_ids=selected,
            failed_task_ids=failed,
            total_attempts=total_attempts,
            latency_ms=latency,
            state_sha256=state_sha,
        )