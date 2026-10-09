from __future__ import annotations

from dataclasses import dataclass

from .evaluation import ObjectiveVector


_MAXIMIZE = ("verified_success", "recovery")
_MINIMIZE = (
    "false_completion",
    "unauthorized_actions",
    "cost",
    "latency",
    "human_interventions",
)


@dataclass(frozen=True)
class ScoredCandidate:
    candidate_id: str
    objectives: ObjectiveVector


def dominates(a: ObjectiveVector, b: ObjectiveVector) -> bool:
    no_worse = True
    strictly_better = False
    for field in _MAXIMIZE:
        av, bv = getattr(a, field), getattr(b, field)
        no_worse &= av >= bv
        strictly_better |= av > bv
    for field in _MINIMIZE:
        av, bv = getattr(a, field), getattr(b, field)
        no_worse &= av <= bv
        strictly_better |= av < bv
    return bool(no_worse and strictly_better)


def nondominated_fronts(candidates: list[ScoredCandidate]) -> list[list[ScoredCandidate]]:
    remaining = list(candidates)
    fronts: list[list[ScoredCandidate]] = []
    while remaining:
        front = [
            candidate
            for candidate in remaining
            if not any(
                dominates(other.objectives, candidate.objectives)
                for other in remaining
                if other.candidate_id != candidate.candidate_id
            )
        ]
        if not front:
            raise ValueError("unable to construct nondominated front")
        fronts.append(front)
        front_ids = {candidate.candidate_id for candidate in front}
        remaining = [candidate for candidate in remaining if candidate.candidate_id not in front_ids]
    return fronts
