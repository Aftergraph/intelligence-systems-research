from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .automatic_campaign import AutoCampaignController, AutoCampaignSchedule
from .learning import LearningCandidate, PromotionPolicy
from .learning_campaign import LearningCampaign, OutcomeSample


@dataclass(frozen=True, slots=True)
class TokenPrice:
    """USD price per one million tokens for one inference plane."""

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None

    def __post_init__(self) -> None:
        if min(self.input_per_million, self.output_per_million) < 0:
            raise ValueError("token prices cannot be negative")
        if self.cached_input_per_million is not None and self.cached_input_per_million < 0:
            raise ValueError("cached token price cannot be negative")

    def cost(self, *, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
        if min(input_tokens, output_tokens, cached_input_tokens) < 0:
            raise ValueError("token counts cannot be negative")
        cached = min(cached_input_tokens, input_tokens)
        uncached = input_tokens - cached
        cached_rate = self.input_per_million if self.cached_input_per_million is None else self.cached_input_per_million
        return (
            uncached * self.input_per_million
            + cached * cached_rate
            + output_tokens * self.output_per_million
        ) / 1_000_000.0


@dataclass(frozen=True, slots=True)
class BenchmarkCostModel:
    generator: TokenPrice
    decision_by_condition: Mapping[str, TokenPrice]
    frontier_decision_conditions: frozenset[str] = frozenset()

    def record_cost_usd(self, record: Mapping[str, Any]) -> float:
        condition = str(record.get("condition") or "")
        try:
            decision_price = self.decision_by_condition[condition]
        except KeyError as exc:
            raise ValueError(f"no decision-plane price for condition {condition!r}") from exc
        metrics = dict(record.get("metrics") or {})
        provider_input = int(metrics.get("provider_input_tokens") or 0)
        provider_output = int(metrics.get("provider_output_tokens") or 0)
        provider_cached = int(metrics.get("provider_cached_input_tokens") or 0)
        decision_input = int(metrics.get("decision_input_tokens") or 0)
        decision_output = int(metrics.get("decision_output_tokens") or 0)
        return self.generator.cost(
            input_tokens=provider_input,
            output_tokens=provider_output,
            cached_input_tokens=provider_cached,
        ) + decision_price.cost(
            input_tokens=decision_input,
            output_tokens=decision_output,
            cached_input_tokens=0,
        )

    def record_cost_components(self, record: Mapping[str, Any]) -> dict[str, float]:
        """Return generator, control-plane and total inference cost for one record."""
        condition = str(record.get("condition") or "")
        try:
            decision_price = self.decision_by_condition[condition]
        except KeyError as exc:
            raise ValueError(f"no decision-plane price for condition {condition!r}") from exc
        metrics = dict(record.get("metrics") or {})
        generator_cost = self.generator.cost(
            input_tokens=int(metrics.get("provider_input_tokens") or 0),
            output_tokens=int(metrics.get("provider_output_tokens") or 0),
            cached_input_tokens=int(metrics.get("provider_cached_input_tokens") or 0),
        )
        decision_cost = decision_price.cost(
            input_tokens=int(metrics.get("decision_input_tokens") or 0),
            output_tokens=int(metrics.get("decision_output_tokens") or 0),
            cached_input_tokens=0,
        )
        return {
            "generator_cost_usd": generator_cost,
            "decision_cost_usd": decision_cost,
            "total_cost_usd": generator_cost + decision_cost,
        }

    def record_frontier_tokens(self, record: Mapping[str, Any]) -> int:
        metrics = dict(record.get("metrics") or {})
        tokens = int(metrics.get("provider_input_tokens") or 0) + int(metrics.get("provider_output_tokens") or 0)
        if str(record.get("condition") or "") in self.frontier_decision_conditions:
            tokens += int(metrics.get("decision_input_tokens") or 0) + int(metrics.get("decision_output_tokens") or 0)
        if tokens < 0:
            raise ValueError("frontier token counts cannot be negative")
        return tokens


def _sample(record: Mapping[str, Any], cost_model: BenchmarkCostModel) -> OutcomeSample:
    metrics = dict(record.get("metrics") or {})
    return OutcomeSample(
        verified=str(record.get("status") or "") == "verified",
        false_completion=int(metrics.get("false_completion_claims") or 0) > 0,
        cost_usd=cost_model.record_cost_usd(record),
    )


def _metrics(records: list[Mapping[str, Any]], samples: list[OutcomeSample], cost_model: BenchmarkCostModel) -> dict[str, Any]:
    if not samples:
        return {
            "missions": 0, "vsr": None, "fcr": None, "cpvo_usd": None,
            "mean_tvo_s": None, "frontier_tokens": 0,
            "frontier_intelligence_efficiency": None,
            "verified_per_million_frontier_tokens": None,
        }
    verified = sum(s.verified for s in samples)
    false = sum(s.false_completion for s in samples)
    total_cost = sum(s.cost_usd for s in samples)
    verified_wall = [
        float((r.get("metrics") or {}).get("wall_time_ms") or 0.0) / 1000.0
        for r, sample in zip(records, samples) if sample.verified
    ]
    frontier_tokens = sum(cost_model.record_frontier_tokens(r) for r in records)
    fie = (verified / frontier_tokens) if frontier_tokens else None
    return {
        "missions": len(samples),
        "verified": verified,
        "vsr": verified / len(samples),
        "fcr": false / len(samples),
        "total_cost_usd": total_cost,
        "cpvo_usd": total_cost / verified if verified else None,
        "mean_tvo_s": (sum(verified_wall) / len(verified_wall)) if verified_wall else None,
        "frontier_tokens": frontier_tokens,
        "frontier_intelligence_efficiency": fie,
        "verified_per_million_frontier_tokens": (fie * 1_000_000.0) if fie is not None else None,
    }


def build_campaign_report(
    records: Iterable[Mapping[str, Any]],
    *,
    incumbent_condition: str,
    candidate_condition: str,
    cost_model: BenchmarkCostModel,
    shadow_pairs: int,
    experiment_pairs: int,
    holdout_pairs: int,
    min_holdout_trials: int,
    noninferiority_margin: float = 0.02,
    max_fcr: float = 0.0,
) -> dict[str, Any]:
    """Drive the statistical promotion gate from paired benchmark evidence.

    Pairing is exact on ``(case_id, repeat)`` and fails closed if either condition
    is absent or duplicated. The function never fabricates counterfactual outcomes.
    """

    rows = [dict(r) for r in records]
    keyed: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in rows:
        condition = str(row.get("condition") or "")
        if condition not in {incumbent_condition, candidate_condition}:
            continue
        key = (str(row.get("case_id") or ""), int(row.get("repeat") or 0), condition)
        if not key[0] or key[1] <= 0:
            raise ValueError("benchmark records require case_id and positive repeat")
        if key in keyed:
            raise ValueError("paired benchmark contains duplicate condition record")
        keyed[key] = row

    pair_keys = sorted({(case, repeat) for case, repeat, _ in keyed})
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case, repeat in pair_keys:
        incumbent = keyed.get((case, repeat, incumbent_condition))
        candidate = keyed.get((case, repeat, candidate_condition))
        if incumbent is None or candidate is None:
            raise ValueError(f"paired benchmark missing paired condition for {case!r} repeat {repeat}")
        pairs.append((incumbent, candidate))

    expected = shadow_pairs + experiment_pairs + holdout_pairs
    if len(pairs) != expected:
        raise ValueError(f"paired benchmark requires exactly {expected} paired missions; got {len(pairs)}")

    candidate = LearningCandidate(
        candidate_id=f"campaign:{candidate_condition}",
        decision_family="control-plane",
        incumbent_strategy=incumbent_condition,
        candidate_strategy=candidate_condition,
    )
    policy = PromotionPolicy(
        vsr_noninferiority_margin=noninferiority_margin,
        max_fcr=max_fcr,
        require_lower_cpvo=True,
    )
    campaign = LearningCampaign(
        candidate=candidate,
        policy=policy,
        min_holdout_trials=min_holdout_trials,
        noninferiority_margin=noninferiority_margin,
    )
    controller = AutoCampaignController(
        campaign,
        AutoCampaignSchedule(
            shadow_pairs=shadow_pairs,
            experiment_pairs=experiment_pairs,
            holdout_pairs=holdout_pairs,
        ),
    )
    incumbent_samples: list[OutcomeSample] = []
    candidate_samples: list[OutcomeSample] = []
    incumbent_records: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    phase_trace: list[str] = []
    for incumbent_record, candidate_record in pairs:
        inc = _sample(incumbent_record, cost_model)
        cand = _sample(candidate_record, cost_model)
        incumbent_samples.append(inc)
        candidate_samples.append(cand)
        incumbent_records.append(incumbent_record)
        candidate_records.append(candidate_record)
        before = campaign.state.value
        controller.record_pair(incumbent=inc, candidate=cand)
        phase_trace.append(f"{before}->{campaign.state.value}")

    promotion = campaign.promotion_decision()
    incumbent_metrics = _metrics(incumbent_records, incumbent_samples, cost_model)
    candidate_metrics = _metrics(candidate_records, candidate_samples, cost_model)
    inc_fie = incumbent_metrics["frontier_intelligence_efficiency"]
    cand_fie = candidate_metrics["frontier_intelligence_efficiency"]
    fie_ratio = (cand_fie / inc_fie) if inc_fie and cand_fie else None
    return {
        "paired_missions": len(pairs),
        "incumbent_condition": incumbent_condition,
        "candidate_condition": candidate_condition,
        "state": campaign.state.value,
        "phase_trace": phase_trace,
        "incumbent_metrics": incumbent_metrics,
        "candidate_metrics": candidate_metrics,
        "frontier_intelligence_efficiency_ratio": fie_ratio,
        "promotion": promotion,
        "truth_boundary": "promotion uses only observed paired benchmark records and explicit token prices",
    }
