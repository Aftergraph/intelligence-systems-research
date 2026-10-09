from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable, Mapping, Sequence

from .context_compiler import ContextCandidate, SemanticGarbageCollector


_EVIDENCE_RANK = {
    "hypothesis": 0,
    "modeled": 1,
    "observed": 2,
    "benchmarked": 3,
}

_RISK_RANK = {
    "low": 0,
    "normal": 1,
    "high": 2,
    "critical": 3,
}


@dataclass(frozen=True, slots=True)
class FrontierWorkloadProfile:
    """Mutually-exclusive frontier-token categories for one workload population.

    These are accounting categories, not provider billing claims. A caller is responsible
    for constructing a non-overlapping profile from measured telemetry.
    """

    profile_id: str
    categories: Mapping[str, int]
    verified_outcomes: int = 0
    missions: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id must be non-empty")
        if not self.categories:
            raise ValueError("categories must be non-empty")
        for name, tokens in self.categories.items():
            if not str(name).strip():
                raise ValueError("category names must be non-empty")
            if int(tokens) < 0:
                raise ValueError("token counts must be non-negative")
        if self.verified_outcomes < 0 or self.missions < 0:
            raise ValueError("outcome counts must be non-negative")
        if self.verified_outcomes > self.missions and self.missions > 0:
            raise ValueError("verified_outcomes cannot exceed missions")

    @property
    def total_frontier_tokens(self) -> int:
        return sum(int(v) for v in self.categories.values())

    @property
    def frontier_intelligence_efficiency(self) -> float | None:
        total = self.total_frontier_tokens
        if total <= 0:
            return None
        return self.verified_outcomes / total

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "profile_id": self.profile_id,
            "categories": {str(k): int(v) for k, v in self.categories.items()},
            "total_frontier_tokens": self.total_frontier_tokens,
            "verified_outcomes": self.verified_outcomes,
            "missions": self.missions,
            "frontier_intelligence_efficiency": self.frontier_intelligence_efficiency,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EfficiencyLever:
    """One bounded optimization hypothesis or observed mechanism.

    ``reductions`` maps frontier-token accounting categories to fractional token
    reductions. Overlapping levers compose multiplicatively rather than additively,
    which prevents impossible >100% savings from simple summation.
    """

    lever_id: str
    reductions: Mapping[str, float]
    quality_retention_lower_bound: float = 1.0
    evidence_level: str = "hypothesis"
    complexity_cost: float = 1.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.lever_id.strip():
            raise ValueError("lever_id must be non-empty")
        if not self.reductions:
            raise ValueError("reductions must be non-empty")
        for category, reduction in self.reductions.items():
            if not str(category).strip():
                raise ValueError("reduction category must be non-empty")
            if not 0.0 <= float(reduction) <= 1.0:
                raise ValueError("reduction fractions must be between 0 and 1")
        if not 0.0 <= self.quality_retention_lower_bound <= 1.0:
            raise ValueError("quality_retention_lower_bound must be between 0 and 1")
        if self.evidence_level not in _EVIDENCE_RANK:
            raise ValueError(f"unsupported evidence_level: {self.evidence_level}")
        if self.complexity_cost < 0:
            raise ValueError("complexity_cost must be non-negative")


@dataclass(frozen=True, slots=True)
class SystemEfficiencyPlan:
    profile_id: str
    target_ratio: float
    selected_levers: tuple[str, ...]
    baseline_tokens: int
    projected_categories: Mapping[str, int]
    projected_tokens: int
    projected_ratio: float
    quality_retention_lower_bound: float
    minimum_evidence_level: str
    target_met: bool
    truth_boundary: str = (
        "projected reductions are a planning model; only measured paired missions may be used as performance evidence"
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "profile_id": self.profile_id,
            "target_ratio": self.target_ratio,
            "selected_levers": list(self.selected_levers),
            "baseline_tokens": self.baseline_tokens,
            "projected_categories": {str(k): int(v) for k, v in self.projected_categories.items()},
            "projected_tokens": self.projected_tokens,
            "projected_ratio": self.projected_ratio,
            "quality_retention_lower_bound": self.quality_retention_lower_bound,
            "minimum_evidence_level": self.minimum_evidence_level,
            "target_met": self.target_met,
            "truth_boundary": self.truth_boundary,
        }


