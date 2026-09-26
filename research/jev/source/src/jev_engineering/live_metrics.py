from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MissionMeasurement:
    mission_id: str
    condition: str
    declared_complete: bool
    verified: bool
    cost_usd: float
    wall_time_s: float
    frontier_input_tokens: int = 0
    frontier_output_tokens: int = 0

    def __post_init__(self) -> None:
        if self.cost_usd < 0 or self.wall_time_s < 0:
            raise ValueError("cost/time cannot be negative")
        if self.frontier_input_tokens < 0 or self.frontier_output_tokens < 0:
            raise ValueError("token counts cannot be negative")


@dataclass(frozen=True, slots=True)
class ConditionMetrics:
    condition: str
    missions: int
    verified_successes: int
    false_completions: int
    vsr: float
    fcr: float
    cpvo_usd: float | None
    mean_tvo_s: float | None
    frontier_tokens: int
    frontier_intelligence_efficiency: float | None


def summarize_measurements(rows: Iterable[MissionMeasurement], *, condition: str) -> ConditionMetrics:
    selected = [r for r in rows if r.condition == condition]
    n = len(selected)
    if n == 0:
        raise ValueError("condition has no measurements")
    verified = [r for r in selected if r.verified]
    false = [r for r in selected if r.declared_complete and not r.verified]
    total_cost = sum(r.cost_usd for r in selected)
    frontier_tokens = sum(r.frontier_input_tokens + r.frontier_output_tokens for r in selected)
    verified_count = len(verified)
    cpvo = total_cost / verified_count if verified_count else None
    tvo = mean(r.wall_time_s for r in verified) if verified else None
    fie = verified_count / frontier_tokens if frontier_tokens else None
    return ConditionMetrics(
        condition=condition,
        missions=n,
        verified_successes=verified_count,
        false_completions=len(false),
        vsr=verified_count / n,
        fcr=len(false) / n,
        cpvo_usd=cpvo,
        mean_tvo_s=tvo,
        frontier_tokens=frontier_tokens,
        frontier_intelligence_efficiency=fie,
    )


def paired_frontier_efficiency_ratio(a: ConditionMetrics, b: ConditionMetrics) -> float | None:
    """Return B/A verified-outcomes-per-frontier-token ratio.

    This is only meaningful when both conditions consumed frontier tokens and
    should never be represented as a general quality multiplier.
    """
    if not a.frontier_intelligence_efficiency or not b.frontier_intelligence_efficiency:
        return None
    return b.frontier_intelligence_efficiency / a.frontier_intelligence_efficiency
