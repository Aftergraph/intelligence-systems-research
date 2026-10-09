from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

from .intelligence_fabric import CompetenceGraph, CompetenceKey


class LearningState(str, Enum):
    OBSERVED = "observed"
    REPLAYED = "replayed"
    SHADOWED = "shadowed"
    EXPERIMENTAL = "experimental"
    HOLDOUT_VERIFIED = "holdout_verified"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class DecisionObservation:
    observation_id: str
    decision_family: str
    teacher_strategy: str
    teacher_decision: str
    verified_outcome: bool
    estimated_cost_usd: float
    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("observation_id", self.observation_id),
            ("decision_family", self.decision_family),
            ("teacher_strategy", self.teacher_strategy),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be non-negative")


@dataclass(frozen=True, slots=True)
class ShadowObservation:
    decision_id: str
    incumbent_strategy: str
    candidate_strategy: str
    incumbent_decision: str
    candidate_decision: str
    incumbent_verified_outcome: bool | None
    candidate_verified_outcome: bool | None
    incumbent_cost_usd: float
    candidate_cost_usd: float

    def __post_init__(self) -> None:
        for name, value in (
            ("decision_id", self.decision_id),
            ("incumbent_strategy", self.incumbent_strategy),
            ("candidate_strategy", self.candidate_strategy),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.incumbent_cost_usd < 0 or self.candidate_cost_usd < 0:
            raise ValueError("shadow costs must be non-negative")


@dataclass(frozen=True, slots=True)
class LearningCandidate:
    candidate_id: str
    decision_family: str
    incumbent_strategy: str
    candidate_strategy: str
    state: LearningState = LearningState.OBSERVED
    replay_runs: int = 0
    shadow_runs: int = 0
    experimental_runs: int = 0
    holdout_runs: int = 0
    holdout_successes: int = 0
    incumbent_vsr: float | None = None
    candidate_vsr: float | None = None
    candidate_fcr: float | None = None
    incumbent_cpvo: float | None = None
    candidate_cpvo: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("candidate_id", self.candidate_id),
            ("decision_family", self.decision_family),
            ("incumbent_strategy", self.incumbent_strategy),
            ("candidate_strategy", self.candidate_strategy),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")
        for name, value in (
            ("replay_runs", self.replay_runs),
            ("shadow_runs", self.shadow_runs),
            ("experimental_runs", self.experimental_runs),
            ("holdout_runs", self.holdout_runs),
            ("holdout_successes", self.holdout_successes),
        ):
            if int(value) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.holdout_successes > self.holdout_runs:
            raise ValueError("holdout_successes cannot exceed holdout_runs")
        for name in ("incumbent_vsr", "candidate_vsr", "candidate_fcr"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("incumbent_cpvo", "candidate_cpvo"):
            value = getattr(self, name)
            if value is not None and float(value) < 0:
                raise ValueError(f"{name} must be non-negative")

    def with_metrics(self, **changes: Any) -> "LearningCandidate":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "candidate_id": self.candidate_id,
            "decision_family": self.decision_family,
            "incumbent_strategy": self.incumbent_strategy,
            "candidate_strategy": self.candidate_strategy,
            "state": self.state.value,
            "replay_runs": self.replay_runs,
            "shadow_runs": self.shadow_runs,
            "experimental_runs": self.experimental_runs,
            "holdout_runs": self.holdout_runs,
            "holdout_successes": self.holdout_successes,
            "incumbent_vsr": self.incumbent_vsr,
            "candidate_vsr": self.candidate_vsr,
            "candidate_fcr": self.candidate_fcr,
            "incumbent_cpvo": self.incumbent_cpvo,
            "candidate_cpvo": self.candidate_cpvo,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    promote: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    vsr_noninferiority_margin: float = 0.0
    max_fcr: float = 0.0
    require_lower_cpvo: bool = True
    min_replay_runs: int = 1
    min_shadow_runs: int = 1
    min_experimental_runs: int = 1
    min_holdout_runs: int = 1

    def __post_init__(self) -> None:
        if not 0.0 <= self.vsr_noninferiority_margin <= 1.0:
            raise ValueError("vsr_noninferiority_margin must be between 0 and 1")
        if not 0.0 <= self.max_fcr <= 1.0:
            raise ValueError("max_fcr must be between 0 and 1")

    def evaluate(self, candidate: LearningCandidate) -> PromotionDecision:
        reasons: list[str] = []
        if candidate.state is not LearningState.HOLDOUT_VERIFIED:
            reasons.append("candidate has not reached holdout_verified")
        if candidate.replay_runs < self.min_replay_runs:
            reasons.append("insufficient replay evidence")
        if candidate.shadow_runs < self.min_shadow_runs:
            reasons.append("insufficient shadow evidence")
        if candidate.experimental_runs < self.min_experimental_runs:
            reasons.append("insufficient experimental evidence")
        if candidate.holdout_runs < self.min_holdout_runs:
            reasons.append("insufficient holdout evidence")
        if candidate.incumbent_vsr is None or candidate.candidate_vsr is None:
            reasons.append("missing VSR metrics")
        elif candidate.candidate_vsr + self.vsr_noninferiority_margin < candidate.incumbent_vsr:
            reasons.append("candidate VSR violates non-inferiority margin")
        if candidate.candidate_fcr is None:
            reasons.append("missing FCR metric")
        elif candidate.candidate_fcr > self.max_fcr:
            reasons.append("candidate FCR exceeds policy")
        if self.require_lower_cpvo:
            if candidate.incumbent_cpvo is None or candidate.candidate_cpvo is None:
                reasons.append("missing CPVO metrics")
            elif candidate.candidate_cpvo >= candidate.incumbent_cpvo:
                reasons.append("candidate CPVO is not lower")
        return PromotionDecision(promote=not reasons, reasons=tuple(reasons))


class LearningRatchet:
    _NEXT = {
        LearningState.OBSERVED: {LearningState.REPLAYED, LearningState.REJECTED, LearningState.QUARANTINED},
        LearningState.REPLAYED: {LearningState.SHADOWED, LearningState.REJECTED, LearningState.QUARANTINED},
        LearningState.SHADOWED: {LearningState.EXPERIMENTAL, LearningState.REJECTED, LearningState.QUARANTINED},
        LearningState.EXPERIMENTAL: {LearningState.HOLDOUT_VERIFIED, LearningState.REJECTED, LearningState.QUARANTINED},
        LearningState.HOLDOUT_VERIFIED: {LearningState.PROMOTED, LearningState.REJECTED, LearningState.QUARANTINED},
        LearningState.PROMOTED: {LearningState.QUARANTINED},
        LearningState.REJECTED: set(),
        LearningState.QUARANTINED: set(),
    }

    def __init__(self, candidate: LearningCandidate) -> None:
        self.candidate = candidate

    def transition(self, state: LearningState) -> LearningCandidate:
        if state not in self._NEXT[self.candidate.state]:
            raise RuntimeError(
                f"illegal learning transition {self.candidate.state.value} -> {state.value}"
            )
        self.candidate = replace(self.candidate, state=state)
        return self.candidate

    def promote_competence(self, graph: CompetenceGraph, key: CompetenceKey) -> None:
        if self.candidate.state is not LearningState.PROMOTED:
            raise RuntimeError("only promoted learning candidates may update competence")
        if self.candidate.holdout_runs <= 0:
            raise RuntimeError("promoted candidate has no holdout observations")
        for index in range(self.candidate.holdout_runs):
            graph.observe(key, success=index < self.candidate.holdout_successes)


class DecisionDistillationCompiler:
    """Find repeated expensive decision families worth moving to a cheaper strategy.

    This compiler does not train a model. It produces a bounded LearningCandidate
    that must still pass replay, shadow, experimental, and holdout gates.
    """

    def __init__(self, *, min_observations: int = 20, min_teacher_vsr: float = 0.90) -> None:
        if min_observations <= 0:
            raise ValueError("min_observations must be positive")
        if not 0.0 <= min_teacher_vsr <= 1.0:
            raise ValueError("min_teacher_vsr must be between 0 and 1")
        self.min_observations = int(min_observations)
        self.min_teacher_vsr = float(min_teacher_vsr)
        self._observations: list[DecisionObservation] = []

    def observe(self, observation: DecisionObservation) -> None:
        self._observations.append(observation)

    def compile_candidate(
        self,
        *,
        decision_family: str,
        candidate_strategy: str,
        candidate_cost_usd: float,
    ) -> LearningCandidate | None:
        rows = [row for row in self._observations if row.decision_family == decision_family]
        if len(rows) < self.min_observations:
            return None
        teachers = {row.teacher_strategy for row in rows}
        if len(teachers) != 1:
            return None
        successes = sum(1 for row in rows if row.verified_outcome)
        teacher_vsr = successes / len(rows)
        if teacher_vsr < self.min_teacher_vsr:
            return None
        teacher_cost = sum(row.estimated_cost_usd for row in rows) / len(rows)
        if candidate_cost_usd >= teacher_cost:
            return None
        teacher_cpvo = teacher_cost / teacher_vsr if teacher_vsr else float("inf")
        # Candidate CPVO is only a planning lower-bound until replay/shadow evidence exists.
        candidate_cpvo = candidate_cost_usd / teacher_vsr if teacher_vsr else float("inf")
        teacher = next(iter(teachers))
        return LearningCandidate(
            candidate_id=f"distill:{decision_family}:{teacher}->{candidate_strategy}",
            decision_family=decision_family,
            incumbent_strategy=teacher,
            candidate_strategy=candidate_strategy,
            incumbent_vsr=teacher_vsr,
            incumbent_cpvo=teacher_cpvo,
            candidate_cpvo=candidate_cpvo,
            metadata={
                "teacher_observations": len(rows),
                "candidate_cpvo_is_projection": True,
            },
        )


@dataclass(frozen=True, slots=True)
class CounterfactualResult:
    candidate_strategy: str
    total_shadow_runs: int
    observable_counterfactual_runs: int
    coverage: float
    agreement_rate: float | None
    candidate_vsr: float | None
    candidate_cpvo: float | None


class CounterfactualReplay:
    """Replay only counterfactuals for which shadow outcomes were actually observed.

    Missing candidate outcomes stay unknown rather than being imputed.
    """

    def __init__(self) -> None:
        self._rows: list[ShadowObservation] = []

    def record(self, observation: ShadowObservation) -> None:
        self._rows.append(observation)

    def evaluate(self, *, candidate_strategy: str) -> CounterfactualResult:
        rows = [row for row in self._rows if row.candidate_strategy == candidate_strategy]
        observed = [row for row in rows if row.candidate_verified_outcome is not None]
        agreement = (
            sum(1 for row in rows if row.incumbent_decision == row.candidate_decision) / len(rows)
            if rows
            else None
        )
        vsr = (
            sum(1 for row in observed if row.candidate_verified_outcome) / len(observed)
            if observed
            else None
        )
        total_cost = sum(row.candidate_cost_usd for row in observed)
        verified = sum(1 for row in observed if row.candidate_verified_outcome)
        cpvo = total_cost / verified if verified else (None if not observed else float("inf"))
        return CounterfactualResult(
            candidate_strategy=candidate_strategy,
            total_shadow_runs=len(rows),
            observable_counterfactual_runs=len(observed),
            coverage=(len(observed) / len(rows)) if rows else 0.0,
            agreement_rate=agreement,
            candidate_vsr=vsr,
            candidate_cpvo=cpvo,
        )
