from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Sequence

from .context_compiler import ContextCandidate
from .system_efficiency import AdaptiveContextBudgeter, EarlyExitGate, RetryBudgetOptimizer, RetryCandidate


@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    path: str
    verified: bool
    predicted_vsr: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path not in {"cheap", "frontier", "frontier_retry"}:
            raise ValueError("unsupported execution path")
        if not 0 <= self.predicted_vsr <= 1:
            raise ValueError("predicted_vsr must be between 0 and 1")
        if min(self.input_tokens, self.output_tokens) < 0 or self.cost_usd < 0:
            raise ValueError("usage must be non-negative")

    @property
    def frontier_tokens(self) -> int:
        return self.input_tokens + self.output_tokens if self.path.startswith("frontier") else 0


@dataclass(frozen=True, slots=True)
class EfficiencyExecutionPolicy:
    required_vsr: float = 0.95
    minimum_context_utility_retention: float = 0.95
    risk_class: str = "normal"
    assurance_level: int = 2
    frontier_token_budget: int = 100_000
    min_retry_vsr_gain_per_1k_tokens: float = 0.01

    def __post_init__(self) -> None:
        if not 0 <= self.required_vsr <= 1:
            raise ValueError("required_vsr must be between 0 and 1")
        if not 0 <= self.minimum_context_utility_retention <= 1:
            raise ValueError("minimum_context_utility_retention must be between 0 and 1")
        if self.frontier_token_budget < 0:
            raise ValueError("frontier_token_budget must be non-negative")


@dataclass(frozen=True, slots=True)
class EfficiencyExecutionReceipt:
    mission_id: str
    status: str
    selected_context_keys: tuple[str, ...]
    candidate_context_tokens: int
    selected_context_tokens: int
    attempts: tuple[ExecutionAttempt, ...]
    frontier_calls: int
    frontier_tokens: int
    cost_usd: float
    verified: bool
    stop_reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "mission_id": self.mission_id,
            "status": self.status,
            "selected_context_keys": list(self.selected_context_keys),
            "candidate_context_tokens": self.candidate_context_tokens,
            "selected_context_tokens": self.selected_context_tokens,
            "context_token_reduction": (
                1.0 - self.selected_context_tokens / self.candidate_context_tokens
                if self.candidate_context_tokens else 0.0
            ),
            "attempts": [
                {
                    "path": a.path, "verified": a.verified, "predicted_vsr": a.predicted_vsr,
                    "input_tokens": a.input_tokens, "output_tokens": a.output_tokens,
                    "frontier_tokens": a.frontier_tokens, "cost_usd": a.cost_usd,
                    "evidence_ids": list(a.evidence_ids), "metadata": dict(a.metadata),
                } for a in self.attempts
            ],
            "frontier_calls": self.frontier_calls,
            "frontier_tokens": self.frontier_tokens,
            "cost_usd": self.cost_usd,
            "verified": self.verified,
            "stop_reason": self.stop_reason,
            "truth_boundary": "receipt records execution telemetry; quality claims require paired holdout evidence",
        }


class EmpiricalEfficiencyExecutionEngine:
    """Execute cheap-first and frontier escalation with measured token accounting.

    The engine never treats model self-report as verification. Callbacks must return an
    ExecutionAttempt whose ``verified`` bit comes from the caller's evidence/verifier path.
    """

    def __init__(self, *, context_budgeter: AdaptiveContextBudgeter | None = None, early_exit_gate: EarlyExitGate | None = None) -> None:
        self.context_budgeter = context_budgeter or AdaptiveContextBudgeter()
        self.early_exit_gate = early_exit_gate or EarlyExitGate()

    def run(
        self,
        *,
        mission_id: str,
        context: Iterable[ContextCandidate],
        policy: EfficiencyExecutionPolicy,
        cheap_attempt: Callable[[tuple[str, ...]], ExecutionAttempt],
        frontier_attempt: Callable[[tuple[str, ...], int], ExecutionAttempt],
        retry_candidates: Sequence[RetryCandidate] = (),
    ) -> EfficiencyExecutionReceipt:
        if not mission_id.strip():
            raise ValueError("mission_id must be non-empty")
        context_plan = self.context_budgeter.plan(
            context, minimum_utility_retention=policy.minimum_context_utility_retention
        )
        keys = context_plan.selected_keys
        attempts: list[ExecutionAttempt] = []

        cheap = cheap_attempt(keys)
        if cheap.path != "cheap":
            raise ValueError("cheap_attempt must return path='cheap'")
        attempts.append(cheap)
        gate = self.early_exit_gate.decide(
            predicted_vsr=cheap.predicted_vsr,
            required_vsr=policy.required_vsr,
            risk_class=policy.risk_class,
            assurance_level=policy.assurance_level,
            cheap_path_verified=cheap.verified,
        )
        if not gate.use_frontier:
            return self._receipt(mission_id, context_plan, attempts, True, "verified_cheap_path_sufficient")

        first = frontier_attempt(keys, 0)
        if first.path != "frontier":
            raise ValueError("first frontier attempt must return path='frontier'")
        if first.frontier_tokens > policy.frontier_token_budget:
            return self._receipt(mission_id, context_plan, attempts, False, "frontier_budget_exceeded")
        attempts.append(first)
        if first.verified:
            return self._receipt(mission_id, context_plan, attempts, True, "frontier_verified")

        remaining = max(0, policy.frontier_token_budget - first.frontier_tokens)
        retry_plan = RetryBudgetOptimizer().plan(
            retry_candidates,
            frontier_token_budget=remaining,
            min_vsr_gain_per_1k_tokens=policy.min_retry_vsr_gain_per_1k_tokens,
        )
        for retry_index in retry_plan.admitted_retries:
            attempt = frontier_attempt(keys, retry_index)
            if attempt.path != "frontier_retry":
                raise ValueError("retry frontier attempt must return path='frontier_retry'")
            used = sum(a.frontier_tokens for a in attempts)
            if used + attempt.frontier_tokens > policy.frontier_token_budget:
                return self._receipt(mission_id, context_plan, attempts, False, "frontier_budget_exceeded")
            attempts.append(attempt)
            if attempt.verified:
                return self._receipt(mission_id, context_plan, attempts, True, "frontier_retry_verified")
        return self._receipt(mission_id, context_plan, attempts, False, retry_plan.stop_reason)

    @staticmethod
    def _receipt(mission_id, context_plan, attempts, verified, reason):
        frontier_calls = sum(1 for a in attempts if a.path.startswith("frontier"))
        frontier_tokens = sum(a.frontier_tokens for a in attempts)
        cost = sum(a.cost_usd for a in attempts)
        return EfficiencyExecutionReceipt(
            mission_id=mission_id,
            status="VERIFIED" if verified else "UNVERIFIED",
            selected_context_keys=context_plan.selected_keys,
            candidate_context_tokens=context_plan.candidate_tokens,
            selected_context_tokens=context_plan.token_budget,
            attempts=tuple(attempts), frontier_calls=frontier_calls,
            frontier_tokens=frontier_tokens, cost_usd=cost, verified=verified, stop_reason=reason,
        )
