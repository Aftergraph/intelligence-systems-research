from pathlib import Path

import pytest

from experiments.institutional_containment.runner import (
    EXECUTION_CLASS,
    EXECUTION_ENGINE,
    manifest_digest,
    run_condition,
)


MANIFEST = Path("data/study012_scenario_manifest.json")


def test_manifest_digest_is_stable_sha256():
    digest = manifest_digest(MANIFEST)
    assert len(digest) == 64
    assert all(ch in "0123456789abcdef" for ch in digest)
    assert digest == manifest_digest(MANIFEST)


def test_runner_records_exact_execution_engine_and_manifest_digest():
    records = run_condition("I0", manifest_path=MANIFEST, seed=12001)
    assert records
    expected_digest = manifest_digest(MANIFEST)
    assert all(record["execution_engine"] == EXECUTION_ENGINE for record in records)
    assert all(record["manifest_sha256"] == expected_digest for record in records)
    assert all(record["execution_class"] == EXECUTION_CLASS for record in records)


def test_runner_is_deterministic_for_same_seed_and_manifest():
    first = run_condition("I4", manifest_path=MANIFEST, seed=12001)
    second = run_condition("I4", manifest_path=MANIFEST, seed=12001)
    assert first == second


def test_runner_rejects_any_fallback_or_substituted_execution_mode():
    with pytest.raises(ValueError, match="fallback"):
        run_condition(
            "I0",
            manifest_path=MANIFEST,
            seed=12001,
            fallback_mode="simulation",
        )


def test_runner_rejects_manifest_that_is_not_study012():
    with pytest.raises(ValueError, match="STUDY-012"):
        run_condition("I0", manifest={"study_id": "OTHER"}, seed=12001)
