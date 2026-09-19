from experiments.verge_crucible.contexts import load_contexts
from experiments.verge_crucible.search import (
    evolve_crucible_context,
    evolve_nominal_context_matched,
)


def test_crucible_exact_budget_accounting():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-CRU-RISK-A")
    result = evolve_crucible_context(context, seed=1)
    assert result.policy_context_evaluations == 256
    assert result.candidate_evaluations == 144
    assert result.promoted_candidates == 16


def test_nominal_exact_budget_accounting():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-CRU-RISK-A")
    result = evolve_nominal_context_matched(context, seed=1)
    assert result.policy_context_evaluations == 256
    assert result.candidate_evaluations == 256


def test_crucible_returns_robust_feasible_elite():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-CRU-RISK-A")
    result = evolve_crucible_context(context, seed=7)
    assert result.robust_feasible is True
    assert result.worst_halo_utility > -10000


def test_crucible_search_is_reproducible():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-CRU-REC-A")
    assert evolve_crucible_context(context, seed=9) == evolve_crucible_context(context, seed=9)
