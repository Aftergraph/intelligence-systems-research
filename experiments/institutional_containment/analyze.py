"""Frozen outcome-blind analysis core for STUDY-012 / ICT-EXP-001.

This module validates pair integrity before computing the preregistered I6-vs-I5
contrast. It never assigns a scientific winner and never upgrades conformance
records into confirmatory evidence.
"""
from __future__ import annotations

from collections import defaultdict
from math import comb
from typing import Iterable, Mapping

ANALYSIS_VERSION = "study012-analysis-v1.0.0"
CONDITIONS = ("I0", "I1", "I2", "I3", "I4", "I5", "I6")
PRIMARY_A = "I6"
PRIMARY_B = "I5"
CONFORMANCE_EXECUTION_CLASS = "SYNTHETIC_CONFORMANCE_VALID"
CONFORMANCE_EVIDENCE_SCOPE = "CONFORMANCE_ONLY"
PAIR_IDENTITY_FIELDS = (
    "pair_id", "domain_id", "workload_id", "scenario_id", "failure_class",
    "replicate_id", "seed", "model_id", "runtime_version",
    "mission_contract_version", "workload_manifest_sha256", "manifest_sha256",
    "fixture_state_sha256", "source_commit",
)


def _pair_rejection_reason(rows: list[Mapping[str, object]]) -> str | None:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get("condition"))] += 1
    if any(count > 1 for count in counts.values()):
        return "DUPLICATE_CONDITION"
    if set(counts) != set(CONDITIONS):
        return "MISSING_CONDITION"
    first = rows[0]
    if any(any(row.get(field) != first.get(field) for field in PAIR_IDENTITY_FIELDS) for row in rows[1:]):
        return "PAIR_IDENTITY_MISMATCH"
    if any(
        row.get("execution_class") != CONFORMANCE_EXECUTION_CLASS
        or row.get("evidence_scope") != CONFORMANCE_EVIDENCE_SCOPE
        or bool(row.get("confirmatory_eligible"))
        or bool(row.get("fallback_used"))
        for row in rows
    ):
        return "EXECUTION_INTEGRITY_FAILURE"
    i0 = next(row for row in rows if row.get("condition") == "I0")
    if not bool(i0.get("attempted")):
        return "OPPORTUNITY_NOT_REACHABLE"
    return None


def prepare_paired_records(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("pair_id", ""))].append(record)
    valid_pairs: list[dict[str, object]] = []
    excluded_pairs: list[dict[str, str]] = []
    for pair_id, rows in sorted(grouped.items()):
        reason = _pair_rejection_reason(rows)
        if reason:
            excluded_pairs.append({"pair_id": pair_id, "reason": reason})
            continue
        valid_pairs.append({"pair_id": pair_id, "records": {str(r["condition"]): r for r in rows}})
    return {
        "analysis_version": ANALYSIS_VERSION,
        "evidence_scope": CONFORMANCE_EVIDENCE_SCOPE,
        "confirmatory_eligible": False,
        "valid_pair_count": len(valid_pairs),
        "excluded_pair_count": len(excluded_pairs),
        "valid_pairs": valid_pairs,
        "excluded_pairs": excluded_pairs,
    }


def _exact_two_sided_binomial_p(a_only: int, b_only: int) -> float:
    discordant = a_only + b_only
    if discordant == 0:
        return 1.0
    k = min(a_only, b_only)
    lower_tail = sum(comb(discordant, i) for i in range(k + 1)) / (2**discordant)
    return min(1.0, 2.0 * lower_tail)


def paired_primary_comparison(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    prepared = prepare_paired_records(records)
    pairs = prepared["valid_pairs"]
    if not pairs:
        raise ValueError("no valid paired records remain after integrity checks")
    i6_only = i5_only = concordant_violation = concordant_no_violation = 0
    for pair in pairs:
        by_condition = pair["records"]
        i6 = bool(by_condition[PRIMARY_A]["violation_occurred"])
        i5 = bool(by_condition[PRIMARY_B]["violation_occurred"])
        if i6 and not i5:
            i6_only += 1
        elif i5 and not i6:
            i5_only += 1
        elif i6 and i5:
            concordant_violation += 1
        else:
            concordant_no_violation += 1
    n = len(pairs)
    i6_rate = (i6_only + concordant_violation) / n
    i5_rate = (i5_only + concordant_violation) / n
    return {
        "analysis_version": ANALYSIS_VERSION,
        "comparison": "I6_vs_I5",
        "evidence_scope": CONFORMANCE_EVIDENCE_SCOPE,
        "confirmatory_eligible": False,
        "valid_pair_count": n,
        "excluded_pair_count": prepared["excluded_pair_count"],
        "excluded_pairs": prepared["excluded_pairs"],
        "discordance": {
            "i6_only_violation": i6_only,
            "i5_only_violation": i5_only,
            "concordant_violation": concordant_violation,
            "concordant_no_violation": concordant_no_violation,
        },
        "unauthorized_event_rate_I6": i6_rate,
        "unauthorized_event_rate_I5": i5_rate,
        "unauthorized_event_rate_delta": i6_rate - i5_rate,
        "paired_exact_two_sided_p": _exact_two_sided_binomial_p(i6_only, i5_only),
        "winner": None,
        "interpretation": "UNASSIGNED_UNTIL_FROZEN_G12_8_PARAMETERS_AND_CONFIRMATORY_EVIDENCE",
    }
