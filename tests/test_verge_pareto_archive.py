from experiments.verge.archive import BehaviorDescriptor, QDArchive
from experiments.verge.evaluation import EvaluationOutcome, ObjectiveVector
from experiments.verge.pareto import ScoredCandidate, dominates, nondominated_fronts


def objectives(vsr=1, fcr=0, uar=0, cost=1.0, latency=1.0, hir=0, recovery=1):
    return ObjectiveVector(
        verified_success=vsr,
        false_completion=fcr,
        unauthorized_actions=uar,
        cost=cost,
        latency=latency,
        human_interventions=hir,
        recovery=recovery,
    )


def outcome(obj=None, feasible=True):
    obj = obj or objectives()
    return EvaluationOutcome(
        feasible=feasible,
        reasons=() if feasible else ("unauthorized_action",),
        verified_success=obj.verified_success,
        false_completion=obj.false_completion,
        objectives=obj,
    )


def test_dominates_when_no_objective_is_worse_and_one_is_better():
    assert dominates(objectives(cost=1.0), objectives(cost=2.0))


def test_dominance_detects_tradeoff_as_incomparable():
    fast_expensive = objectives(cost=3.0, latency=1.0)
    slow_cheap = objectives(cost=1.0, latency=3.0)
    assert not dominates(fast_expensive, slow_cheap)
    assert not dominates(slow_cheap, fast_expensive)


def test_nondominated_fronts_separate_dominated_candidate():
    a = ScoredCandidate("a", objectives(cost=1.0))
    b = ScoredCandidate("b", objectives(cost=2.0))
    c = ScoredCandidate("c", objectives(cost=0.5, latency=2.0))
    fronts = nondominated_fronts([a, b, c])
    assert {x.candidate_id for x in fronts[0]} == {"a", "c"}
    assert [x.candidate_id for x in fronts[1]] == ["b"]


def test_archive_rejects_infeasible_candidate():
    archive = QDArchive()
    descriptor = BehaviorDescriptor(parallelism=1, intervention_band=0, verification_depth=2)
    inserted = archive.insert("bad", descriptor, outcome(feasible=False))
    assert inserted is False
    assert len(archive) == 0


def test_archive_replaces_cell_only_with_higher_quality_candidate():
    archive = QDArchive()
    descriptor = BehaviorDescriptor(parallelism=2, intervention_band=0, verification_depth=2)
    assert archive.insert("old", descriptor, outcome(objectives(cost=3.0))) is True
    assert archive.insert("worse", descriptor, outcome(objectives(cost=4.0))) is False
    assert archive.insert("better", descriptor, outcome(objectives(cost=2.0))) is True
    assert archive.get(descriptor).candidate_id == "better"


def test_archive_keeps_behaviorally_distinct_elites():
    archive = QDArchive()
    d1 = BehaviorDescriptor(parallelism=1, intervention_band=0, verification_depth=2)
    d2 = BehaviorDescriptor(parallelism=4, intervention_band=0, verification_depth=2)
    archive.insert("serial", d1, outcome())
    archive.insert("parallel", d2, outcome())
    assert {entry.candidate_id for entry in archive.entries()} == {"serial", "parallel"}
