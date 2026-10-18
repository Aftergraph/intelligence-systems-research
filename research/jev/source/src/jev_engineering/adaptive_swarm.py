from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .heterogeneous_agents import (
    BackendBinding,
    BackendIdentity,
    BackendRegistry,
    CompetenceRouter,
    HeterogeneousSubagentExecutor,
    RouteDecision,
    SignedSubagentReceipt,
    TopologyDecision,
    TopologyMode,
)
from .multi_agent import MultiAgentPlan, SubagentSpec
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


@dataclass(frozen=True, slots=True)
class VerifiedOutcome:
    backend_id: str
    competence_key: str
    success: bool
    quality: float
    verifier_ids: tuple[str, ...]
    evidence_sha256: str
    live_provider_evidence: bool = False

    def __post_init__(self) -> None:
        if not self.backend_id or not self.competence_key:
            raise ValueError("backend_id and competence_key are required")
        if not 0.0 <= self.quality <= 1.0:
            raise ValueError("quality must be between 0 and 1")
        if len(set(self.verifier_ids)) < 2:
            raise ValueError("verified outcome requires at least two independent verifiers")
        if len(self.evidence_sha256) != 64:
            raise ValueError("evidence_sha256 must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class CompetenceObservation:
    backend_id: str
    competence_key: str
    prior: float
    observed: float
    updated: float
    evidence_sha256: str
    verifier_ids: tuple[str, ...]


class CompetenceLedger:
    """Bounded competence learning from independently verified outcomes only."""

    def __init__(self, *, alpha: float = 0.2, floor: float = 0.0, ceiling: float = 1.0) -> None:
        if not 0.0 < alpha <= 1.0 or not 0.0 <= floor <= ceiling <= 1.0:
            raise ValueError("invalid competence ledger bounds")
        self.alpha = alpha
        self.floor = floor
        self.ceiling = ceiling
        self._scores: dict[tuple[str, str], float] = {}
        self._history: list[CompetenceObservation] = []
        self._seen_evidence: set[str] = set()
        self._lock = threading.Lock()

    def seed(self, backend: BackendIdentity) -> None:
        with self._lock:
            for key, value in backend.competence.items():
                self._scores.setdefault((backend.backend_id, key), float(value))

    def score(self, backend: BackendIdentity, key: str) -> float:
        with self._lock:
            return self._scores.get((backend.backend_id, key), float(backend.competence.get(key, 0.0)))

    def apply(self, outcome: VerifiedOutcome) -> CompetenceObservation:
        with self._lock:
            if outcome.evidence_sha256 in self._seen_evidence:
                raise ValueError("duplicate verified outcome evidence")
            self._seen_evidence.add(outcome.evidence_sha256)
            k = (outcome.backend_id, outcome.competence_key)
            prior = self._scores.get(k, 0.0)
            observed = outcome.quality if outcome.success else 0.0
            updated = min(self.ceiling, max(self.floor, (1.0 - self.alpha) * prior + self.alpha * observed))
            self._scores[k] = updated
            row = CompetenceObservation(
                backend_id=outcome.backend_id,
                competence_key=outcome.competence_key,
                prior=prior,
                observed=observed,
                updated=updated,
                evidence_sha256=outcome.evidence_sha256,
                verifier_ids=outcome.verifier_ids,
            )
            self._history.append(row)
            return row

    @property
    def history(self) -> tuple[CompetenceObservation, ...]:
        with self._lock:
            return tuple(self._history)


class AdaptiveCompetenceRouter(CompetenceRouter):
    def __init__(self, registry: BackendRegistry, bindings: tuple[BackendBinding, ...], ledger: CompetenceLedger) -> None:
        super().__init__(registry, bindings)
        self.ledger = ledger
        for backend_id in {bid for binding in bindings for bid in binding.candidate_backend_ids}:
            self.ledger.seed(registry.identity(backend_id))

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
            score = 1.0 if binding.competence_key is None else self.ledger.score(identity, binding.competence_key)
            if score >= binding.min_competence:
                candidates.append((score, backend_id))
        if not candidates:
            raise RuntimeError(f"no eligible backend for agent {spec.agent_id}")
        candidates.sort(key=lambda row: (-row[0], row[1]))
        score, backend_id = candidates[0]
        return RouteDecision(spec.agent_id, backend_id, score, tuple(binding.candidate_backend_ids), "verified-outcome competence")


@dataclass(frozen=True, slots=True)
class ReceiptChainLink:
    index: int
    receipt_sha256: str
    previous_link_sha256: str | None
    link_sha256: str
    backend_id: str
    provider: str
    live_provider_evidence: bool


class CrossProviderReceiptChain:
    """Hash chain over already-signed subagent receipts; does not elevate evidence class."""

    def __init__(self, signer: Ed25519ReceiptSigner) -> None:
        self.signer = signer
        self._links: list[ReceiptChainLink] = []

    @staticmethod
    def _sha(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

    def append(self, row: SignedSubagentReceipt) -> ReceiptChainLink:
        payload = row.receipt.payload
        receipt_sha = self._sha({
            "payload": payload,
            "payload_sha256": row.receipt.payload_sha256,
            "signature_b64": row.receipt.signature_b64,
            "key_id": row.receipt.key_id,
        })
        previous = self._links[-1].link_sha256 if self._links else None
        body = {
            "index": len(self._links),
            "receipt_sha256": receipt_sha,
            "previous_link_sha256": previous,
            "backend_id": payload["backend"]["backend_id"],
            "provider": payload["backend"]["provider"],
            "live_provider_evidence": row.live_provider_evidence,
        }
        link = ReceiptChainLink(
            index=body["index"], receipt_sha256=receipt_sha, previous_link_sha256=previous,
            link_sha256=self._sha(body), backend_id=body["backend_id"], provider=body["provider"],
            live_provider_evidence=row.live_provider_evidence,
        )
        self._links.append(link)
        return link

    @property
    def links(self) -> tuple[ReceiptChainLink, ...]:
        return tuple(self._links)

    @property
    def all_live(self) -> bool:
        return bool(self._links) and all(link.live_provider_evidence for link in self._links)

    def seal(self) -> PublicSignedReceipt:
        return self.signer.sign({
            "schema": "aftergraph.cross-provider-receipt-chain/1.0",
            "links": [link.__dict__ if hasattr(link, "__dict__") else {
                "index": link.index, "receipt_sha256": link.receipt_sha256,
                "previous_link_sha256": link.previous_link_sha256, "link_sha256": link.link_sha256,
                "backend_id": link.backend_id, "provider": link.provider,
                "live_provider_evidence": link.live_provider_evidence,
            } for link in self._links],
            "all_live": self.all_live,
        })

    def verify(self, receipt: PublicSignedReceipt) -> bool:
        verifier = Ed25519ReceiptVerifier({self.signer.key_id: self.signer.public_key_bytes()})
        if not verifier.verify(receipt):
            return False
        previous = None
        for index, row in enumerate(receipt.payload.get("links", [])):
            if row.get("index") != index or row.get("previous_link_sha256") != previous:
                return False
            body = {k: row[k] for k in ("index", "receipt_sha256", "previous_link_sha256", "backend_id", "provider", "live_provider_evidence")}
            if self._sha(body) != row.get("link_sha256"):
                return False
            previous = row["link_sha256"]
        return bool(receipt.payload.get("links"))


@dataclass(frozen=True, slots=True)
class TopologyRewriteDecision:
    from_mode: TopologyMode
    to_mode: TopologyMode
    reason: str
    max_parallelism: int


class AdaptiveTopologyRewriter:
    """Rewrites concurrency only; never changes agents, dependencies, scopes, or bindings."""

    def __init__(self, *, failure_threshold: float = 0.25, max_parallelism: int = 4) -> None:
        if not 0.0 <= failure_threshold <= 1.0 or max_parallelism < 1:
            raise ValueError("invalid topology rewrite policy")
        self.failure_threshold = failure_threshold
        self.max_parallelism = max_parallelism

    def rewrite(self, plan: MultiAgentPlan, *, recent_successes: int, recent_failures: int, current: TopologyMode) -> tuple[MultiAgentPlan, TopologyRewriteDecision]:
        total = recent_successes + recent_failures
        failure_rate = (recent_failures / total) if total else 0.0
        roots = sum(1 for task in plan.tasks if not task.dependencies)
        if failure_rate > self.failure_threshold:
            selected = TopologyMode.HIERARCHICAL
            parallelism = 1
            reason = "verified failure rate exceeded threshold"
        elif roots >= 2:
            selected = TopologyMode.PARALLEL
            parallelism = min(self.max_parallelism, roots, plan.max_parallelism)
            reason = "verified outcomes permit bounded independent fan-out"
        else:
            selected = TopologyMode.HIERARCHICAL
            parallelism = 1
            reason = "dependency-dominant graph"
        decision = TopologyRewriteDecision(current, selected, reason, parallelism)
        return replace(plan, max_parallelism=parallelism), decision