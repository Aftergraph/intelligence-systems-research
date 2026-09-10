"""SDC-B0 Task #57: Semantic Progress Metric Scorer — GREEN Implementation.

Protocol source: docs/sdc/b0/2026-09-09-semantic-progress-metric.md

Semantic progress measures independently accepted capability movement,
NOT raw commit count or tool-call volume. This is the primary success
indicator for SDC-B0 continuous runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Event classification (frozen by spec)
# ---------------------------------------------------------------------------

# +1 positive units: one per independently verified merged change
_POSITIVE_EVENT_TYPES = frozenset({
    "bug_closure_verified",              # test added + fix merged + CI green
    "capability_accepted",               # spec-bound task merged with tests
    "test_coverage_verified",            # previously absent behavior now covered
    "performance_improvement_validated", # benchmark delta >= 5% on primary metric
    "security_correction_verified",      # independent review confirmed
    "spec_completion_approved",          # frozen document merged
})

# -1 penalties (one each)
_NEGATIVE_EVENT_TYPES = frozenset({
    "work_reverted",                  # merge reverted within same run
    "duplicate_work",                 # same capability implemented twice
    "work_conflict",                  # incompatible changes requiring reconciliation
    "stale_base_invalidated",         # work discarded due to base drift
    "regression_unresolved",          # test failure persisting > 2 hours
    "reconciliation_debt_accrual",    # unmerged branch w/ conflicts > 2 sample intervals
    "false_completion_claim",         # handoff says complete but verifier rejects
    "human_intervention",             # manual merge/revert/fix/override/unblock/scope-adjust
})

# 0 neutral (no score change)
_NEUTRAL_EVENT_TYPES = frozenset({
    "refactor_no_behavioral_change",
    "documentation_not_bound_to_spec",
    "test_only_no_new_coverage",
    "dependency_bump_no_security_fix",
})


@dataclass(frozen=True)
class UnmergedBranch:
    """State of one unmerged branch for reconciliation debt computation.

    Attributes:
        branch_name: git branch name.
        age_hours: hours since last update (unmerged).
        conflict_count: unresolved conflict count on this branch.
        worker_id: owning worker id (for telemetry context / deduplication).
    """
    branch_name: str
    age_hours: float
    conflict_count: int
    worker_id: str = ""


class SemanticProgressScorer:
    """Scores SDC-B0 telemetry events per the frozen semantic-progress rubric.

    Construction:
        scorer = SemanticProgressScorer(events)   # batch from existing log
        scorer = SemanticProgressScorer()          # empty, then add_event()

    Live ingestion:
        scorer.add_event(event)   # one telemetry event dict

    Branch / debt state (needed for reconciliation debt):
        scorer.update_branches([UnmergedBranch(...), ...])
        scorer.set_active_workers(n)

    Query API:
        scorer.score()        -> int   (positive units minus penalty units)
        scorer.debt()         -> float (reconciliation debt per frozen formula)
        scorer.interventions() -> int (human_intervention count)

    Frozen reconciliation debt formula:
        debt = sum(age_hours * conflict_count_per_branch) / max(active_workers, 1)

    When active_worker_count is zero, denominator = 1 (avoids div-by-zero
    and ensures debt keeps accumulating for unmerged branches).
    """

    def __init__(self, telemetry_events: list[dict[str, Any]] | None = None,
                 active_workers: int = 0) -> None:
        self._score: int = 0
        self._human_interventions: int = 0
        self._branches: dict[str, UnmergedBranch] = {}
        self._active_workers: int = max(active_workers, 0)
        if telemetry_events:
            for evt in telemetry_events:
                self.add_event(evt)

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def score(self) -> int:
        """Current semantic progress score."""
        return self._score

    def debt(self) -> float:
        """Reconciliation debt per frozen formula.

        debt = sum(age_hours * conflict_count) / max(active_workers, 1)
        """
        if not self._branches:
            return 0.0
        numerator = sum(
            b.age_hours * b.conflict_count for b in self._branches.values()
        )
        denominator = max(self._active_workers, 1)
        return numerator / denominator

    def interventions(self) -> int:
        """Number of human_intervention events processed."""
        return self._human_interventions

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def add_event(self, event: dict[str, Any]) -> None:
        """Process one telemetry event and update the running score."""
        event_type = event.get("event", "")
        if event_type in _POSITIVE_EVENT_TYPES:
            self._score += 1
        elif event_type in _NEGATIVE_EVENT_TYPES:
            if event_type == "human_intervention":
                self._human_interventions += 1
            self._score -= 1
        # neutral: no-op

    # ------------------------------------------------------------------
    # Branch / worker tracking (needed for debt computation)
    # ------------------------------------------------------------------

    def update_branches(self, branches: list[UnmergedBranch]) -> None:
        """Replace the tracked unmerged-branch set.

        Called by the run monitor whenever branch state changes (new branch,
        age tick, conflict resolution, merge).
        """
        self._branches = {b.branch_name: b for b in branches}

    def set_active_workers(self, count: int) -> None:
        """Update the number of currently active workers.

        The debt denominator is max(active_workers, 1).
        """
        self._active_workers = max(count, 0)

    def branch_count(self) -> int:
        """Number of currently tracked unmerged branches."""
        return len(self._branches)
