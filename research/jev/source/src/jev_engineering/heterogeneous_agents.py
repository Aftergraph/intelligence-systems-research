from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Mapping

from .multi_agent import MultiAgentPlan, SubagentOutcome, SubagentSpec, SubagentStatus, SubagentTask
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


class BackendKind(str, Enum):
    LOCAL = "local"
    PROVIDER = "provider"
    WORKER = "worker"


class TopologyMode(str, Enum):
    HIERARCHICAL = "hierarchical"
    PARALLEL = "parallel"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class BackendIdentity:
    backend_id: str
    kind: BackendKind
    provider: str
    model: str
    endpoint: str = ""
    authenticated: bool = False
    live_provider: bool = False
    capabilities: frozenset[str] = frozenset()
    competence: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_id.strip() or not self.provider.strip() or not self.model.strip():
            raise ValueError("backend_id, provider and model must be non-empty")
        for key, score in self.competence.items():
            if not 0.0 <= float(score) <= 1.0:
                raise ValueError(f"competence score for {key!r} must be between 0 and 1")
        if self.live_provider:
            if self.kind is not BackendKind.PROVIDER:
                raise ValueError("live_provider requires provider backend kind")
            if not self.authenticated:
                raise ValueError("live_provider requires authenticated backend")
            if not self.endpoint.lower().startswith("https://"):
                raise ValueError("live_provider requires https endpoint")


