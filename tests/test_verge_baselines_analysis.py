import json

from experiments.verge.analysis import summarize_runs
from experiments.verge.baselines import run_ga, run_pareto, run_qd, run_random
from experiments.verge.harness import load_cases


def test_search_baselines_are_reproducible_and_budget_matched():
    cases = load_cases()
    runners = (run_random, run_ga, run_pareto, run_qd)
    results = []
    for runner in runners:
        a = runner(cases, seed=12, population_size=8, generations=4)
        b = runner(cases, seed=12, population_size=8, generations=4)
        assert a == b
        assert a.evaluations == 40
        results.append(a)
    assert len({r.name for r in results}) == 4


def test_summary_reports_cost_normalized_and_safety_metrics():
    cases = load_cases()
    runs = [
        run_random(cases, seed=1, population_size=8, generations=3),
        run_random(cases, seed=2, population_size=8, generations=3),
    ]
    summary = summarize_runs(runs)
    assert summary["runs"] == 2
    assert "mean_best_quality" in summary
    assert "mean_unauthorized_actions" in summary
    assert "mean_cost_per_verified_outcome" in summary
    json.dumps(summary, sort_keys=True)
