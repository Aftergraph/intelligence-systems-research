"""GREEN tests for SDC-B0 Task #57: Semantic Progress Metric Scorer.

Protocol source: docs/sdc/b0/2026-09-09-semantic-progress-metric.md
"""
from __future__ import annotations

from typing import Any

import pytest

from src.sdc_b0.semantic_progress import SemanticProgressScorer, UnmergedBranch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pos(event_type: str, **extra: Any) -> dict[str, Any]:
    d: dict[str, Any] = {"event": event_type}
    d.update(extra)
    return d


def _neg(event_type: str, **extra: Any) -> dict[str, Any]:
    return _pos(event_type, **extra)


# ---------------------------------------------------------------------------
# Construction / empty baseline
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_empty_scorer_has_zero_score(self) -> None:
        s = SemanticProgressScorer()
        assert s.score() == 0

    def test_empty_scorer_has_zero_debt(self) -> None:
        s = SemanticProgressScorer()
        assert s.debt() == 0.0

    def test_empty_scorer_has_zero_interventions(self) -> None:
        s = SemanticProgressScorer()
        assert s.interventions() == 0

    def test_batch_seed_from_list(self) -> None:
        events = [
            _pos("bug_closure_verified"),
            _neg("work_reverted"),
        ]
        s = SemanticProgressScorer(events)
        assert s.score() == 0  # +1 -1

    def test_batch_seed_respects_human_interventions(self) -> None:
        events = [
            _neg("human_intervention"),
            _neg("human_intervention"),
            _pos("capability_accepted"),
        ]
        s = SemanticProgressScorer(events)
        assert s.score() == -1  # +1 -2
        assert s.interventions() == 2


# ---------------------------------------------------------------------------
# Positive event types (+1 each)
# ---------------------------------------------------------------------------

class TestPositiveEvents:
    POSITIVE_TYPES = [
        "bug_closure_verified",
        "capability_accepted",
        "test_coverage_verified",
        "performance_improvement_validated",
        "security_correction_verified",
        "spec_completion_approved",
    ]

    @pytest.mark.parametrize("event_type", POSITIVE_TYPES)
    def test_each_positive_event_increments_score(self, event_type: str) -> None:
        s = SemanticProgressScorer()
        s.add_event(_pos(event_type))
        assert s.score() == 1

    def test_multiple_positive_events_sum(self) -> None:
        s = SemanticProgressScorer()
        for et in self.POSITIVE_TYPES:
            s.add_event(_pos(et))
        assert s.score() == len(self.POSITIVE_TYPES)


# ---------------------------------------------------------------------------
# Negative event types (-1 each)
# ---------------------------------------------------------------------------

class TestNegativeEvents:
    NEGATIVE_TYPES = [
        "work_reverted",
        "duplicate_work",
        "work_conflict",
        "stale_base_invalidated",
        "regression_unresolved",
        "reconciliation_debt_accrual",
        "false_completion_claim",
        "human_intervention",
    ]

    @pytest.mark.parametrize("event_type", NEGATIVE_TYPES)
    def test_each_negative_event_decrements_score(self, event_type: str) -> None:
        s = SemanticProgressScorer()
        s.add_event(_neg(event_type))
        assert s.score() == -1

    def test_multiple_negative_events_sum(self) -> None:
        s = SemanticProgressScorer()
        for et in self.NEGATIVE_TYPES:
            s.add_event(_neg(et))
        assert s.score() == -len(self.NEGATIVE_TYPES)


# ---------------------------------------------------------------------------
# Human intervention tracking
# ---------------------------------------------------------------------------

class TestHumanIntervention:
    def test_human_intervention_increments_counter(self) -> None:
        s = SemanticProgressScorer()
        assert s.interventions() == 0
        s.add_event(_neg("human_intervention"))
        assert s.interventions() == 1
        s.add_event(_neg("human_intervention"))
        assert s.interventions() == 2

    def test_non_human_events_do_not_increment_counter(self) -> None:
        s = SemanticProgressScorer()
        s.add_event(_pos("bug_closure_verified"))
        s.add_event(_neg("work_reverted"))
        assert s.interventions() == 0

    def test_mixed_score_and_interventions(self) -> None:
        s = SemanticProgressScorer()
        s.add_event(_pos("capability_accepted"))   # +1, int=0
        s.add_event(_neg("human_intervention"))     # -1, int=1
        s.add_event(_neg("work_reverted"))          # -1, int=1
        assert s.score() == -1
        assert s.interventions() == 1


# ---------------------------------------------------------------------------
# Neutral events (0)
# ---------------------------------------------------------------------------

class TestNeutralEvents:
    NEUTRAL_TYPES = [
        "refactor_no_behavioral_change",
        "documentation_not_bound_to_spec",
        "test_only_no_new_coverage",
        "dependency_bump_no_security_fix",
    ]

    @pytest.mark.parametrize("event_type", NEUTRAL_TYPES)
    def test_each_neutral_event_leaves_score_unchanged(self, event_type: str) -> None:
        s = SemanticProgressScorer()
        s.add_event(_pos(event_type))
        assert s.score() == 0

    def test_neutral_events_do_not_add_to_interventions(self) -> None:
        s = SemanticProgressScorer()
        for et in self.NEUTRAL_TYPES:
            s.add_event(_pos(et))
        assert s.interventions() == 0

    def test_neutral_events_between_positive_negative(self) -> None:
        s = SemanticProgressScorer()
        s.add_event(_pos("bug_closure_verified"))     # +1
        s.add_event(_pos("refactor_no_behavioral_change"))  # 0
        s.add_event(_neg("work_reverted"))            # -1
        assert s.score() == 0


