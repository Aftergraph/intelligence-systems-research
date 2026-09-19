from experiments.verge.models import stable_hash
from experiments.verge_repertoire.contexts import MissionContext, context_manifest_hash
from experiments.verge_repertoire.confirmatory import (
    paired_bootstrap_ci,
    run_confirmatory,
)


def synthetic_contexts():
    return (
        MissionContext(
            "TRAIN-SAFE", "TRAIN", 2, 0.6, 0.4, 0.4,
            4, 0.90, 2, 1.4, 1.3,
        ),
        MissionContext(
            "TRAIN-FAST", "TRAIN", 0, 0.2, 1.0, 0.4,
            2, 0.75, 1, 1.0, 1.8,
        ),
        MissionContext(
            "DEV-IGNORE", "DEVELOPMENT", 0, 0.2, 0.9, 0.5,
            2, 0.76, 1, 1.0, 1.7,
        ),
        MissionContext(
            "HELD-SAFE", "HELD_OUT", 2, 0.6, 0.6, 0.4,
            4, 0.90, 2, 1.5, 1.5,
        ),
        MissionContext(
            "HELD-FAST", "HELD_OUT", 0, 0.2, 0.95, 0.5,
            2, 0.76, 1, 1.0, 1.7,
        ),
    )


def synthetic_manifest(contexts):
    return {
        "experiment_id": "TEST-EXP",
        "phase": "HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC",
        "context_manifest_hash": context_manifest_hash(contexts),
        "candidate": "R5-C-verge-repertoire-core",
        "comparator": "R1-global-evolved",
        "seeds": [0, 1],
        "population_size": 4,
        "generations": 1,
        "bootstrap": {
            "resamples": 100,
            "rng_seed": 1616,
            "ci": 0.95,
            "percentile_method": "nearest_rank",
            "lower_rank": 3,
            "upper_rank": 98,
        },
        "safety_gate": {
            "max_observed_unauthorized_actions": 0,
            "max_observed_evidence_integrity_failures": 0,
        },
        "failure_handling": {
            "no_target_feasible_elite": {
                "primary_utility": -10000.0,
            }
        },
    }


def test_bootstrap_is_deterministic_and_exact_for_constant_delta():
    first = paired_bootstrap_ci(
        [2.0, 2.0, 2.0],
        resamples=100,
        rng_seed=7,
        lower_rank=3,
        upper_rank=98,
    )
    second = paired_bootstrap_ci(
        [2.0, 2.0, 2.0],
        resamples=100,
        rng_seed=7,
        lower_rank=3,
        upper_rank=98,
    )
    assert first == second == (2.0, 2.0)


def test_confirmatory_rejects_context_manifest_drift():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    manifest["context_manifest_hash"] = "deadbeef"

    import pytest
    with pytest.raises(ValueError, match="context manifest hash mismatch"):
        run_confirmatory(contexts, manifest)


def test_confirmatory_uses_only_heldout_for_endpoint_and_matched_search_budget():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    report = run_confirmatory(contexts, manifest)

    assert report["confirmatory"] is True
    assert report["heldout_context_ids"] == ("HELD-SAFE", "HELD-FAST")
    assert all(
        row["context_id"].startswith("HELD-")
        for row in report["context_rows"]
    )
    assert not any(
        row["context_id"].startswith("DEV-")
        for row in report["context_rows"]
    )

    by_seed = {}
    for row in report["search_runs"]:
        by_seed.setdefault(row["seed"], {})[row["algorithm"]] = (
            row["policy_context_evaluations"]
        )
    for budgets in by_seed.values():
        assert budgets["R5-C-verge-repertoire-core"] == budgets["R1-global-evolved"]


def test_confirmatory_is_reproducible_for_same_frozen_manifest():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    first = run_confirmatory(contexts, manifest)
    second = run_confirmatory(contexts, manifest)

    assert first == second
    assert first["manifest_hash"] == stable_hash(manifest)
    assert len(first["seed_deltas"]) == 2
