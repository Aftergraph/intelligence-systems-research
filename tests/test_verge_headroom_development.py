from experiments.verge_headroom.study import run_development_pilot


def test_development_uses_identical_candidate_sets_and_budgets():
    report = run_development_pilot(seeds=(0, 1), candidate_budget_per_niche=128)

    for seed in (0, 1):
        rows = [r for r in report["search_runs"] if r["seed"] == seed]
        assert len(rows) == 2
        by_alg = {r["algorithm"]: r for r in rows}
        assert by_alg["NOMINAL-RANK"]["policy_context_evaluations"] == by_alg["HEADROOM-RANK"]["policy_context_evaluations"]
        assert by_alg["NOMINAL-RANK"]["candidate_set_hash"] == by_alg["HEADROOM-RANK"]["candidate_set_hash"]


def test_development_does_not_touch_heldout():
    report = run_development_pilot(seeds=(0,), candidate_budget_per_niche=128)
    assert report["held_out_evaluated"] is False
    assert all(cid.startswith("DEV-") for cid in report["development_context_ids"])
    assert all(row["context_id"].startswith("DEV-") for row in report["context_rows"])


def test_development_is_reproducible():
    first = run_development_pilot(seeds=(0, 1), candidate_budget_per_niche=128)
    second = run_development_pilot(seeds=(0, 1), candidate_budget_per_niche=128)
    assert first == second


def test_development_reports_worst_context_delta():
    report = run_development_pilot(seeds=(0, 1, 2), candidate_budget_per_niche=128)
    assert len(report["seed_worst_deltas"]) == 3
    for row in report["seed_worst_deltas"]:
        assert row["delta_worst"] == (
            row["headroom_worst_utility"] - row["nominal_worst_utility"]
        )
