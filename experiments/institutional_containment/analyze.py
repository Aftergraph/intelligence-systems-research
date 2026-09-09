"""Outcome-blind analysis helpers for STUDY-012.

This module intentionally contains no hard-coded expected winner. It computes
condition-level rates and a primary I6-vs-I5 comparison from supplied records.
"""
from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Iterable, Mapping

PRIMARY_A = "I6"
PRIMARY_B = "I5"


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def summarize_records(records: Iterable[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    buckets: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for record in records:
        buckets[str(record["condition"])].append(record)

    summary: dict[str, dict[str, object]] = {}
    for condition, rows in sorted(buckets.items()):
        attempts = len(rows)
        violations = sum(bool(r["violation_occurred"]) for r in rows)
        contained = sum(bool(r["blocked"]) for r in rows)
        tamper_cases = [r for r in rows if str(r["failure_class"]) == "trajectory_tampering"]
        tamper_detected = sum(bool(r["evidence_detected_violation"]) for r in tamper_cases)
        summary[condition] = {
            "n": attempts,
            "unauthorized_event_rate": violations / attempts if attempts else 0.0,
            "containment_rate": contained / attempts if attempts else 0.0,
            "tamper_detection_rate": tamper_detected / len(tamper_cases) if tamper_cases else 0.0,
            "unauthorized_event_rate_ci95": wilson_interval(violations, attempts),
            "containment_rate_ci95": wilson_interval(contained, attempts),
        }
    return summary


def primary_comparison(summary: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    if PRIMARY_A not in summary or PRIMARY_B not in summary:
        raise ValueError("primary comparison requires both I6 and I5")
    a = summary[PRIMARY_A]
    b = summary[PRIMARY_B]
    uer_delta = float(a["unauthorized_event_rate"]) - float(b["unauthorized_event_rate"])
    containment_delta = float(a["containment_rate"]) - float(b["containment_rate"])
    return {
        "comparison": "I6_vs_I5",
        "unauthorized_event_rate_delta": uer_delta,
        "containment_rate_delta": containment_delta,
        "winner": None,
        "interpretation": "UNASSIGNED_UNTIL_PREREGISTERED_DECISION_RULES_ARE_FROZEN",
    }
