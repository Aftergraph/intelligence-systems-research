import json
from collections import defaultdict
from pathlib import Path

import pytest

from experiments.institutional_containment.harness import CONDITIONS
from experiments.institutional_containment.runner import run_workload_matrix


WORKLOAD_MANIFEST = Path("data/study012_workload_manifest.json")
SOURCE_COMMIT = "a" * 40
PAIR_FIELDS = (
    "workload_id",
    "scenario_id",
    "replicate_id",
    "seed",
    "model_id",
    "runtime_version",
    "fixture_state_sha256",
    "mission_contract_version",
    "workload_manifest_sha256",
    "source_commit",
)


def _records(seed: int = 1207001):
    return run_workload_matrix(
        manifest_path=WORKLOAD_MANIFEST,
        replicate_id="R001",
        seed=seed,
        source_commit=SOURCE_COMMIT,
    )


def test_workload_runner_executes_three_domains_times_ten_scenarios_times_seven_conditions():
    records = _records()
    assert len(records) == 3 * 10 * 7
    assert {record["condition"] for record in records} == set(CONDITIONS)
    assert len({record["workload_id"] for record in records}) == 3
    assert len({record["scenario_id"] for record in records}) == 10


def test_each_pair_has_exactly_one_record_per_condition_and_identical_pair_identity():
    grouped = defaultdict(list)
    for record in _records():
        grouped[(record["workload_id"], record["scenario_id"], record["replicate_id"])].append(record)

    assert len(grouped) == 30
    for pair_records in grouped.values():
        assert len(pair_records) == len(CONDITIONS)
        assert {record["condition"] for record in pair_records} == set(CONDITIONS)
        for field in PAIR_FIELDS:
            assert len({record[field] for record in pair_records}) == 1, field
        assert len({record["run_id"] for record in pair_records}) == len(CONDITIONS)


def test_pair_identity_is_bound_to_explicit_frozen_manifest_metadata():
    manifest = json.loads(WORKLOAD_MANIFEST.read_text(encoding="utf-8"))
    records = _records()

    assert manifest["model_id"] == "synthetic-deterministic-agent-v1"
    assert manifest["runtime_version"] == "synthetic_in_process_v1"
    assert manifest["mission_contract_version"] == "study012-synthetic-v1"
    assert all(record["model_id"] == manifest["model_id"] for record in records)
    assert all(record["runtime_version"] == manifest["runtime_version"] for record in records)
    assert all(
        record["mission_contract_version"] == manifest["mission_contract_version"]
        for record in records
    )
    assert all(record["source_commit"] == SOURCE_COMMIT for record in records)
    assert all(len(record["fixture_state_sha256"]) == 64 for record in records)
    assert all(len(record["workload_manifest_sha256"]) == 64 for record in records)


def test_condition_order_is_randomized_per_pair_but_deterministic_for_same_seed():
    first = _records(seed=1207001)
    second = _records(seed=1207001)
    assert first == second

    grouped = defaultdict(list)
    for record in first:
        grouped[(record["workload_id"], record["scenario_id"])].append(record["condition"])

    assert all(set(order) == set(CONDITIONS) for order in grouped.values())
    assert len({tuple(order) for order in grouped.values()}) > 1


def test_different_master_seed_changes_execution_order_not_pair_membership():
    first = _records(seed=1207001)
    second = _records(seed=1207002)

    first_members = {
        (r["workload_id"], r["scenario_id"], r["replicate_id"], r["condition"])
        for r in first
    }
    second_members = {
        (r["workload_id"], r["scenario_id"], r["replicate_id"], r["condition"])
        for r in second
    }
    assert first_members == second_members
    assert [r["run_id"] for r in first] != [r["run_id"] for r in second]


def test_source_commit_is_required_and_must_be_full_sha():
    with pytest.raises(ValueError, match="source_commit"):
        run_workload_matrix(
            manifest_path=WORKLOAD_MANIFEST,
            replicate_id="R001",
            seed=1207001,
            source_commit="main",
        )


def test_replicate_id_is_required_and_path_opaque():
    for bad in ("", "../R001", "R/001", "R 001"):
        with pytest.raises(ValueError, match="replicate_id"):
            run_workload_matrix(
                manifest_path=WORKLOAD_MANIFEST,
                replicate_id=bad,
                seed=1207001,
                source_commit=SOURCE_COMMIT,
            )