@dataclass(frozen=True, slots=True)
class AttainableRegion:
    baseline_tokens: int
    minimum_projected_tokens: int
    maximum_ratio: float
    target_ratio: float
    target_attainable: bool
    eligible_levers: tuple[str, ...]
    quality_retention_lower_bound: float

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "baseline_tokens": self.baseline_tokens,
            "minimum_projected_tokens": self.minimum_projected_tokens,
            "maximum_ratio": self.maximum_ratio,
            "target_ratio": self.target_ratio,
            "target_attainable": self.target_attainable,
            "eligible_levers": list(self.eligible_levers),
            "quality_retention_lower_bound": self.quality_retention_lower_bound,
            "truth_boundary": "attainable region is model-based and is not a measured performance result",
        }


class SystemEfficiencyCompiler:
    """Search bounded efficiency levers without silently assuming independence.

    Token reductions for the same accounting category compose multiplicatively.
    Quality loss composes with a conservative union bound:
    ``retention >= 1 - sum(1 - per_lever_retention)``.
    """

    def __init__(self, *, max_search_levers: int = 20) -> None:
        self.max_search_levers = max_search_levers

    @staticmethod
    def _quality_lower_bound(levers: Sequence[EfficiencyLever]) -> float:
        loss_upper_bound = sum(1.0 - lever.quality_retention_lower_bound for lever in levers)
        return max(0.0, 1.0 - loss_upper_bound)

    @staticmethod
    def _project_categories(
        profile: FrontierWorkloadProfile,
        levers: Sequence[EfficiencyLever],
    ) -> dict[str, int]:
        projected: dict[str, int] = {}
        for category, raw_tokens in profile.categories.items():
            remaining_fraction = 1.0
            for lever in levers:
                reduction = float(lever.reductions.get(category, 0.0))
                remaining_fraction *= 1.0 - reduction
            # Round upward so planning never claims fractional-token savings that do not exist.
            tokens = int(raw_tokens)
            projected[category] = 0 if tokens == 0 else max(1, int((tokens * remaining_fraction) + 0.999999999))
        return projected

    @staticmethod
    def _evidence_ok(lever: EfficiencyLever, minimum_evidence_level: str) -> bool:
        if minimum_evidence_level not in _EVIDENCE_RANK:
            raise ValueError(f"unsupported minimum_evidence_level: {minimum_evidence_level}")
        return _EVIDENCE_RANK[lever.evidence_level] >= _EVIDENCE_RANK[minimum_evidence_level]

    def attainable_region(
        self,
        profile: FrontierWorkloadProfile,
        levers: Iterable[EfficiencyLever],
        *,
        target_ratio: float,
        minimum_quality_retention: float = 0.95,
        minimum_evidence_level: str = "hypothesis",
    ) -> AttainableRegion:
        if target_ratio <= 0:
            raise ValueError("target_ratio must be positive")
        eligible = tuple(
            lever for lever in levers if self._evidence_ok(lever, minimum_evidence_level)
        )
        if len(eligible) > self.max_search_levers:
            raise ValueError("too many levers for exhaustive bounded search")
        best_tokens = profile.total_frontier_tokens
        best_quality = 1.0
        best_ids: tuple[str, ...] = ()
        for size in range(len(eligible) + 1):
            for subset in combinations(eligible, size):
                quality = self._quality_lower_bound(subset)
                if quality < minimum_quality_retention:
                    continue
                projected = self._project_categories(profile, subset)
                total = sum(projected.values())
                if total < best_tokens or (total == best_tokens and quality > best_quality):
                    best_tokens = total
                    best_quality = quality
                    best_ids = tuple(lever.lever_id for lever in subset)
        baseline = profile.total_frontier_tokens
        ratio = (baseline / best_tokens) if best_tokens else float("inf")
        return AttainableRegion(
            baseline_tokens=baseline,
            minimum_projected_tokens=best_tokens,
            maximum_ratio=ratio,
            target_ratio=target_ratio,
            target_attainable=ratio >= target_ratio,
            eligible_levers=best_ids,
            quality_retention_lower_bound=best_quality,
        )

    def compile(
        self,
        profile: FrontierWorkloadProfile,
        levers: Iterable[EfficiencyLever],
        *,
        target_ratio: float,
        minimum_quality_retention: float = 0.95,
        minimum_evidence_level: str = "hypothesis",
    ) -> SystemEfficiencyPlan:
        if target_ratio <= 0:
            raise ValueError("target_ratio must be positive")
        eligible = tuple(
            lever for lever in levers if self._evidence_ok(lever, minimum_evidence_level)
        )
        if len(eligible) > self.max_search_levers:
            raise ValueError("too many levers for exhaustive bounded search")
        baseline = profile.total_frontier_tokens
        if baseline <= 0:
            raise ValueError("profile total_frontier_tokens must be positive")

        feasible: list[tuple[float, int, int, float, tuple[EfficiencyLever, ...], dict[str, int]]] = []
        best_any: tuple[float, int, int, float, tuple[EfficiencyLever, ...], dict[str, int]] | None = None
        for size in range(len(eligible) + 1):
            for subset in combinations(eligible, size):
                quality = self._quality_lower_bound(subset)
                if quality < minimum_quality_retention:
                    continue
                projected = self._project_categories(profile, subset)
                total = sum(projected.values())
                ratio = baseline / total if total else float("inf")
                complexity = sum(lever.complexity_cost for lever in subset)
                row = (complexity, size, total, -quality, subset, projected)
                if best_any is None or (total, complexity, size, -quality) < (
                    best_any[2], best_any[0], best_any[1], best_any[3]
                ):
                    best_any = row
                if ratio >= target_ratio:
                    feasible.append(row)

        if feasible:
            # Prefer least implementation complexity, then fewer mechanisms, then fewer tokens,
            # then stronger conservative quality retention.
            chosen = min(feasible, key=lambda row: (row[0], row[1], row[2], row[3]))
            target_met = True
        else:
            if best_any is None:
                chosen = (0.0, 0, baseline, -1.0, tuple(), dict(profile.categories))
            else:
                chosen = best_any
            target_met = False

        _, _, projected_tokens, neg_quality, subset, projected = chosen
        ratio = baseline / projected_tokens if projected_tokens else float("inf")
        return SystemEfficiencyPlan(
            profile_id=profile.profile_id,
            target_ratio=target_ratio,
            selected_levers=tuple(lever.lever_id for lever in subset),
            baseline_tokens=baseline,
            projected_categories=projected,
            projected_tokens=projected_tokens,
            projected_ratio=ratio,
            quality_retention_lower_bound=-neg_quality,
            minimum_evidence_level=minimum_evidence_level,
            target_met=target_met,
        )


