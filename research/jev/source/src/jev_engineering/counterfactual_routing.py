from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from .adaptive_swarm import AdaptiveCompetenceRouter, VerifiedOutcome
from .heterogeneous_agents import BackendRegistry, RouteDecision, TopologyMode
from .multi_agent import SubagentSpec


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CounterfactualEstimate:
    estimate_id: str
    agent_id: str
    selected_backend_id: str
    alternate_backend_id: str
    predicted_success: float
    modeled_only: bool = True


class CounterfactualRouter:
    """Produces explicitly modeled alternatives; never reports them as measured."""
    def __init__(self, router: AdaptiveCompetenceRouter, registry: BackendRegistry) -> None:
        self.router = router
        self.registry = registry

    def estimate(self, spec: SubagentSpec) -> tuple[RouteDecision, tuple[CounterfactualEstimate, ...]]:
        selected = self.router.select(spec)
        binding = self.router.bindings[spec.agent_id]
        rows=[]
        for backend_id in binding.candidate_backend_ids:
            if backend_id == selected.backend_id:
                continue
            identity=self.registry.identity(backend_id)
            if not binding.required_capabilities.issubset(identity.capabilities):
                continue
            score=1.0 if binding.competence_key is None else self.router.ledger.score(identity,binding.competence_key)
            rows.append(CounterfactualEstimate(
                estimate_id=_sha([spec.agent_id, selected.backend_id, backend_id, round(score,8)]),
                agent_id=spec.agent_id, selected_backend_id=selected.backend_id,
                alternate_backend_id=backend_id, predicted_success=max(0.0,min(1.0,score)), modeled_only=True,
            ))
        return selected, tuple(sorted(rows,key=lambda x:(-x.predicted_success,x.alternate_backend_id)))


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    estimate_id: str
    predicted: float
    observed: float
    brier_score: float
    evidence_sha256: str


class CalibrationLedger:
    def __init__(self) -> None:
        self._estimates: dict[str, CounterfactualEstimate] = {}
        self._resolved: set[str] = set()
        self._results: list[CalibrationResult] = []

    def register(self, estimate: CounterfactualEstimate) -> None:
        self._estimates.setdefault(estimate.estimate_id, estimate)

    def resolve(self, estimate_id: str, outcome: VerifiedOutcome) -> CalibrationResult:
        if estimate_id in self._resolved:
            raise ValueError("counterfactual estimate already resolved")
        estimate=self._estimates[estimate_id]
        if outcome.backend_id != estimate.alternate_backend_id:
            raise ValueError("verified outcome backend does not match counterfactual challenger")
        observed=outcome.quality if outcome.success else 0.0
        result=CalibrationResult(estimate_id, estimate.predicted_success, observed, (estimate.predicted_success-observed)**2, outcome.evidence_sha256)
        self._resolved.add(estimate_id); self._results.append(result); return result

    @property
    def mean_brier_score(self) -> float | None:
        return None if not self._results else sum(x.brier_score for x in self._results)/len(self._results)


@dataclass(frozen=True, slots=True)
class ShadowObservation:
    task_id: str
    primary_backend_id: str
    challenger_backend_id: str
    measured_shadow: bool
    independently_verified: bool
    evidence_sha256: str | None

    @property
    def eligible_for_learning(self) -> bool:
        return self.measured_shadow and self.independently_verified and bool(self.evidence_sha256)


@dataclass(frozen=True, slots=True)
class DecayedCompetence:
    raw_score: float
    decayed_score: float
    epochs_since_verified: int


class CompetenceDecayPolicy:
    def __init__(self, *, prior: float = 0.5, retention_per_epoch: float = 0.98) -> None:
        if not 0 <= prior <= 1 or not 0 < retention_per_epoch <= 1:
            raise ValueError("invalid decay policy")
        self.prior=prior; self.retention=retention_per_epoch

    def apply(self, score: float, epochs_since_verified: int) -> DecayedCompetence:
        if not 0 <= score <= 1 or epochs_since_verified < 0:
            raise ValueError("invalid competence decay input")
        weight=self.retention**epochs_since_verified
        decayed=self.prior+(score-self.prior)*weight
        return DecayedCompetence(score, max(0.0,min(1.0,decayed)), epochs_since_verified)


@dataclass(frozen=True, slots=True)
class TopologyOutcome:
    workload_class: str
    topology: TopologyMode
    success: bool
    quality: float
    verifier_ids: tuple[str,...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if len(set(self.verifier_ids)) < 2: raise ValueError("topology outcome requires two independent verifiers")
        if not 0 <= self.quality <= 1: raise ValueError("quality out of range")


class TopologyOutcomeMemory:
    def __init__(self) -> None:
        self._rows: list[TopologyOutcome]=[]; self._seen:set[str]=set()
    def record(self,row:TopologyOutcome)->None:
        if row.evidence_sha256 in self._seen: raise ValueError("duplicate topology evidence")
        self._seen.add(row.evidence_sha256); self._rows.append(row)
    def score(self, workload_class:str, topology:TopologyMode)->float|None:
        rows=[r for r in self._rows if r.workload_class==workload_class and r.topology is topology]
        if not rows: return None
        vals=[r.quality if r.success else 0.0 for r in rows]
        return sum(vals)/len(vals)
    def preferred(self, workload_class:str, fallback:TopologyMode=TopologyMode.HIERARCHICAL)->TopologyMode:
        scored=[(self.score(workload_class,t),t) for t in (TopologyMode.HIERARCHICAL,TopologyMode.PARALLEL)]
        scored=[x for x in scored if x[0] is not None]
        if not scored:return fallback
        scored.sort(key=lambda x:(-x[0],x[1].value)); return scored[0][1]