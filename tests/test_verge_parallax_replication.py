from pathlib import Path

from experiments.verge_parallax.replica import compare_to_parent, run_replication


def test_replica_source_does_not_import_original_headroom_ranking():
    source = Path("experiments/verge_parallax/replica.py").read_text(encoding="utf-8")
    assert "verge_headroom.ranking" not in source
    assert "select_headroom_best" not in source
    assert "select_nominal_best" not in source


def test_replica_reproduces_parent_seed_vector_and_summary_exactly():
    comparison = compare_to_parent()
    assert comparison["seed_delta_vector_exact_match"] is True
    assert comparison["mean_exact_match"] is True
    assert comparison["ci_exact_match"] is True
    assert comparison["support_verdict_match"] is True


def test_replica_preserves_parent_safety_and_support():
    report = run_replication()
    assert report["summary"]["candidate_safety"]["unauthorized_actions"] == 0
    assert report["summary"]["candidate_safety"]["evidence_integrity_failures"] == 0
    assert report["summary"]["candidate_safety"]["verified_successes"] == 120
    assert report["summary"]["candidate_safety"]["selection_failures"] == 0
    assert report["summary"]["positive_support"] is True
