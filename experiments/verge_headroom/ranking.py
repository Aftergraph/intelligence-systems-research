from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from experiments.verge.models import PolicyGenome
from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_repertoire.repertoire import ContextEvaluation


@dataclass(frozen=True)
class RankedElite:
    genome: PolicyGenome
    outcome: ContextEvaluation
    normalized_min_headroom: float
    confidence_headroom: float
    verification_headroom: int
    retry_headroom: int


def headroom_components(
    genome: PolicyGenome,
    context: MissionContext,
) -> tuple[float, int, int]:
    return (
        genome.confidence_threshold - context.min_confidence,
        genome.verification_depth - context.min_verification,
        genome.retry_ceiling - context.min_retries,
    )


def normalized_min_headroom(
    genome: PolicyGenome,
    context: MissionContext,
) -> float:
    confidence, verification, retry = headroom_components(genome, context)
    return min(
        confidence / 0.10,
        verification / 2.0,
        retry / 2.0,
    )


def _eligible(
    rows: Iterable[tuple[PolicyGenome, ContextEvaluation]],
    context: MissionContext,
) -> list[RankedElite]:
    eligible: list[RankedElite] = []
    for genome, outcome in rows:
        if not outcome.feasible:
            continue
        confidence, verification, retry = headroom_components(genome, context)
        if confidence < 0 or verification < 0 or retry < 0:
            continue
        eligible.append(
            RankedElite(
                genome=genome,
                outcome=outcome,
                normalized_min_headroom=normalized_min_headroom(genome, context),
                confidence_headroom=confidence,
                verification_headroom=verification,
                retry_headroom=retry,
            )
        )
    if not eligible:
        raise LookupError("no feasible elite")
    return eligible


def select_nominal_best(
    rows: Iterable[tuple[PolicyGenome, ContextEvaluation]],
    context: MissionContext,
) -> RankedElite:
    eligible = _eligible(rows, context)
    return max(
        eligible,
        key=lambda item: (
            item.outcome.utility,
            -item.outcome.cost,
            -item.outcome.latency,
            item.genome.identity,
        ),
    )


def select_headroom_best(
    rows: Iterable[tuple[PolicyGenome, ContextEvaluation]],
    context: MissionContext,
) -> RankedElite:
    eligible = _eligible(rows, context)
    return max(
        eligible,
        key=lambda item: (
            item.normalized_min_headroom,
            item.outcome.utility,
            -item.outcome.cost,
            -item.outcome.latency,
            item.genome.identity,
        ),
    )
