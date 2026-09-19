from experiments.verge_bastion.study import run_development_pilot


def test_development_pilot_uses_equal_total_search_budget():
    report = run_development_pilot(
        seeds=(0, 1),
        policy_context_budget_per_niche=128,
        population_size=8,
    )
    for seed in (0, 1):
        rows = [r for r in report["search_runs"] if r["seed"] == seed]
        assert len(rows) == 2
        budgets = {r["algorithm"]: r["policy_context_evaluations"] for r in rows}
        assert budgets["NOMINAL-REPERTOIRE"] == budgets["BASTION-ROBUST-REPERTOIRE"]


def test_development_pilot_does_not_evaluate_heldout():
    report = run_development_pilot(
        seeds=(0,),
        policy_context_budget_per_niche=128,
        population_size=8,
    )
    assert report["held_out_evaluated"] is False
    assert report["development_context_ids"]
    assert all(cid.startswith("DEV-") for cid in report["development_context_ids"])
    assert all(row["context_id"].startswith("DEV-") for row in report["context_rows"])


def test_development_pilot_is_reproducible():
    first = run_development_pilot(
        seeds=(0, 1),
        policy_context_budget_per_niche=128,
        population_size=8,
    )
    second = run_development_pilot(
        seeds=(0, 1),
        policy_context_budget_per_niche=128,
        population_size=8,
    )
    assert first == second


def test_development_pilot_reports_robust_coverage_and_worst_delta():
    report = run_development_pilot(
        seeds=(0, 1, 2),
        policy_context_budget_per_niche=128,
        population_size=8,
    )
    assert len(report["seed_worst_deltas"]) == 3
    assert 0.0 <= report["summary"]["bastion_train_robust_coverage"] <= 1.0
    assert 0.0 <= report["summary"]["nominal_train_robust_coverage"] <= 1.0
    for row in report["seed_worst_deltas"]:
        assert row["delta_worst"] == (
            row["bastion_worst_utility"] - row["nominal_worst_utility"]
        )
