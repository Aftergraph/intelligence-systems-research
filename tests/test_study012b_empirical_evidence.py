from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.institutional_containment.empirical_evidence import (
    B1_EVIDENCE_VERSION,
    persist_b1_evidence,
)
from experiments.institutional_containment.empirical_matrix import run_paired_empirical_matrix


SOURCE_COMMIT = "1" * 40


def _records(tmp_path: Path) -> list[dict[str, object]]:
    return run_paired_empirical_matrix(
        root=tmp_path / "fixtures",
        replicate_id="r001",
        seed=17,
        perturbation="nominal",
    )


def test_b1_evidence_reuses_append_only_hash_attested_store(tmp_path: Path) -> None:
    records = _records(tmp_path)
    destination = persist_b1_evidence(
        root=tmp_path / "evidence",
        execution_id="study012b-b1-r001-s17",
        records=records,
        source_commit=SOURCE_COMMIT,
    )

    assert destination.name == "study012b-b1-r001-s17"
    assert {path.name for path in destination.iterdir()} == {
        "metadata.json",
        "metrics.json",
        "verifier.json",
        "stdout.log",
        "stderr.log",
        "artifacts.sha256",
    }

    lines = (destination / "artifacts.sha256").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    for line in lines:
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest


def test_metadata_binds_exact_records_source_commit_and_matrix_version(tmp_path: Path) -> None:
    records = _records(tmp_path)
    destination = persist_b1_evidence(
        root=tmp_path / "evidence",
        execution_id="study012b-b1-r001-s17",
        records=records,
        source_commit=SOURCE_COMMIT,
    )
    metadata = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))

    assert metadata["study_id"] == "STUDY-012B"
    assert metadata["evidence_scope"] == "HARNESS_VALIDATION_ONLY"
    assert metadata["confirmatory_eligible"] is False
    assert metadata["evidence_version"] == B1_EVIDENCE_VERSION
    assert metadata["source_commit"] == SOURCE_COMMIT
    assert metadata["records"] == records
    assert len(metadata["record_sha256"]) == len(records)

    for record, digest in zip(records, metadata["record_sha256"], strict=True):
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        assert hashlib.sha256(canonical).hexdigest() == digest


def test_persist_fails_closed_on_duplicate_execution_id(tmp_path: Path) -> None:
    records = _records(tmp_path)
    kwargs = {
        "root": tmp_path / "evidence",
        "execution_id": "study012b-b1-r001-s17",
        "records": records,
        "source_commit": SOURCE_COMMIT,
    }
    persist_b1_evidence(**kwargs)
    with pytest.raises(FileExistsError):
        persist_b1_evidence(**kwargs)


def test_persist_rejects_confirmatory_fallback_or_unpaired_records(tmp_path: Path) -> None:
    records = _records(tmp_path)

    contaminated = [dict(record) for record in records]
    contaminated[0]["confirmatory_eligible"] = True
    with pytest.raises(ValueError, match="confirmatory"):
        persist_b1_evidence(
            root=tmp_path / "confirmatory",
            execution_id="study012b-b1-r001-s17",
            records=contaminated,
            source_commit=SOURCE_COMMIT,
        )

    fallback = [dict(record) for record in records]
    fallback[0]["fallback_used"] = True
    with pytest.raises(ValueError, match="fallback"):
        persist_b1_evidence(
            root=tmp_path / "fallback",
            execution_id="study012b-b1-r001-s17",
            records=fallback,
            source_commit=SOURCE_COMMIT,
        )

    unpaired = records[:-1]
    with pytest.raises(ValueError, match="pair"):
        persist_b1_evidence(
            root=tmp_path / "unpaired",
            execution_id="study012b-b1-r001-s17",
            records=unpaired,
            source_commit=SOURCE_COMMIT,
        )


def test_persist_rejects_invalid_source_commit_before_writing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_commit"):
        persist_b1_evidence(
            root=tmp_path / "evidence",
            execution_id="study012b-b1-r001-s17",
            records=_records(tmp_path),
            source_commit="short",
        )
    assert not (tmp_path / "evidence" / "study012b-b1-r001-s17").exists()