# ---------------------------------------------------------------------------
# Unknown event types (unknown events are neutral)
# ---------------------------------------------------------------------------

class TestUnknownEvents:
    def test_unknown_event_is_neutral(self) -> None:
        s = SemanticProgressScorer()
        s.add_event({"event": "completely_unknown_event_type"})
        assert s.score() == 0

    def test_unknown_event_does_not_increment_interventions(self) -> None:
        s = SemanticProgressScorer()
        s.add_event({"event": "ghost_event"})
        assert s.interventions() == 0


# ---------------------------------------------------------------------------
# Reconciliation debt formula
# ---------------------------------------------------------------------------

class TestReconciliationDebt:
    def test_empty_branches_returns_zero_debt(self) -> None:
        s = SemanticProgressScorer()
        assert s.debt() == 0.0

    def test_single_branch_debt(self) -> None:
        s = SemanticProgressScorer(active_workers=2)
        s.update_branches([
            UnmergedBranch(branch_name="b1", age_hours=5.0, conflict_count=3,
                           worker_id="w1"),
        ])
        # 5 * 3 / max(2,1) = 15 / 2 = 7.5
        assert s.debt() == pytest.approx(7.5)

    def test_multiple_branches_summed(self) -> None:
        s = SemanticProgressScorer(active_workers=1)
        s.update_branches([
            UnmergedBranch(branch_name="b1", age_hours=2.0, conflict_count=4,
                           worker_id="w1"),
            UnmergedBranch(branch_name="b2", age_hours=3.0, conflict_count=2,
                           worker_id="w2"),
        ])
        # (2*4 + 3*2) / max(1,1) = (8 + 6) / 1 = 14.0
        assert s.debt() == pytest.approx(14.0)

    def test_active_workers_zero_defaults_denominator_to_one(self) -> None:
        s = SemanticProgressScorer(active_workers=0)
        s.update_branches([
            UnmergedBranch(branch_name="b1", age_hours=10.0, conflict_count=5,
                           worker_id="w1"),
        ])
        # 10 * 5 / max(0,1) = 50 / 1 = 50.0
        assert s.debt() == pytest.approx(50.0)

    def test_set_active_workers_updates_denominator(self) -> None:
        s = SemanticProgressScorer(active_workers=1)
        s.update_branches([
            UnmergedBranch(branch_name="b1", age_hours=6.0, conflict_count=2,
                           worker_id="w1"),
        ])
        # 6*2 / 1 = 12
        assert s.debt() == pytest.approx(12.0)
        s.set_active_workers(3)
        # 6*2 / 3 = 4
        assert s.debt() == pytest.approx(4.0)

    def test_branches_with_zero_conflict_yield_zero_contribution(self) -> None:
        s = SemanticProgressScorer(active_workers=2)
        s.update_branches([
            UnmergedBranch(branch_name="clean", age_hours=100.0, conflict_count=0,
                           worker_id="w1"),
        ])
        assert s.debt() == 0.0

    def test_branches_replaced_on_update(self) -> None:
        s = SemanticProgressScorer(active_workers=1)
        s.update_branches([
            UnmergedBranch(branch_name="old", age_hours=1.0, conflict_count=1,
                           worker_id="w1"),
        ])
        assert s.debt() == pytest.approx(1.0)
        s.update_branches([])  # clear all
        assert s.debt() == 0.0

    def test_debt_is_float(self) -> None:
        s = SemanticProgressScorer(active_workers=2)
        s.update_branches([
            UnmergedBranch(branch_name="b1", age_hours=1.0, conflict_count=1,
                           worker_id="w1"),
        ])
        assert isinstance(s.debt(), float)

    def test_debt_formula_matches_frozen_spec_literal(self) -> None:
        """Reproduce the exact frozen formula:
        debt = sum(age_hours * conflict_count) / max(active_workers, 1)
        """
        branches = [
            UnmergedBranch(branch_name="x", age_hours=2.5, conflict_count=4,
                           worker_id="w1"),
            UnmergedBranch(branch_name="y", age_hours=1.0, conflict_count=1,
                           worker_id="w2"),
        ]
        active = 3
        expected = (2.5 * 4 + 1.0 * 1) / max(active, 1)
        s = SemanticProgressScorer(active_workers=active)
        s.update_branches(branches)
        assert s.debt() == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Branch / worker API surface
# ---------------------------------------------------------------------------

class TestBranchApi:
    def test_branch_count_reflects_updated_set(self) -> None:
        s = SemanticProgressScorer()
        assert s.branch_count() == 0
        s.update_branches([
            UnmergedBranch(branch_name="a", age_hours=1.0, conflict_count=1),
        ])
        assert s.branch_count() == 1
        s.update_branches([
            UnmergedBranch(branch_name="a", age_hours=1.0, conflict_count=1),
            UnmergedBranch(branch_name="b", age_hours=2.0, conflict_count=3),
        ])
        assert s.branch_count() == 2

    def test_active_workers_clamped_to_nonnegative(self) -> None:
        s = SemanticProgressScorer(active_workers=5)
        s.set_active_workers(-3)
        assert s._active_workers == 0
