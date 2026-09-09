"""Append-only evidence adapter for STUDY-012B B1 harness validation.

This module deliberately reuses the repository's existing atomic, append-only,
hash-attested run-evidence writer instead of inventing another evidence store.
It binds the exact B1 paired records and source commit to one completed-run
artifact while preserving the non-confirmatory scope of STUDY-012B B1.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from experiments.runtime_acceleration.evidence import write_run_evidence

B1_EVIDENCE_VERSION = "study012b-b1-evidence-v1"
_SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_EXPECTED_CONDITIONS = {"I0", "I3"}


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _record_digest(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(record)).hexdigest()


def _validate_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise ValueError("B1 evidence requires non-empty paired records")

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("study_id") != "STUDY-012B":
            raise ValueError("B1 evidence record has wrong study_id")
        if record.get("evidence_scope") != "HARNESS_VALIDATION_ONLY":
            raise ValueError("B1 evidence must remain HARNESS_VALIDATION_ONLY")
        if record.get("confirmatory_eligible") is not False:
            raise ValueError("confirmatory B1 evidence is forbidden")
        if record.get("fallback_used") is not False:
            raise ValueError("fallback-contaminated B1 evidence is forbidden")
        pair_id = record.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("B1 evidence record is missing pair_id")
        grouped[pair_id].append(record)

    for pair_id, pair_records in grouped.items():
        conditions = [record.get("condition") for record in pair_records]
        if len(pair_records) != 2 or set(conditions) != _EXPECTED_CONDITIONS:
            raise ValueError(f"pair {pair_id} must contain exactly I0 and I3")
        if len({record.get("actor_intent_sha256") for record in pair_records}) != 1:
            raise ValueError(f"pair {pair_id} actor intent drifted")
        if len({record.get("fixture_initial_sha256") for record in pair_records}) != 1:
            raise ValueError(f"pair {pair_id} initial fixture state drifted")


def persist_b1_evidence(
    *,
    root: Path | str,
    execution_id: str,
    records: Sequence[Mapping[str, Any]],
    source_commit: str,
) -> Path:
    """Persist one immutable-by-creation B1 validation evidence directory.

    Reusing ``write_run_evidence`` means duplicate execution IDs fail closed and
    every completed artifact is covered by ``artifacts.sha256``. The adapter
    adds STUDY-012B-specific pairing and scope checks before any evidence is
    written.
    """
    if not isinstance(source_commit, str) or not _SOURCE_COMMIT_RE.fullmatch(source_commit):
        raise ValueError("source_commit must be a full lowercase 40-character Git SHA")

    materialized = [dict(record) for record in records]
    _validate_records(materialized)

    record_sha256 = [_record_digest(record) for record in materialized]
    pair_ids = sorted({str(record["pair_id"]) for record in materialized})

    metadata = {
        "study_id": "STUDY-012B",
        "experiment_id": "ICT-EXP-0001-B",
        "execution_id": execution_id,
        "evidence_version": B1_EVIDENCE_VERSION,
        "evidence_scope": "HARNESS_VALIDATION_ONLY",
        "confirmatory_eligible": False,
        "source_commit": source_commit,
        "record_count": len(materialized),
        "pair_ids": pair_ids,
        "record_sha256": record_sha256,
        "records": materialized,
    }
    integrity = {
        "record_count": len(materialized),
        "pair_count": len(pair_ids),
        "conditions_per_pair": 2,
        "efficacy_metrics_emitted": False,
    }
    verifier = {
        "scope": "HARNESS_VALIDATION_ONLY",
        "confirmatory_eligible": False,
        "pairing_integrity": "PASS",
        "record_binding": "SHA256_CANONICAL_JSON",
        "result_claim": None,
    }

    return write_run_evidence(
        Path(root),
        execution_id,
        {
            "metadata": metadata,
            "metrics": integrity,
            "verifier": verifier,
            "stdout": "",
            "stderr": "",
        },
    )