@dataclass(frozen=True, slots=True)
class BackendBinding:
    agent_id: str
    candidate_backend_ids: tuple[str, ...]
    required_capabilities: frozenset[str] = frozenset()
    competence_key: str | None = None
    min_competence: float = 0.0

    def __post_init__(self) -> None:
        if not self.agent_id.strip() or not self.candidate_backend_ids:
            raise ValueError("agent_id and at least one candidate backend are required")
        if len(set(self.candidate_backend_ids)) != len(self.candidate_backend_ids):
            raise ValueError("candidate_backend_ids must be unique")
        if not 0.0 <= self.min_competence <= 1.0:
            raise ValueError("min_competence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class BackendExecution:
    status: SubagentStatus
    output: Mapping[str, Any]
    confidence: float
    tools_called: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    provider_request_ids: tuple[str, ...] = ()
    evidence_origin: str = "local"
    authenticated: bool = False
    transport_security: str = "local"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


BackendExecutor = Callable[[BackendIdentity, SubagentSpec, SubagentTask, Mapping[str, Any], str, str], BackendExecution | Mapping[str, Any]]


class BackendRegistry:
    def __init__(self) -> None:
        self._rows: dict[str, tuple[BackendIdentity, BackendExecutor]] = {}

    def register(self, identity: BackendIdentity, executor: BackendExecutor) -> None:
        if identity.backend_id in self._rows:
            raise ValueError(f"duplicate backend_id {identity.backend_id}")
        self._rows[identity.backend_id] = (identity, executor)

    def get(self, backend_id: str) -> tuple[BackendIdentity, BackendExecutor]:
        try:
            return self._rows[backend_id]
        except KeyError as exc:
            raise KeyError(f"unknown backend_id {backend_id}") from exc

    def identity(self, backend_id: str) -> BackendIdentity:
        return self.get(backend_id)[0]


@dataclass(frozen=True, slots=True)
class RouteDecision:
    agent_id: str
    backend_id: str
    score: float
    considered_backend_ids: tuple[str, ...]
    reason: str


class CompetenceRouter:
    def __init__(self, registry: BackendRegistry, bindings: tuple[BackendBinding, ...]) -> None:
        self.registry = registry
        self.bindings = {binding.agent_id: binding for binding in bindings}
        if len(self.bindings) != len(bindings):
            raise ValueError("duplicate backend binding for agent_id")

    def select(self, spec: SubagentSpec) -> RouteDecision:
        try:
            binding = self.bindings[spec.agent_id]
        except KeyError as exc:
            raise KeyError(f"no backend binding for agent {spec.agent_id}") from exc
        candidates: list[tuple[float, str]] = []
        for backend_id in binding.candidate_backend_ids:
            identity = self.registry.identity(backend_id)
            if not binding.required_capabilities.issubset(identity.capabilities):
                continue
            score = 1.0 if binding.competence_key is None else float(identity.competence.get(binding.competence_key, 0.0))
            if score >= binding.min_competence:
                candidates.append((score, backend_id))
        if not candidates:
            raise RuntimeError(f"no eligible backend for agent {spec.agent_id}")
        candidates.sort(key=lambda row: (-row[0], row[1]))
        score, backend_id = candidates[0]
        return RouteDecision(
            agent_id=spec.agent_id,
            backend_id=backend_id,
            score=score,
            considered_backend_ids=tuple(binding.candidate_backend_ids),
            reason=("capability+competence" if binding.competence_key else "capability"),
        )


@dataclass(frozen=True, slots=True)
class TopologyDecision:
    requested: TopologyMode
    selected: TopologyMode
    max_parallelism: int
    independent_root_tasks: int
    reason: str


class DynamicTopologySelector:
    def __init__(self, *, parallel_threshold: int = 2, max_parallelism: int = 4) -> None:
        if parallel_threshold < 2 or max_parallelism < 1:
            raise ValueError("invalid topology selector limits")
        self.parallel_threshold = parallel_threshold
        self.max_parallelism = max_parallelism

    def select(self, plan: MultiAgentPlan, requested: TopologyMode = TopologyMode.AUTO) -> TopologyDecision:
        roots = sum(1 for task in plan.tasks if not task.dependencies)
        if requested is TopologyMode.AUTO:
            selected = TopologyMode.PARALLEL if roots >= self.parallel_threshold else TopologyMode.HIERARCHICAL
        else:
            selected = requested
        parallelism = 1 if selected is TopologyMode.HIERARCHICAL else min(self.max_parallelism, max(1, roots), plan.max_parallelism)
        return TopologyDecision(
            requested=requested,
            selected=selected,
            max_parallelism=parallelism,
            independent_root_tasks=roots,
            reason=("multiple independent roots" if selected is TopologyMode.PARALLEL else "dependency-dominant graph"),
        )

    def apply(self, plan: MultiAgentPlan, requested: TopologyMode = TopologyMode.AUTO) -> tuple[MultiAgentPlan, TopologyDecision]:
        decision = self.select(plan, requested)
        return replace(plan, max_parallelism=decision.max_parallelism), decision


@dataclass(frozen=True, slots=True)
class SignedSubagentReceipt:
    receipt: PublicSignedReceipt
    live_provider_evidence: bool


class HeterogeneousSubagentExecutor:
    """Routes agent roles to heterogeneous backends and emits signed per-agent receipts.

    A cryptographic signature authenticates the local receipt issuer only. Live-provider
    evidence additionally requires an authenticated HTTPS provider backend, provider-issued
    request lineage, and an explicit ``live-provider`` evidence origin.
    """

    def __init__(
        self,
        *,
        registry: BackendRegistry,
        router: CompetenceRouter,
        signer: Ed25519ReceiptSigner,
        persistent_signing_key: bool,
    ) -> None:
        self.registry = registry
        self.router = router
        self.signer = signer
        self.persistent_signing_key = persistent_signing_key
        self._receipts: list[SignedSubagentReceipt] = []
        self._routes: list[RouteDecision] = []
        self._lock = threading.Lock()

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()

    @property
    def receipts(self) -> tuple[SignedSubagentReceipt, ...]:
        with self._lock:
            return tuple(self._receipts)

    @property
    def routes(self) -> tuple[RouteDecision, ...]:
        with self._lock:
            return tuple(self._routes)

    @staticmethod
    def _normalize(raw: BackendExecution | Mapping[str, Any]) -> BackendExecution:
        if isinstance(raw, BackendExecution):
            return raw
        return BackendExecution(
            status=SubagentStatus(str(raw.get("status", "success"))),
            output=dict(raw.get("output", {})),
            confidence=float(raw.get("confidence", 0.0)),
            tools_called=tuple(str(x) for x in raw.get("tools_called", ())),
            errors=tuple(str(x) for x in raw.get("errors", ())),
            provider_request_ids=tuple(str(x) for x in raw.get("provider_request_ids", ())),
            evidence_origin=str(raw.get("evidence_origin", "local")),
            authenticated=bool(raw.get("authenticated", False)),
            transport_security=str(raw.get("transport_security", "local")),
        )

    def __call__(
        self,
        spec: SubagentSpec,
        task: SubagentTask,
        context: Mapping[str, Any],
        trace_id: str,
        span_id: str,
    ) -> SubagentOutcome:
        route = self.router.select(spec)
        identity, executor = self.registry.get(route.backend_id)
        execution = self._normalize(executor(identity, spec, task, context, trace_id, span_id))

        live_evidence = (
            self.persistent_signing_key
            and identity.live_provider
            and identity.authenticated
            and execution.authenticated
            and execution.transport_security.lower() == "https"
            and execution.evidence_origin == "live-provider"
            and bool(execution.provider_request_ids)
        )
        if identity.live_provider and not live_evidence:
            execution = BackendExecution(
                status=SubagentStatus.FAILURE,
                output=dict(execution.output),
                confidence=execution.confidence,
                tools_called=execution.tools_called,
                errors=execution.errors + ("invalid_live_provider_attestation",),
                provider_request_ids=execution.provider_request_ids,
                evidence_origin=execution.evidence_origin,
                authenticated=execution.authenticated,
                transport_security=execution.transport_security,
            )

        payload = {
            "schema": "aftergraph.subagent-execution-receipt/1.0",
            "task_id": task.task_id,
            "agent_id": spec.agent_id,
            "role": spec.role,
            "backend": {
                "backend_id": identity.backend_id,
                "kind": identity.kind.value,
                "provider": identity.provider,
                "model": identity.model,
                "endpoint": identity.endpoint,
                "authenticated": identity.authenticated,
                "live_provider": identity.live_provider,
            },
            "trace_id": trace_id,
            "span_id": span_id,
            "input_sha256": self._hash({"payload": dict(task.payload), "context": dict(context)}),
            "output_sha256": self._hash(dict(execution.output)),
            "status": execution.status.value,
            "confidence": execution.confidence,
            "tools_called": list(execution.tools_called),
            "provider_request_ids": list(execution.provider_request_ids),
            "evidence_origin": execution.evidence_origin,
            "authenticated": execution.authenticated,
            "transport_security": execution.transport_security,
            "persistent_signing_key": self.persistent_signing_key,
            "live_provider_evidence": live_evidence,
        }
        signed = SignedSubagentReceipt(self.signer.sign(payload), live_evidence)
        with self._lock:
            self._routes.append(route)
            self._receipts.append(signed)
        return SubagentOutcome(
            task_id=task.task_id,
            agent_id=spec.agent_id,
            trace_id=trace_id,
            span_id=span_id,
            status=execution.status,
            output=dict(execution.output),
            confidence=execution.confidence,
            errors=execution.errors,
            tools_called=execution.tools_called,
        )

    def verify_receipts(self) -> bool:
        verifier = Ed25519ReceiptVerifier({self.signer.key_id: self.signer.public_key_bytes()})
        return all(verifier.verify(row.receipt) for row in self.receipts)

    @property
    def authenticated_live_provider_execution(self) -> bool:
        receipts = self.receipts
        return bool(receipts) and all(row.live_provider_evidence for row in receipts)