from experiments.verge_halo.study import run_development_pilot


def test_development_pilot_reuses_one_repertoire_for_both_selector_arms():
    report = run_development_pilot(
        seeds=(0, 1),
        population_size=6,
        generations=2,
    )

    assert report["confirmatory"] is False
    assert report["held_out_evaluated"] is False
    assert len(report["search_runs"]) == 2
    assert {row["seed"] for row in report["search_runs"]} == {0, 1}
    assert all(
        row["algorithm"] == "SHARED-R5-C-FIXED-REPERTOIRE"
        for row in report["search_runs"]
    )

    for seed in (0, 1):
        seed_rows = [
            row for row in report["context_rows"]
            if row["seed"] == seed
        ]
        hashes = {row["repertoire_hash"] for row in seed_rows}
        assert len(hashes) == 1
        assert {row["selector"] for row in seed_rows} == {
            "NOMINAL",
            "HALO",
        }


def test_development_pilot_never_evaluates_heldout_contexts():
    report = run_development_pilot(
        seeds=(0,),
        population_size=6,
        generations=2,
    )
    assert report["development_context_ids"]
    assert all(
        context_id.startswith("DEV-")
        for context_id in report["development_context_ids"]
    )
    assert all(
        row["context_id"].startswith("DEV-")
        for row in report["context_rows"]
    )
    assert not any(
        "HELD-" in row["context_id"]
        for row in report["context_rows"]
    )


def test_development_pilot_reports_seed_worst_context_delta():
    report = run_development_pilot(
        seeds=(0, 1, 2),
        population_size=6,
        generations=2,
    )

    assert len(report["seed_worst_deltas"]) == 3
    for seed_row in report["seed_worst_deltas"]:
        expected = (
            seed_row["halo_worst_utility"]
            - seed_row["nominal_worst_utility"]
        )
        assert seed_row["delta_worst"] == expected

    assert report["summary"]["seeds"] == 3
    assert (
        report["summary"]["halo_safety_failures"] >= 0
    )
    assert (
        report["summary"]["nominal_safety_failures"] >= 0
    )


def test_development_pilot_is_reproducible():
    first = run_development_pilot(
        seeds=(0, 1),
        population_size=6,
        generations=2,
    )
    second = run_development_pilot(
        seeds=(0, 1),
        population_size=6,
        generations=2,
    )
    assert first == second
