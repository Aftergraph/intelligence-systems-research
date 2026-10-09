from experiments.verge.baselines import run_fixed
from experiments.verge.engine import evolve
from experiments.verge.harness import load_cases


def test_fixed_governed_baseline_is_feasible_on_frozen_s2_pack():
    result = run_fixed(load_cases(), seed=0, population_size=4, generations=1)
    assert result.best.outcome.feasible is True
    assert result.best.outcome.objectives.unauthorized_actions == 0


def test_verge_never_returns_infeasible_candidate_across_frozen_seed_pack():
    cases = load_cases()
    for seed in range(30):
        result = evolve(cases, seed=seed, population_size=20, generations=10)
        assert result.best.outcome.feasible is True, seed
        assert result.best.outcome.objectives.unauthorized_actions == 0, seed
