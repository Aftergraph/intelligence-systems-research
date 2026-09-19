from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import mean

from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_repertoire.repertoire import (
    Repertoire,
    RepertoireEntry,
    evaluate_in_context,
)


DEFAULT_CONFIDENCE_SHOCKS = (0.00, 0.02, 0.04)
DEFAULT_LATENCY_SHOCKS = (0.00, 0.10)
DEFAULT_COST_SHOCKS = (0.00, 0.10)


@dataclass(frozen=True)
class HaloSelection:
    entry: RepertoireEntry
    worst_utility: float
    mean_utility: float
    descriptor_distance: float
    halo_evaluations: int


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def make_halo(
    target: MissionContext,
    *,
    confidence_shocks: tuple[float, ...] = DEFAULT_CONFIDENCE_SHOCKS,
    latency_shocks: tuple[float, ...] = DEFAULT_LATENCY_SHOCKS,
    cost_shocks: tuple[float, ...] = DEFAULT_COST_SHOCKS,
) -> tuple[MissionContext, ...]:
    points: list[MissionContext] = []
    for confidence in confidence_shocks:
        for latency in latency_shocks:
            for cost in cost_shocks:
                suffix = (
                    f"c{confidence:.2f}-"
                    f"l{latency:.2f}-"
                    f"k{cost:.2f}"
                )
                points.append(
                    replace(
                        target,
                        context_id=f"{target.context_id}#halo-{suffix}",
                        min_confidence=_clip01(
                            target.min_confidence + confidence
                        ),
                        latency_pressure=_clip01(
                            target.latency_pressure + latency
                        ),
                        cost_pressure=_clip01(
                            target.cost_pressure + cost
                        ),
                    )
                )
    return tuple(points)


def _descriptor_distance(
    entry: RepertoireEntry,
    target: MissionContext,
) -> float:
    target_descriptor = target.descriptor()
    return sum(
        (left - right) ** 2
        for left, right in zip(
            entry.source_descriptor,
            target_descriptor,
        )
    )


def select_halo_robust(
    repertoire: Repertoire,
    target: MissionContext,
    *,
    confidence_shocks: tuple[float, ...] = DEFAULT_CONFIDENCE_SHOCKS,
    latency_shocks: tuple[float, ...] = DEFAULT_LATENCY_SHOCKS,
    cost_shocks: tuple[float, ...] = DEFAULT_COST_SHOCKS,
) -> HaloSelection:
    points = make_halo(
        target,
        confidence_shocks=confidence_shocks,
        latency_shocks=latency_shocks,
        cost_shocks=cost_shocks,
    )
    if not points:
        raise ValueError("halo must contain at least one point")

    candidates: list[HaloSelection] = []
    entries = repertoire.entries()
    for entry in entries:
        nominal = evaluate_in_context(entry.genome, target)
        if not nominal.feasible:
            continue

        outcomes = [
            evaluate_in_context(entry.genome, point)
            for point in points
        ]
        if not all(outcome.feasible for outcome in outcomes):
            continue

        utilities = [outcome.utility for outcome in outcomes]
        candidates.append(
            HaloSelection(
                entry=entry,
                worst_utility=min(utilities),
                mean_utility=mean(utilities),
                descriptor_distance=_descriptor_distance(
                    entry,
                    target,
                ),
                halo_evaluations=len(points),
            )
        )

    if not candidates:
        raise LookupError("no halo-feasible elite")

    return max(
        candidates,
        key=lambda selection: (
            selection.worst_utility,
            selection.mean_utility,
            -selection.descriptor_distance,
            selection.entry.source_context_id,
        ),
    ).__class__(
        entry=max(
            candidates,
            key=lambda selection: (
                selection.worst_utility,
                selection.mean_utility,
                -selection.descriptor_distance,
                selection.entry.source_context_id,
            ),
        ).entry,
        worst_utility=max(
            candidates,
            key=lambda selection: (
                selection.worst_utility,
                selection.mean_utility,
                -selection.descriptor_distance,
                selection.entry.source_context_id,
            ),
        ).worst_utility,
        mean_utility=max(
            candidates,
            key=lambda selection: (
                selection.worst_utility,
                selection.mean_utility,
                -selection.descriptor_distance,
                selection.entry.source_context_id,
            ),
        ).mean_utility,
        descriptor_distance=max(
            candidates,
            key=lambda selection: (
                selection.worst_utility,
                selection.mean_utility,
                -selection.descriptor_distance,
                selection.entry.source_context_id,
            ),
        ).descriptor_distance,
        halo_evaluations=len(entries) * len(points),
    )
