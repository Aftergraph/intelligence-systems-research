from experiments.verge_repertoire.contexts import load_contexts
from experiments.verge_repertoire.study import (
    build_random_repertoire,
    evolve_global_policy,
    evolve_global_pareto_policy,
    run_development_pilot,
)
from experiments.verge_repertoire.repertoire import (
    evolve_fixed_repertoire,
    evolve_repertoire,
)


def test_global_policy_training_uses_train_contexts_only_and_matched_context_budget():
    contexts = load_contexts()
    result = evolve_global_policy(
        contexts,
        seed=5,
        population_size=8,
        generations=4,
    )
    train_count = sum(c.split == "TRAIN" for c in contexts)
    assert result.training_context_ids
    assert all(cid.startswith("TRAIN-") for cid in result.training_context_ids)
    assert result.policy_context_evaluations == 8 * (4 + 1) * train_count


def test_development_pilot_is_reproducible_and_does_not_touch_heldout():
    first = run_development_pilot(
        seeds=(0, 1, 2),
        population_size=6,
        generations=3,
    )
    second = run_development_pilot(
        seeds=(0, 1, 2),
        population_size=6,
        generations=3,
    )
    assert first == second
    assert first["evidence_class"] == "EXPLORATORY_DEVELOPMENT"
    assert first["confirmatory"] is False
    assert first["held_out_evaluated"] is False
    assert first["development_context_ids"]
    assert all(cid.startswith("DEV-") for cid in first["development_context_ids"])
    assert not any("HELD-" in row["context_id"] for row in first["rows"])


def test_search_conditions_use_equal_policy_context_evaluation_budget():
    report = run_development_pilot(
        seeds=(0,),
        population_size=6,
        generations=2,
    )
    search_rows = [
        row for row in report["search_runs"]
        if row["algorithm"] in {"R1-global-evolved", "R6-verge-repertoire"}
    ]
    assert len(search_rows) == 2
    assert len({row["policy_context_evaluations"] for row in search_rows}) == 1


def test_repertoire_selector_can_outperform_static_global_policy_on_at_least_one_dev_context():
    report = run_development_pilot(
        seeds=tuple(range(6)),
        population_size=8,
        generations=4,
    )
    deltas = [
        row["utility_delta_repertoire_minus_global"]
        for row in report["paired_context_rows"]
    ]
    assert any(delta > 0 for delta in deltas)


def test_random_repertoire_uses_same_train_budget_as_verge_repertoire():
    contexts = load_contexts()
    result = build_random_repertoire(
        contexts,
        seed=9,
        evaluations_per_context=24,
    )
    train_count = sum(c.split == "TRAIN" for c in contexts)
    assert result.evaluations == 24 * train_count
    assert result.training_context_ids
    assert all(cid.startswith("TRAIN-") for cid in result.training_context_ids)
    assert len(result.repertoire) > 0


def test_development_pilot_includes_matched_random_repertoire_ablation():
    report = run_development_pilot(
        seeds=(0,),
        population_size=6,
        generations=2,
    )
    rows = {
        row["algorithm"]: row["policy_context_evaluations"]
        for row in report["search_runs"]
    }
    assert rows["R3-random-repertoire"] == rows["R6-verge-repertoire"]


def test_fixed_and_adaptive_repertoires_have_equal_search_budget():
    contexts = load_contexts()
    fixed = evolve_fixed_repertoire(
        contexts,
        seed=4,
        population_size=6,
        generations=3,
    )
    adaptive = evolve_repertoire(
        contexts,
        seed=4,
        population_size=6,
        generations=3,
    )
    assert fixed.evaluations == adaptive.evaluations
    assert fixed.training_context_ids == adaptive.training_context_ids
    assert fixed.adaptive is False
    assert adaptive.adaptive is True


def test_development_pilot_compares_fixed_operator_repertoire_to_adaptive_verge():
    report = run_development_pilot(
        seeds=(0,),
        population_size=6,
        generations=2,
    )
    rows = {
        row["algorithm"]: row["policy_context_evaluations"]
        for row in report["search_runs"]
    }
    assert rows["R5-fixed-operator-repertoire"] == rows["R6-verge-repertoire"]
    assert "mean_utility_delta_verge_minus_fixed_repertoire" in report["summary"]


def test_global_pareto_training_uses_matched_train_budget():
    contexts = load_contexts()
    result = evolve_global_pareto_policy(
        contexts,
        seed=6,
        population_size=8,
        generations=4,
    )
    train_count = sum(c.split == "TRAIN" for c in contexts)
    assert result.policy_context_evaluations == 8 * (4 + 1) * train_count
    assert all(cid.startswith("TRAIN-") for cid in result.training_context_ids)


def test_development_pilot_freezes_strongest_non_repertoire_comparator():
    report = run_development_pilot(
        seeds=(0, 1, 2),
        population_size=6,
        generations=3,
    )
    rows = {
        row["algorithm"]: row["policy_context_evaluations"]
        for row in report["search_runs"]
        if row["seed"] == 0
    }
    assert rows["R4-global-pareto"] == rows["R1-global-evolved"]
    assert report["primary_non_repertoire_comparator"] in {
        "R1-global-evolved",
        "R4-global-pareto",
    }
