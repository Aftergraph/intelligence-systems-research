from __future__ import annotations

from dataclasses import dataclass

from .evaluation import EvaluationOutcome


@dataclass(frozen=True)
class BehaviorDescriptor:
    parallelism: int
    intervention_band: int
    verification_depth: int


@dataclass(frozen=True)
class ArchiveEntry:
    candidate_id: str
    descriptor: BehaviorDescriptor
    outcome: EvaluationOutcome


def _quality_key(outcome: EvaluationOutcome) -> tuple[float, ...]:
    obj = outcome.objectives
    return (
        float(obj.verified_success),
        float(obj.recovery),
        -float(obj.false_completion),
        -float(obj.unauthorized_actions),
        -float(obj.cost),
        -float(obj.latency),
        -float(obj.human_interventions),
    )


class QDArchive:
    def __init__(self) -> None:
        self._cells: dict[BehaviorDescriptor, ArchiveEntry] = {}

    def insert(
        self,
        candidate_id: str,
        descriptor: BehaviorDescriptor,
        outcome: EvaluationOutcome,
    ) -> bool:
        if not outcome.feasible:
            return False
        current = self._cells.get(descriptor)
        proposed = ArchiveEntry(candidate_id, descriptor, outcome)
        if current is None or _quality_key(outcome) > _quality_key(current.outcome):
            self._cells[descriptor] = proposed
            return True
        return False

    def get(self, descriptor: BehaviorDescriptor) -> ArchiveEntry:
        return self._cells[descriptor]

    def entries(self) -> tuple[ArchiveEntry, ...]:
        return tuple(self._cells[key] for key in sorted(
            self._cells,
            key=lambda d: (d.parallelism, d.intervention_band, d.verification_depth),
        ))

    def __len__(self) -> int:
        return len(self._cells)
