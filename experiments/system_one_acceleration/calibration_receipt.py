"""Durable calibration receipts for JAR-EXP-0014.

Receipts bind the frozen labeled corpus and calibration protocol to measured
provider results. They intentionally contain no raw calibration state and do
not mutate or grant execution authority.
"""

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from .calibration_runner import CalibrationRunResult
from .corpus import CalibrationCase


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def calibration_corpus_sha256(cases: Sequence[CalibrationCase]) -> str:
    projection = [
        {
            "case_id": case.case_id,
            "decision_type": case.decision_type,
            "expected": case.expected,
            "critical": case.critical,
        }
        for case in cases
    ]
    return canonical_sha256(projection)


def build_calibration_receipt(
    *,
    receipt_id: str,
    result: CalibrationRunResult,
    cases: Sequence[CalibrationCase],
    protocol_document: Mapping[str, Any],
    source_commit: str,
    generated_at: str,
) -> dict[str, Any]:
    if not receipt_id or not source_commit or not generated_at:
        raise ValueError("receipt_id, source_commit and generated_at are required")

    case_ids = tuple(case.case_id for case in cases)
    observation_ids = tuple(row.case_id for row in result.observations)
    if case_ids != observation_ids:
        raise ValueError("calibration observations do not bind exactly to frozen corpus")

    threshold = result.threshold
    critical_cases = sum(case.critical for case in cases)

    return {
        "schema_version": "aftergraph.system-one-calibration/0.1",
        "experiment_id": "JAR-EXP-0014",
        "receipt_id": receipt_id,
        "requested_model": result.requested_model,
        "returned_model": result.returned_model,
        "corpus_sha256": calibration_corpus_sha256(cases),
        "protocol_sha256": canonical_sha256(dict(protocol_document)),
        "result": {
            "threshold": threshold.threshold,
            "accepted": threshold.accepted,
            "total": threshold.total,
            "coverage": threshold.coverage,
            "errors": threshold.errors,
            "error_rate": threshold.error_rate,
            "wilson_upper": threshold.wilson_upper,
            "critical_cases": critical_cases,
            "critical_errors": threshold.critical_errors,
            "feasible": threshold.feasible,
        },
        "usage": {
            "provider_calls": result.provider_calls,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        },
        "provenance": {
            "source_commit": source_commit,
            "generated_at": generated_at,
        },
    }
