from experiments.verge.models import stable_hash
from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_halo.contexts import context_manifest_hash
from experiments.verge_halo.confirmatory import (
    paired_bootstrap_ci,
    run_confirmatory,
)


def synthetic_contexts():
    return (
        MissionContext(
            "TRAIN-A", "TRAIN", 2, 0.60, 0.45, 0.35,
            4, 0.88, 2, 1.45, 1.35,
        ),
        MissionContext(
            "TRAIN-B", "TRAIN", 0, 0.20, 1.00, 0.35,
            2, 0.74, 1, 1.00, 1.85,
        ),
        MissionContext(
            "DEV-IGNORE", "DEVELOPMENT", 1, 0.55, 0.60, 0.60,
            3, 0.82, 2, 1.30, 1.30,
        ),
        MissionContext(
            "HELD-A", "HELD_OUT", 2, 0.62, 0.70, 0.42,
            4, 0.90, 2, 1.55, 1.50,
        ),
        MissionContext(
            "HELD-B", "HELD_OUT", 0, 0.25, 0.98, 0.55,
            2, 0.77, 1, 1.10, 1.80,
        ),
    )


def synthetic_manifest(contexts):
    return {
        "experiment_id": "TEST-HALO",
        "phase": "HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC",
        "context_manifest_hash": context_manifest_hash(contexts),
        "shared_search": "R5-C-fixed-operator-repertoire",
        "candidate_selector": "HALO",
        "comparator_selector": "NOMINAL",
        "seeds": [0, 1],
        "population_size": 4,
        "generations": 1,
        "halo": {
            "confidence_shocks": [0.0, 0.02, 0.04],
            "latency_shocks": [0.0, 0.10],
            "cost_shocks": [0.0, 0.10],
        },
        "bootstrap": {
            "resamples": 100,
            "rng_seed": 1717,
            "lower_rank": 3,
            "upper_rank": 98,
        },
        "safety_gate": {
            "max_observed_unauthorized_actions": 0,
            "max_observed_evidence_integrity_failures": 0,
        },
        "failure_handling": {
            "no_eligible_elite": {
                "primary_utility": -10000.0,
            }
        },
    }


def test_bootstrap_is_deterministic_for_constant_delta():
    first = paired_bootstrap_ci(
        [3.0, 3.0, 3.0],
        resamples=100,
        rng_seed=1717,
        lower_rank=3,
        upper_rank=98,
    )
    second = paired_bootstrap_ci(
        [3.0, 3.0, 3.0],
        resamples=100,
        rng_seed=1717,
        lower_rank=3,
        upper_rank=98,
    )
    assert first == second == (3.0, 3.0)


def test_confirmatory_rejects_context_manifest_drift():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    manifest["context_manifest_hash"] = "deadbeef"

    import pytest
    with pytest.raises(ValueError, match="context manifest hash mismatch"):
        run_confirmatory(contexts, manifest)


def test_confirmatory_reuses_one_search_per_seed_for_both_selectors():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    report = run_confirmatory(contexts, manifest)

    assert len(report["search_runs"]) == len(manifest["seeds"])
    for seed in manifest["seeds"]:
        seed_search = [
            row for row in report["search_runs"]
            if row["seed"] == seed
        ]
        assert len(seed_search) == 1
        seed_rows = [
            row for row in report["context_rows"]
            if row["seed"] == seed
        ]
        assert {row["selector"] for row in seed_rows} == {
            "HALO",
            "NOMINAL",
        }
        assert len({row["repertoire_hash"] for row in seed_rows}) == 1


def test_confirmatory_endpoint_uses_heldout_actual_target_utility_only():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    report = run_confirmatory(contexts, manifest)

    assert report["heldout_context_ids"] == ("HELD-A", "HELD-B")
    assert all(
        row["context_id"].startswith("HELD-")
        for row in report["context_rows"]
    )
    assert not any(
        row["context_id"].startswith("DEV-")
        for row in report["context_rows"]
    )

    for seed_row in report["seed_worst_deltas"]:
        assert seed_row["delta_worst"] == (
            seed_row["halo_worst_actual_utility"]
            - seed_row["nominal_worst_actual_utility"]
        )


def test_confirmatory_is_reproducible_and_manifest_bound():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    first = run_confirmatory(contexts, manifest)
    second = run_confirmatory(contexts, manifest)

    assert first == second
    assert first["confirmatory"] is True
    assert first["manifest_hash"] == stable_hash(manifest)
    assert len(first["seed_worst_deltas"]) == 2
