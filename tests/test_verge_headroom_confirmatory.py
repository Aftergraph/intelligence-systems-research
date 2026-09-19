from experiments.verge.models import stable_hash
from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_headroom.contexts import context_manifest_hash
from experiments.verge_headroom.confirmatory import (
    paired_bootstrap_ci,
    run_confirmatory,
)


def synthetic_contexts():
    return (
        MissionContext("TRAIN-A","TRAIN",2,0.6,0.4,0.4,4,0.89,2,1.4,1.3),
        MissionContext("TRAIN-B","TRAIN",0,0.2,1.0,0.4,2,0.75,1,1.0,1.8),
        MissionContext("DEV-IGNORE","DEVELOPMENT",1,0.5,0.6,0.6,3,0.83,2,1.3,1.3),
        MissionContext("HELD-A","HELD_OUT",2,0.65,0.7,0.5,4,0.93,2,1.5,1.5),
        MissionContext("HELD-B","HELD_OUT",0,0.3,1.0,0.6,2,0.81,1,1.1,1.9),
    )


def synthetic_manifest(contexts):
    return {
        "experiment_id":"TEST-HDR",
        "phase":"HELD_OUT_CONFIRMATORY_INTERNAL_SYNTHETIC",
        "context_manifest_hash":context_manifest_hash(contexts),
        "candidate":"HEADROOM-RANK",
        "comparator":"NOMINAL-RANK",
        "seeds":[0,1],
        "candidate_budget_per_niche":64,
        "population_size":8,
        "bootstrap":{
            "resamples":100,
            "rng_seed":2021,
            "lower_rank":3,
            "upper_rank":98,
        },
        "safety_gate":{
            "max_observed_unauthorized_actions":0,
            "max_observed_evidence_integrity_failures":0,
        },
        "failure_handling":{
            "no_target_feasible_elite":{
                "primary_utility":-10000.0,
            }
        },
    }


def test_bootstrap_is_deterministic():
    assert paired_bootstrap_ci(
        [2.0,2.0,2.0],
        resamples=100,
        rng_seed=2021,
        lower_rank=3,
        upper_rank=98,
    ) == (2.0,2.0)


def test_confirmatory_rejects_context_manifest_drift():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    manifest["context_manifest_hash"] = "deadbeef"
    import pytest
    with pytest.raises(ValueError, match="context manifest hash mismatch"):
        run_confirmatory(contexts, manifest)


def test_confirmatory_uses_heldout_only_and_same_candidate_sets():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    report = run_confirmatory(contexts, manifest)

    assert report["heldout_context_ids"] == ("HELD-A","HELD-B")
    assert all(row["context_id"].startswith("HELD-") for row in report["context_rows"])
    assert not any(row["context_id"].startswith("DEV-") for row in report["context_rows"])

    for seed in manifest["seeds"]:
        rows = [r for r in report["search_runs"] if r["seed"] == seed]
        assert len(rows) == 2
        hashes = {r["candidate_set_hash"] for r in rows}
        assert len(hashes) == 1


def test_confirmatory_is_reproducible_and_manifest_bound():
    contexts = synthetic_contexts()
    manifest = synthetic_manifest(contexts)
    first = run_confirmatory(contexts, manifest)
    second = run_confirmatory(contexts, manifest)
    assert first == second
    assert first["manifest_hash"] == stable_hash(manifest)
    assert len(first["seed_worst_deltas"]) == 2
