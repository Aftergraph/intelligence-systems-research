from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import ceil, sqrt
from random import Random
from statistics import NormalDist
from typing import Any, Iterable, Mapping

from .campaign_runtime import BenchmarkCostModel
from .learning_campaign import OutcomeSample
from .statistics import wilson_interval


@dataclass(frozen=True, slots=True)
class EvidenceCampaignPolicy:
    """Evidence-grade promotion policy for paired control-plane experiments.

    Promotion is based on the reserved holdout slice only. Shadow and experiment
    observations may guide development, but cannot make a candidate pass holdout.
    """

    min_holdout_pairs: int = 20
    noninferiority_margin: float = 0.02
    max_fcr: float = 0.0
    require_lower_cpvo: bool = True
    min_fie_ratio: float = 1.0
    target_fie_ratio: float = 10.0
    bootstrap_samples: int = 10_000
    bootstrap_seed: int = 20260925

    def __post_init__(self) -> None:
        if self.min_holdout_pairs < 1:
            raise ValueError("min_holdout_pairs must be positive")
        if not 0 <= self.noninferiority_margin <= 1:
            raise ValueError("noninferiority_margin must be between 0 and 1")
        if not 0 <= self.max_fcr <= 1:
            raise ValueError("max_fcr must be between 0 and 1")
        if self.min_fie_ratio <= 0 or self.target_fie_ratio <= 0:
            raise ValueError("FIE ratios must be positive")
        if self.bootstrap_samples < 100:
            raise ValueError("bootstrap_samples must be >= 100")


@dataclass(frozen=True, slots=True)
class RegressionPolicy:
    window_size: int = 20
    min_vsr: float = 0.90
    max_fcr: float = 0.0
    max_cpvo_usd: float | None = None

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be positive")
        if not 0 <= self.min_vsr <= 1 or not 0 <= self.max_fcr <= 1:
            raise ValueError("VSR/FCR bounds must be between 0 and 1")
        if self.max_cpvo_usd is not None and self.max_cpvo_usd < 0:
            raise ValueError("max_cpvo_usd cannot be negative")


class ContinuousRegressionMonitor:
    """Sliding post-promotion guardrail that can trigger quarantine."""

    def __init__(self, policy: RegressionPolicy) -> None:
        self.policy = policy
        self._rows: deque[OutcomeSample] = deque(maxlen=policy.window_size)

    def observe(self, sample: OutcomeSample) -> dict[str, Any]:
        self._rows.append(sample)
        if len(self._rows) < self.policy.window_size:
            return {
                "quarantine": False,
                "ready": False,
                "window_size": len(self._rows),
                "reasons": [],
            }
        rows = list(self._rows)
        verified = sum(row.verified for row in rows)
        false = sum(row.false_completion for row in rows)
        vsr = verified / len(rows)
        fcr = false / len(rows)
        total_cost = sum(row.cost_usd for row in rows)
        cpvo = total_cost / verified if verified else float("inf")
        reasons: list[str] = []
        if vsr < self.policy.min_vsr:
            reasons.append("VSR below post-promotion floor")
        if fcr > self.policy.max_fcr:
            reasons.append("FCR above post-promotion ceiling")
        if self.policy.max_cpvo_usd is not None and cpvo > self.policy.max_cpvo_usd:
            reasons.append("CPVO above post-promotion ceiling")
        return {
            "quarantine": bool(reasons),
            "ready": True,
            "window_size": len(rows),
            "vsr": vsr,
            "fcr": fcr,
            "cpvo_usd": cpvo,
            "reasons": reasons,
        }


