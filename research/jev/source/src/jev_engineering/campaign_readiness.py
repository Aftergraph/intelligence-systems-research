from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .evidence_campaign import plan_noninferiority_pairs


_INFRA_EXIT_CODES = {124, 126, 127, 9009}


@dataclass(frozen=True, slots=True)
class CompletionReadinessPolicy:
    min_pilot_pairs: int = 3
    min_verified_rate_per_condition: float = 0.50
    max_max_turn_rate_per_condition: float = 0.50
    max_false_completion_rate: float = 0.0
    require_baseline_exit_code: int = 1

    def __post_init__(self) -> None:
        if self.min_pilot_pairs < 1:
            raise ValueError("min_pilot_pairs must be positive")
        for value in (
            self.min_verified_rate_per_condition,
            self.max_max_turn_rate_per_condition,
            self.max_false_completion_rate,
        ):
            if not 0 <= value <= 1:
                raise ValueError("readiness rates must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CompletionConditionReport:
    condition: str
    missions: int
    verified: int
    verified_rate: float
    max_turns: int
    max_turn_rate: float
    verifier_runs: int
    verifier_run_rate: float
    completion_claims: int
    false_completion_claims: int
    false_completion_rate: float
    baseline_valid: bool


@dataclass(frozen=True, slots=True)
class CompletionReadinessReport:
    ready: bool
    paired_missions: int
    conditions: tuple[CompletionConditionReport, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "paired_missions": self.paired_missions,
            "conditions": [asdict(x) for x in self.conditions],
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class TurnBudgetRecommendation:
    condition: str
    current_max_turns: int
    recommended_max_turns: int
    action: str
    reason: str


@dataclass(frozen=True, slots=True)
class PoweredCampaignPlan:
    executable: bool
    baseline_vsr_assumption: float
    noninferiority_margin: float
    alpha_one_sided: float
    power: float
    shadow_pairs: int
    experiment_pairs: int
    holdout_pairs: int
    total_pairs: int
    sample_size_method: str
    completion_readiness: dict[str, Any]
    blockers: tuple[str, ...]
    truth_boundary: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["blockers"] = list(self.blockers)
        return value


def _condition_rows(records: Iterable[Mapping[str, Any]], condition: str) -> list[dict[str, Any]]:
    return [dict(r) for r in records if str(r.get("condition") or "") == condition]


def _baseline_valid(row: Mapping[str, Any], expected_exit_code: int) -> bool:
    raw = row.get("baseline_verification_exit_code")
    if raw is None:
        return False
    exit_code = int(raw)
    if exit_code in _INFRA_EXIT_CODES:
        return False
    return exit_code == expected_exit_code


def analyze_completion_readiness(
    records: Iterable[Mapping[str, Any]],
    *,
    incumbent_condition: str,
    candidate_condition: str,
    policy: CompletionReadinessPolicy | None = None,
) -> CompletionReadinessReport:
    policy = policy or CompletionReadinessPolicy()
    rows = [dict(r) for r in records]
    reports: list[CompletionConditionReport] = []
    reasons: list[str] = []
    pair_keys: set[tuple[int, str]] = set()
    for row in rows:
        if str(row.get("condition") or "") in {incumbent_condition, candidate_condition}:
            pair_keys.add((int(row.get("repeat") or 0), str(row.get("case_id") or "")))
    if len(pair_keys) < policy.min_pilot_pairs:
        reasons.append(f"pilot has {len(pair_keys)} pairs; requires at least {policy.min_pilot_pairs}")

    for condition in (incumbent_condition, candidate_condition):
        cond = _condition_rows(rows, condition)
        missions = len(cond)
        verified = sum(str(r.get("status") or "") == "verified" for r in cond)
        max_turns = sum(str(r.get("status") or "") == "max_turns" for r in cond)
        verifier_runs = sum(int((r.get("metrics") or {}).get("verifier_runs") or 0) for r in cond)
        completion_claims = sum(int((r.get("metrics") or {}).get("completion_claims") or 0) for r in cond)
        false_claims = sum(int((r.get("metrics") or {}).get("false_completion_claims") or 0) for r in cond)
        verified_rate = verified / missions if missions else 0.0
        max_turn_rate = max_turns / missions if missions else 1.0
        verifier_run_rate = sum(int((r.get("metrics") or {}).get("verifier_runs") or 0) > 0 for r in cond) / missions if missions else 0.0
        false_rate = false_claims / completion_claims if completion_claims else 0.0
        baseline_valid = bool(cond) and all(_baseline_valid(r, policy.require_baseline_exit_code) for r in cond)
        report = CompletionConditionReport(
            condition=condition,
            missions=missions,
            verified=verified,
            verified_rate=verified_rate,
            max_turns=max_turns,
            max_turn_rate=max_turn_rate,
            verifier_runs=verifier_runs,
            verifier_run_rate=verifier_run_rate,
            completion_claims=completion_claims,
            false_completion_claims=false_claims,
            false_completion_rate=false_rate,
            baseline_valid=baseline_valid,
        )
        reports.append(report)
        if not baseline_valid:
            reasons.append(f"{condition}: baseline verifier did not produce the preregistered failing exit code")
        if verified_rate < policy.min_verified_rate_per_condition:
            reasons.append(f"{condition}: verified completion rate below readiness floor")
        if max_turn_rate > policy.max_max_turn_rate_per_condition:
            reasons.append(f"{condition}: max-turn exhaustion rate above readiness ceiling")
        if false_rate > policy.max_false_completion_rate:
            reasons.append(f"{condition}: false-completion rate above readiness ceiling")

    return CompletionReadinessReport(
        ready=not reasons,
        paired_missions=len(pair_keys),
        conditions=tuple(reports),
        reasons=tuple(reasons),
    )


def recommend_turn_budgets(
    report: CompletionReadinessReport,
    *,
    current_max_turns: int,
    diagnostic_cap: int = 12,
) -> tuple[TurnBudgetRecommendation, ...]:
    if current_max_turns < 1 or diagnostic_cap < current_max_turns:
        raise ValueError("invalid turn budget bounds")
    recommendations: list[TurnBudgetRecommendation] = []
    for cond in report.conditions:
        if not cond.baseline_valid:
            action = "repair_verifier_first"
            target = current_max_turns
            reason = "turn budget is uninterpretable until verifier baseline is valid"
        elif cond.false_completion_rate > 0:
            action = "repair_completion_gate"
            target = current_max_turns
            reason = "false completion observed; more turns must not mask a bad completion gate"
        elif cond.verifier_run_rate == 0:
            action = "diagnostic_turn_increase"
            target = min(diagnostic_cap, max(current_max_turns + 2, current_max_turns * 2))
            reason = "no mission reached verifier; permit a bounded diagnostic increase only"
        elif cond.verified_rate == 0:
            action = "repair_generation_or_verification"
            target = min(diagnostic_cap, current_max_turns + 2)
            reason = "verifier ran but no mission verified; inspect generated patch/evidence before scaling"
        else:
            action = "hold"
            target = current_max_turns
            reason = "condition has verified completions; collect additional pilot pairs before scaling"
        recommendations.append(TurnBudgetRecommendation(cond.condition, current_max_turns, target, action, reason))
    return tuple(recommendations)


def plan_powered_campaign(
    *,
    readiness: CompletionReadinessReport,
    baseline_vsr_assumption: float,
    noninferiority_margin: float = 0.02,
    alpha: float = 0.05,
    power: float = 0.80,
    shadow_pairs: int = 5,
    experiment_pairs: int = 10,
    min_holdout_pairs: int = 20,
    live_lineage_proven: bool,
    pricing_reviewed: bool,
    preregistered: bool,
) -> PoweredCampaignPlan:
    sizing = plan_noninferiority_pairs(
        baseline_vsr=baseline_vsr_assumption,
        margin=noninferiority_margin,
        alpha=alpha,
        power=power,
    )
    holdout = max(min_holdout_pairs, int(sizing["recommended_pairs"]))
    blockers: list[str] = []
    if not readiness.ready:
        blockers.append("completion_readiness_not_met")
    if not live_lineage_proven:
        blockers.append("authenticated_lineage_not_proven")
    if not pricing_reviewed:
        blockers.append("pricing_not_reviewed")
    if not preregistered:
        blockers.append("campaign_not_preregistered")
    return PoweredCampaignPlan(
        executable=not blockers,
        baseline_vsr_assumption=baseline_vsr_assumption,
        noninferiority_margin=noninferiority_margin,
        alpha_one_sided=alpha,
        power=power,
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout,
        total_pairs=shadow_pairs + experiment_pairs + holdout,
        sample_size_method=str(sizing["method"]),
        completion_readiness=readiness.to_dict(),
        blockers=tuple(blockers),
        truth_boundary=(
            "This is a preregistration/power-planning artifact. executable=true authorizes only the planned "
            "research campaign; it is not a performance result or deployment authority."
        ),
    )