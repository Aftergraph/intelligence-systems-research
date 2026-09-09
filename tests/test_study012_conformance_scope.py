import json
from pathlib import Path

import pytest

from experiments.institutional_containment.runner import (
    EXECUTION_CLASS,
    run_condition,
    run_workload_matrix,
)


SCENARIO_MANIFEST = Path("data/study012_scenario_manifest.json")
WORKLOAD_MANIFEST = Path("data/study012_workload_manifest.json")
POWER_PLAN = Path("data/study012_power_plan.json")
SOURCE_COMMIT = "a" * 40


def test_execution_class_explicitly_marks_conformance_only_evidence():
    assert EXECUTION_CLASS == "SYNTHETIC_CONFORMANCE_VALID"
    records = run_condition("I0", manifest_path=SCENARIO_MANIFEST, seed=12001)
    assert records
    assert all(record["evidence_scope"] == "CONFORMANCE_ONLY" for record in records)
    assert all(record["confirmatory_eligible"] is False for record in records)


def test_workload_matrix_cannot_be_switched_into_confirmatory_mode():
    with pytest.raises(ValueError, match="confirmatory"):
        run_workload_matrix(
            manifest_path=WORKLOAD_MANIFEST,
            replicate_id="R001",
            seed=12001,
            source_commit=SOURCE_COMMIT,
            confirmatory=True,
        )


def test_default_workload_matrix_records_are_never_confirmatory_eligible():
    records = run_workload_matrix(
        manifest_path=WORKLOAD_MANIFEST,
        replicate_id="R001",
        seed=12001,
        source_commit=SOURCE_COMMIT,
    )
    assert records
    assert all(record["execution_class"] == "SYNTHETIC_CONFORMANCE_VALID" for record in records)
    assert all(record["evidence_scope"] == "CONFORMANCE_ONLY" for record in records)
    assert all(record["confirmatory_eligible"] is False for record in records)


def test_power_plan_is_explicitly_invalid_for_current_deterministic_harness():
    plan = json.loads(POWER_PLAN.read_text(encoding="utf-8"))
    assert plan["valid_for_current_harness"] is False
    assert plan["confirmatory_authorized"] is False
    assert plan["review_disposition"] == "INVALIDATED_FOR_CURRENT_DETERMINISTIC_HARNESS"
