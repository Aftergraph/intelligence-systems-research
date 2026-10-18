from experiments.verge.pilot import run_pilot


def test_pilot_runs_matched_algorithms_and_emits_paired_rows():
    report = run_pilot(seeds=(0, 1), population_size=6, generations=2)
    assert report["configuration"]["evaluations_per_run"] == 18
    assert len(report["rows"]) == 12
    algorithms = {row["algorithm"] for row in report["rows"]}
    assert algorithms == {
        "B0-random",
        "B1-fixed",
        "B2-simple-ga",
        "B5-pareto-style",
        "B6-qd-style",
        "B11-verge",
    }
    for seed in (0, 1):
        seed_rows = [row for row in report["rows"] if row["seed"] == seed]
        assert {row["evaluations"] for row in seed_rows} == {18}


def test_pilot_report_separates_exploratory_evidence_from_confirmatory_claims():
    report = run_pilot(seeds=(0,), population_size=4, generations=1)
    assert report["evidence_class"] == "EXPLORATORY_SYNTHETIC"
    assert report["confirmatory"] is False
    assert "does not establish real-agent superiority" in report["claim_boundary"]