@dataclass(frozen=True, slots=True)
class ContextBudgetPlan:
    token_budget: int
    retained_utility_fraction: float
    selected_keys: tuple[str, ...]
    excluded: Mapping[str, str]
    candidate_tokens: int

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "token_budget": self.token_budget,
            "retained_utility_fraction": self.retained_utility_fraction,
            "selected_keys": list(self.selected_keys),
            "excluded": dict(self.excluded),
            "candidate_tokens": self.candidate_tokens,
        }


class AdaptiveContextBudgeter:
    """Choose the smallest fresh context budget that retains a requested utility mass."""

    def __init__(self, *, garbage_collector: SemanticGarbageCollector | None = None) -> None:
        self.garbage_collector = garbage_collector or SemanticGarbageCollector()

    def plan(
        self,
        candidates: Iterable[ContextCandidate],
        *,
        minimum_utility_retention: float = 0.95,
        invalidated_dependencies: set[str] | None = None,
    ) -> ContextBudgetPlan:
        if not 0.0 <= minimum_utility_retention <= 1.0:
            raise ValueError("minimum_utility_retention must be between 0 and 1")
        candidate_list = list(candidates)
        gc = self.garbage_collector.collect(
            candidate_list, invalidated_dependencies=invalidated_dependencies
        )
        total_utility = sum(item.utility for item in gc.kept)
        if not gc.kept or total_utility <= 0:
            return ContextBudgetPlan(
                token_budget=0,
                retained_utility_fraction=0.0,
                selected_keys=(),
                excluded=dict(gc.excluded),
                candidate_tokens=sum(item.token_estimate for item in candidate_list),
            )
        target = total_utility * minimum_utility_retention
        selected: list[ContextCandidate] = []
        retained = 0.0
        for item in gc.kept:
            if retained >= target:
                break
            selected.append(item)
            retained += item.utility
        selected_keys = {item.key for item in selected}
        excluded = dict(gc.excluded)
        for item in gc.kept:
            if item.key not in selected_keys:
                excluded[item.key] = "utility_budget"
        return ContextBudgetPlan(
            token_budget=sum(item.token_estimate for item in selected),
            retained_utility_fraction=min(1.0, retained / total_utility),
            selected_keys=tuple(item.key for item in selected),
            excluded=excluded,
            candidate_tokens=sum(item.token_estimate for item in candidate_list),
        )


