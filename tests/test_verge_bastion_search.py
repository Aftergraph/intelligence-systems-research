from experiments.verge_bastion.contexts import (
    context_manifest_hash,
    load_contexts,
)
from experiments.verge_bastion.robust_search import (
    DEFAULT_TRAIN_CONFIDENCE_SHOCKS,
    DEFAULT_TRAIN_COST_SHOCKS,
    DEFAULT_TRAIN_LATENCY_SHOCKS,
    evolve_nominal_context,
    evolve_robust_context,
    make_training_halo,
)


def test_context_splits_are_disjoint_and_manifest_hash_is_stable():
    contexts = load_contexts()
    splits = {
        split: {c.context_id for c in contexts if c.split == split}
        for split in ("TRAIN", "DEVELOPMENT", "HELD_OUT")
    }
    assert all(splits.values())
    assert splits["TRAIN"].isdisjoint(splits["DEVELOPMENT"])
    assert splits["TRAIN"].isdisjoint(splits["HELD_OUT"])
    assert splits["DEVELOPMENT"].isdisjoint(splits["HELD_OUT"])
    assert context_manifest_hash(contexts) == context_manifest_hash(load_contexts())


def test_training_halo_has_frozen_eight_point_cartesian_product():
    context = next(c for c in load_contexts() if c.split == "TRAIN")
    halo = make_training_halo(context)
    assert len(halo) == (
        len(DEFAULT_TRAIN_CONFIDENCE_SHOCKS)
        * len(DEFAULT_TRAIN_LATENCY_SHOCKS)
        * len(DEFAULT_TRAIN_COST_SHOCKS)
    ) == 8
    assert len({point.context_id for point in halo}) == 8


def test_nominal_and_robust_context_search_consume_exact_equal_budget():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-BAS-RISK-A")
    budget = 256

    nominal = evolve_nominal_context(
        context,
        seed=3,
        policy_context_budget=budget,
        population_size=8,
    )
    robust = evolve_robust_context(
        context,
        seed=3,
        policy_context_budget=budget,
        population_size=8,
    )

    assert nominal.policy_context_evaluations == budget
    assert robust.policy_context_evaluations == budget
    assert nominal.candidate_evaluations == budget
    assert robust.candidate_evaluations == budget // 8


def test_robust_search_returns_halo_feasible_elite():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-BAS-RISK-A")
    result = evolve_robust_context(
        context,
        seed=7,
        policy_context_budget=256,
        population_size=8,
    )
    assert result.robust_feasible is True
    assert result.worst_halo_utility > -10000
    assert result.mean_halo_utility > -10000


def test_search_is_reproducible():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-BAS-REC-A")
    first = evolve_robust_context(
        context,
        seed=11,
        policy_context_budget=256,
        population_size=8,
    )
    second = evolve_robust_context(
        context,
        seed=11,
        policy_context_budget=256,
        population_size=8,
    )
    assert first == second