def _pairs(
    records: Iterable[Mapping[str, Any]],
    incumbent_condition: str,
    candidate_condition: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    keyed: dict[tuple[int, str, str], dict[str, Any]] = {}
    for raw in records:
        row = dict(raw)
        condition = str(row.get("condition") or "")
        if condition not in {incumbent_condition, candidate_condition}:
            continue
        case = str(row.get("case_id") or "")
        repeat = int(row.get("repeat") or 0)
        if not case or repeat <= 0:
            raise ValueError("paired records require case_id and positive repeat")
        key = (repeat, case, condition)
        if key in keyed:
            raise ValueError("duplicate paired condition record")
        keyed[key] = row
    pair_keys = sorted({(repeat, case) for repeat, case, _ in keyed})
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for repeat, case in pair_keys:
        inc = keyed.get((repeat, case, incumbent_condition))
        cand = keyed.get((repeat, case, candidate_condition))
        if inc is None or cand is None:
            raise ValueError(f"missing paired condition for {case!r} repeat {repeat}")
        pairs.append((inc, cand))
    return pairs


def _condition_metrics(records: list[Mapping[str, Any]], cost_model: BenchmarkCostModel) -> dict[str, Any]:
    if not records:
        return {
            "missions": 0,
            "verified": 0,
            "vsr": None,
            "fcr": None,
            "cpvo_usd": None,
            "mean_tvo_s": None,
            "total_cost_usd": 0.0,
            "generator_cost_usd": 0.0,
            "decision_cost_usd": 0.0,
            "all_model_tokens": 0,
            "decision_tokens": 0,
            "control_plane_token_tax": None,
            "control_plane_cost_tax": None,
            "frontier_tokens": 0,
            "frontier_control_tokens": 0,
            "frontier_control_token_tax": None,
            "frontier_intelligence_efficiency": None,
        }
    verified = sum(str(r.get("status") or "") == "verified" for r in records)
    completion_claims = sum(int((r.get("metrics") or {}).get("completion_claims") or 0) for r in records)
    false_claims = sum(int((r.get("metrics") or {}).get("false_completion_claims") or 0) for r in records)
    generator_cost = decision_cost = 0.0
    provider_tokens = decision_tokens = frontier_tokens = frontier_control_tokens = 0
    verified_wall: list[float] = []
    for record in records:
        metrics = dict(record.get("metrics") or {})
        components = cost_model.record_cost_components(record)
        generator_cost += components["generator_cost_usd"]
        decision_cost += components["decision_cost_usd"]
        p_tokens = int(metrics.get("provider_input_tokens") or 0) + int(metrics.get("provider_output_tokens") or 0)
        d_tokens = int(metrics.get("decision_input_tokens") or 0) + int(metrics.get("decision_output_tokens") or 0)
        provider_tokens += p_tokens
        decision_tokens += d_tokens
        frontier_tokens += cost_model.record_frontier_tokens(record)
        if str(record.get("condition") or "") in cost_model.frontier_decision_conditions:
            frontier_control_tokens += d_tokens
        if str(record.get("status") or "") == "verified":
            verified_wall.append(float(metrics.get("wall_time_ms") or 0.0) / 1000.0)
    total_cost = generator_cost + decision_cost
    all_tokens = provider_tokens + decision_tokens
    fie = verified / frontier_tokens if frontier_tokens else None
    return {
        "missions": len(records),
        "verified": verified,
        "vsr": verified / len(records),
        "completion_claims": completion_claims,
        "false_completion_claims": false_claims,
        "fcr": false_claims / completion_claims if completion_claims else 0.0,
        "cpvo_usd": total_cost / verified if verified else None,
        "mean_tvo_s": sum(verified_wall) / len(verified_wall) if verified_wall else None,
        "total_cost_usd": total_cost,
        "generator_cost_usd": generator_cost,
        "decision_cost_usd": decision_cost,
        "all_model_tokens": all_tokens,
        "generator_tokens": provider_tokens,
        "decision_tokens": decision_tokens,
        "control_plane_token_tax": decision_tokens / all_tokens if all_tokens else None,
        "control_plane_cost_tax": decision_cost / total_cost if total_cost else None,
        "frontier_tokens": frontier_tokens,
        "frontier_control_tokens": frontier_control_tokens,
        "frontier_control_token_tax": frontier_control_tokens / frontier_tokens if frontier_tokens else None,
        "frontier_intelligence_efficiency": fie,
        "verified_per_million_frontier_tokens": fie * 1_000_000 if fie is not None else None,
    }


def _paired_bootstrap_delta(
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    if not pairs:
        raise ValueError("paired bootstrap requires at least one pair")
    deltas = [
        int(str(cand.get("status") or "") == "verified")
        - int(str(inc.get("status") or "") == "verified")
        for inc, cand in pairs
    ]
    estimate = sum(deltas) / len(deltas)
    rng = Random(seed)
    boot: list[float] = []
    n = len(deltas)
    for _ in range(samples):
        boot.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    boot.sort()
    lo_index = max(0, min(len(boot) - 1, int(0.025 * (len(boot) - 1))))
    hi_index = max(0, min(len(boot) - 1, int(0.975 * (len(boot) - 1))))
    return {
        "estimate": estimate,
        "bootstrap_ci": [boot[lo_index], boot[hi_index]],
        "confidence": 0.95,
        "method": "paired-percentile-bootstrap",
        "samples": samples,
        "seed": seed,
    }


def analyze_frontier_efficiency_target(
    records: Iterable[Mapping[str, Any]],
    *,
    incumbent_condition: str,
    candidate_condition: str,
    cost_model: BenchmarkCostModel,
    target_ratio: float = 10.0,
) -> dict[str, Any]:
    """Separate what control-plane offload can achieve from broader 10x claims."""
    if target_ratio <= 0:
        raise ValueError("target_ratio must be positive")
    pairs = _pairs(records, incumbent_condition, candidate_condition)
    inc_records = [inc for inc, _ in pairs]
    cand_records = [cand for _, cand in pairs]
    inc = _condition_metrics(inc_records, cost_model)
    cand = _condition_metrics(cand_records, cost_model)
    observed = None
    if inc["frontier_intelligence_efficiency"] and cand["frontier_intelligence_efficiency"]:
        observed = cand["frontier_intelligence_efficiency"] / inc["frontier_intelligence_efficiency"]
    generator_tokens = int(inc["generator_tokens"])
    incumbent_frontier = int(inc["frontier_tokens"])
    ceiling = (incumbent_frontier / generator_tokens) if generator_tokens else None
    attainable = bool(ceiling is not None and ceiling >= target_ratio)
    max_candidate_frontier = incumbent_frontier / target_ratio if target_ratio else 0.0
    generator_reduction = None
    if generator_tokens:
        generator_reduction = max(0.0, 1.0 - max_candidate_frontier / generator_tokens)
    return {
        "target_ratio": target_ratio,
        "observed_fie_ratio": observed,
        "incumbent_frontier_tokens": incumbent_frontier,
        "incumbent_generator_tokens": generator_tokens,
        "incumbent_frontier_control_tokens": int(inc["frontier_control_tokens"]),
        "control_plane_only_ceiling_ratio": ceiling,
        "target_attainable_by_control_plane_only": attainable,
        "requires_generator_or_context_reduction": not attainable,
        "minimum_generator_token_reduction_fraction_if_control_is_zero": generator_reduction,
        "truth_boundary": (
            "ceiling assumes equal verified outcomes, incumbent generator-token load, and complete removal "
            "of frontier control tokens; it is a feasibility bound, not an observed performance claim"
        ),
    }


def evaluate_evidence_campaign(
    records: Iterable[Mapping[str, Any]],
    *,
    incumbent_condition: str,
    candidate_condition: str,
    cost_model: BenchmarkCostModel,
    shadow_pairs: int,
    experiment_pairs: int,
    holdout_pairs: int,
    policy: EvidenceCampaignPolicy | None = None,
) -> dict[str, Any]:
    policy = policy or EvidenceCampaignPolicy()
    pairs = _pairs(records, incumbent_condition, candidate_condition)
    expected = shadow_pairs + experiment_pairs + holdout_pairs
    if len(pairs) != expected:
        raise ValueError(f"campaign requires exactly {expected} pairs; got {len(pairs)}")
    if holdout_pairs < policy.min_holdout_pairs:
        raise ValueError("holdout_pairs is below policy min_holdout_pairs")
    shadow = pairs[:shadow_pairs]
    experiment = pairs[shadow_pairs : shadow_pairs + experiment_pairs]
    holdout = pairs[shadow_pairs + experiment_pairs :]

    def phase(rows: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
        inc_rows = [inc for inc, _ in rows]
        cand_rows = [cand for _, cand in rows]
        inc = _condition_metrics(inc_rows, cost_model)
        cand = _condition_metrics(cand_rows, cost_model)
        ratio = None
        if inc["frontier_intelligence_efficiency"] and cand["frontier_intelligence_efficiency"]:
            ratio = cand["frontier_intelligence_efficiency"] / inc["frontier_intelligence_efficiency"]
        return {
            "pairs": len(rows),
            "incumbent": inc,
            "candidate": cand,
            "frontier_intelligence_efficiency_ratio": ratio,
            "paired_vsr_delta": _paired_bootstrap_delta(
                rows, samples=policy.bootstrap_samples, seed=policy.bootstrap_seed
            ) if rows else None,
        }

    shadow_metrics = phase(shadow)
    experiment_metrics = phase(experiment)
    holdout_metrics = phase(holdout)
    all_metrics = phase(pairs)

    reasons: list[str] = []
    delta = holdout_metrics["paired_vsr_delta"]
    assert delta is not None
    lower = float(delta["bootstrap_ci"][0])
    if lower < -policy.noninferiority_margin:
        reasons.append("holdout paired VSR violates non-inferiority margin")
    cand_holdout = holdout_metrics["candidate"]
    inc_holdout = holdout_metrics["incumbent"]
    if float(cand_holdout["fcr"] or 0.0) > policy.max_fcr:
        reasons.append("holdout candidate FCR exceeds policy")
    if policy.require_lower_cpvo:
        c_cpvo = cand_holdout["cpvo_usd"]
        i_cpvo = inc_holdout["cpvo_usd"]
        if c_cpvo is None or i_cpvo is None or float(c_cpvo) >= float(i_cpvo):
            reasons.append("holdout candidate CPVO is not lower")
    fie_ratio = holdout_metrics["frontier_intelligence_efficiency_ratio"]
    if fie_ratio is None or float(fie_ratio) < policy.min_fie_ratio:
        reasons.append("holdout frontier intelligence efficiency ratio is below policy")

    inc_success = int(inc_holdout["verified"])
    cand_success = int(cand_holdout["verified"])
    inc_ci = wilson_interval(inc_success, holdout_pairs)
    cand_ci = wilson_interval(cand_success, holdout_pairs)
    efficiency = analyze_frontier_efficiency_target(
        [row for pair in pairs for row in pair],
        incumbent_condition=incumbent_condition,
        candidate_condition=candidate_condition,
        cost_model=cost_model,
        target_ratio=policy.target_fie_ratio,
    )
    return {
        "version": 1,
        "paired_missions": len(pairs),
        "phase_allocation": {
            "shadow": shadow_pairs,
            "experiment": experiment_pairs,
            "holdout": holdout_pairs,
        },
        "incumbent_condition": incumbent_condition,
        "candidate_condition": candidate_condition,
        "shadow": shadow_metrics,
        "experiment": experiment_metrics,
        "holdout": holdout_metrics,
        "all": all_metrics,
        "promotion": {
            "promote": not reasons,
            "reasons": reasons,
            "evidence_scope": "holdout-only",
            "noninferiority_margin": policy.noninferiority_margin,
            "incumbent_holdout_vsr_ci": [inc_ci.lower, inc_ci.upper],
            "candidate_holdout_vsr_ci": [cand_ci.lower, cand_ci.upper],
            "min_fie_ratio": policy.min_fie_ratio,
        },
        "efficiency_target": efficiency,
        "truth_boundary": (
            "promotion is determined only from the reserved holdout slice; shadow/experiment evidence "
            "cannot make a candidate pass holdout, and bootstrap intervals are descriptive paired estimates"
        ),
    }


def plan_noninferiority_pairs(
    *,
    baseline_vsr: float,
    margin: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Conservative sample-size approximation before paired mission collection.

    Uses an independent-proportions normal approximation, intentionally conservative
    for a paired design. Final preregistration may replace this with a domain-specific
    paired-power model once discordance is known from pilot data.
    """
    if not 0 < baseline_vsr < 1:
        raise ValueError("baseline_vsr must be between 0 and 1")
    if not 0 < margin < 1:
        raise ValueError("margin must be between 0 and 1")
    if not 0 < alpha < 0.5 or not 0.5 < power < 1:
        raise ValueError("alpha/power out of range")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha)
    z_beta = normal.inv_cdf(power)
    variance_term = sqrt(2 * baseline_vsr * (1 - baseline_vsr))
    n = ((z_alpha + z_beta) * variance_term / margin) ** 2
    recommended = max(2, ceil(n))
    return {
        "baseline_vsr": baseline_vsr,
        "noninferiority_margin": margin,
        "alpha_one_sided": alpha,
        "power": power,
        "recommended_pairs": recommended,
        "method": "conservative-independent-proportions-approximation",
        "truth_boundary": "planning approximation only; paired pilot discordance should refine the final power calculation",
    }