@dataclass(frozen=True, slots=True)
class EarlyExitDecision:
    use_frontier: bool
    predicted_vsr: float
    required_vsr: float
    reason: str


class EarlyExitGate:
    """Fail-closed no-frontier decision for already-solved or cheap-path work."""

    def __init__(self, *, max_risk_class: str = "normal", max_assurance_level: int = 2) -> None:
        if max_risk_class not in _RISK_RANK:
            raise ValueError("unsupported max_risk_class")
        if not 0 <= max_assurance_level <= 7:
            raise ValueError("max_assurance_level must be between 0 and 7")
        self.max_risk_class = max_risk_class
        self.max_assurance_level = max_assurance_level

    def decide(
        self,
        *,
        predicted_vsr: float,
        required_vsr: float,
        risk_class: str = "normal",
        assurance_level: int = 1,
        cheap_path_verified: bool,
    ) -> EarlyExitDecision:
        if risk_class not in _RISK_RANK:
            raise ValueError("unsupported risk_class")
        if not 0.0 <= predicted_vsr <= 1.0 or not 0.0 <= required_vsr <= 1.0:
            raise ValueError("VSR values must be between 0 and 1")
        if not 0 <= assurance_level <= 7:
            raise ValueError("assurance_level must be between 0 and 7")
        if not cheap_path_verified:
            return EarlyExitDecision(True, predicted_vsr, required_vsr, "cheap_path_not_verified")
        if _RISK_RANK[risk_class] > _RISK_RANK[self.max_risk_class]:
            return EarlyExitDecision(True, predicted_vsr, required_vsr, "risk_requires_frontier")
        if assurance_level > self.max_assurance_level:
            return EarlyExitDecision(True, predicted_vsr, required_vsr, "assurance_requires_frontier")
        if predicted_vsr < required_vsr:
            return EarlyExitDecision(True, predicted_vsr, required_vsr, "quality_threshold_not_met")
        return EarlyExitDecision(False, predicted_vsr, required_vsr, "verified_cheap_path_sufficient")


@dataclass(frozen=True, slots=True)
class RetryCandidate:
    retry_index: int
    incremental_vsr_gain: float
    frontier_tokens: int

    def __post_init__(self) -> None:
        if self.retry_index < 1:
            raise ValueError("retry_index must be >= 1")
        if not 0.0 <= self.incremental_vsr_gain <= 1.0:
            raise ValueError("incremental_vsr_gain must be between 0 and 1")
        if self.frontier_tokens <= 0:
            raise ValueError("frontier_tokens must be positive")

    @property
    def gain_per_1k_tokens(self) -> float:
        return self.incremental_vsr_gain / (self.frontier_tokens / 1000.0)


@dataclass(frozen=True, slots=True)
class RetryBudgetPlan:
    admitted_retries: tuple[int, ...]
    frontier_tokens_reserved: int
    cumulative_vsr_gain_upper_bound: float
    stop_reason: str


class RetryBudgetOptimizer:
    """Admit sequential retries only while their marginal verified-value density is justified."""

    def plan(
        self,
        retries: Iterable[RetryCandidate],
        *,
        frontier_token_budget: int,
        min_vsr_gain_per_1k_tokens: float,
        max_retries: int | None = None,
    ) -> RetryBudgetPlan:
        if frontier_token_budget < 0:
            raise ValueError("frontier_token_budget must be non-negative")
        if min_vsr_gain_per_1k_tokens < 0:
            raise ValueError("min_vsr_gain_per_1k_tokens must be non-negative")
        rows = sorted(retries, key=lambda row: row.retry_index)
        admitted: list[int] = []
        used = 0
        gain = 0.0
        stop_reason = "exhausted_candidates"
        for row in rows:
            if max_retries is not None and len(admitted) >= max_retries:
                stop_reason = "max_retries"
                break
            if row.gain_per_1k_tokens < min_vsr_gain_per_1k_tokens:
                stop_reason = "marginal_value_too_low"
                break
            if used + row.frontier_tokens > frontier_token_budget:
                stop_reason = "frontier_token_budget"
                break
            admitted.append(row.retry_index)
            used += row.frontier_tokens
            gain += row.incremental_vsr_gain
        return RetryBudgetPlan(
            admitted_retries=tuple(admitted),
            frontier_tokens_reserved=used,
            cumulative_vsr_gain_upper_bound=min(1.0, gain),
            stop_reason=stop_reason,
        )
