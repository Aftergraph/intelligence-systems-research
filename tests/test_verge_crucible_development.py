from experiments.verge_crucible.study import run_development_pilot


def test_crucible_development_uses_equal_total_policy_context_budget():
    report = run_development_pilot(seeds=(0, 1))
    for seed in (0, 1):
        rows = [r for r in report["search_runs"] if r["seed"] == seed]
        assert len(rows) == 2
        budgets = {r["algorithm"]: r["policy_context_evaluations"] for r in rows}
        assert budgets["NOMINAL-REPERTOIRE"] == budgets["CRUCIBLE-REPERTOIRE"]


def test_crucible_development_never_evaluates_heldout():
    report = run_development_pilot(seeds=(0,))
    assert report["held_out_evaluated"] is False
    assert all(cid.startswith("DEV-") for cid in report["development_context_ids"])
    assert all(row["context_id"].startswith("DEV-") for row in report["context_rows"])


def test_crucible_development_is_reproducible():
    assert run_development_pilot(seeds=(0, 1)) == run_development_pilot(seeds=(0, 1))
