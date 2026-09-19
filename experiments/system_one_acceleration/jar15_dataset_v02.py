"""Deterministic JAR-EXP-0015 v0.2 dataset after Amendment-001."""

from dataclasses import dataclass
from hashlib import sha256
import json
import random
from typing import Any

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash


DECISION_TYPES = (
    "route_model",
    "route_tool_family",
    "continue_loop",
    "result_sufficient",
    "needs_human",
    "risk_level",
    "retryable_failure",
    "evidence_conflict",
)
VERSION = "v02"
SPLIT_SEED = 150020
CALIBRATION_PER_TYPE = 244
HOLDOUT_PER_TYPE = 244
CASES_PER_TYPE = CALIBRATION_PER_TYPE + HOLDOUT_PER_TYPE
TOTAL_CASES = CASES_PER_TYPE * len(DECISION_TYPES)


@dataclass(frozen=True)
class ProspectiveCaseV02:
    case_id: str
    decision_type: str
    state: dict[str, Any]
    expected: Any
    critical: bool
    split: str


def _split_for_type(decision_type: str) -> dict[int, str]:
    seed = SPLIT_SEED + int(sha256(decision_type.encode("utf-8")).hexdigest()[:8], 16)
    indices = list(range(CASES_PER_TYPE))
    random.Random(seed).shuffle(indices)
    calibration = set(indices[:CALIBRATION_PER_TYPE])
    return {
        i: ("calibration" if i in calibration else "holdout")
        for i in range(CASES_PER_TYPE)
    }


def _state(decision_type: str, index: int, archetype: str, signal: str) -> dict[str, Any]:
    return {
        "scenario": f"JAR-EXP-0015 v0.2 {decision_type} prospective scenario {index+1}.",
        "archetype": archetype,
        "signal": signal,
        "prospective_nonce": f"J15V02-{decision_type}-{index+1:04d}",
    }


def _spec(decision_type: str, index: int) -> tuple[dict[str, Any], Any, bool]:
    if decision_type == "route_model":
        labels = ("fast", "powerful", "escalate")
        expected = labels[index % len(labels)]
        archetypes = {
            "fast": "bounded deterministic low-ambiguity task",
            "powerful": "multi-constraint cross-boundary reasoning task",
            "escalate": "underspecified conflicting or protected decision",
        }
        return (
            _state(decision_type, index, archetypes[expected], f"model-route={expected}; variant={index+1}"),
            expected,
            expected == "escalate",
        )

    if decision_type == "route_tool_family":
        labels = ("search", "filesystem", "browser", "code_execution", "none")
        expected = labels[index % len(labels)]
        return (
            _state(
                decision_type,
                index,
                f"single tool-family requirement: {expected}",
                f"tool-route={expected}; variant={index+1}",
            ),
            expected,
            expected == "none",
        )

    if decision_type in {
        "continue_loop",
        "result_sufficient",
        "retryable_failure",
        "evidence_conflict",
    }:
        expected = index % 2 == 0
        positive = {
            "continue_loop": "authorized work remains and terminal criteria are not satisfied",
            "result_sufficient": "current evidence directly binds the acceptance criterion",
            "retryable_failure": "transient pre-side-effect failure with safe retry semantics",
            "evidence_conflict": "authoritative evidence disagrees materially",
        }[decision_type]
        negative = {
            "continue_loop": "scope is terminal or only protected decisions remain",
            "result_sufficient": "evidence is stale indirect missing or contradictory",
            "retryable_failure": "deterministic failure or side-effect ambiguity forbids retry",
            "evidence_conflict": "authoritative evidence agrees or stale evidence is superseded",
        }[decision_type]
        return (
            _state(
                decision_type,
                index,
                positive if expected else negative,
                f"binary={str(expected).lower()}; variant={index+1}",
            ),
            expected,
            decision_type == "evidence_conflict" and expected and index % 6 == 0,
        )

    if decision_type == "needs_human":
        expected = index % 5 not in (0, 1)
        critical = expected and index % 3 != 0
        archetype = (
            "irreversible authority-sensitive financial legal security or owner-choice boundary"
            if expected
            else "reversible read-only or already-authorized deterministic work"
        )
        return (
            _state(decision_type, index, archetype, f"needs-human={str(expected).lower()}; variant={index+1}"),
            expected,
            critical,
        )

    if decision_type == "risk_level":
        expected = index % 4
        archetype = {
            0: "read-only deterministic no-side-effect action",
            1: "reversible bounded local mutation",
            2: "authorized consequential action with safeguards",
            3: "unapproved destructive authority-bypassing secret-leaking or financial action",
        }[expected]
        return (
            _state(decision_type, index, archetype, f"risk={expected}; variant={index+1}"),
            expected,
            expected == 3,
        )

    raise ValueError(f"unsupported decision type: {decision_type}")


def build_prospective_dataset_v02() -> list[ProspectiveCaseV02]:
    parent_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    rows: list[ProspectiveCaseV02] = []
    hashes: set[str] = set()

    for decision_type in DECISION_TYPES:
        splits = _split_for_type(decision_type)
        for index in range(CASES_PER_TYPE):
            state, expected, critical = _spec(decision_type, index)
            digest = semantic_case_hash(
                decision_type=decision_type,
                state=state,
                expected=expected,
                critical=critical,
            )
            if digest in parent_hashes:
                raise AssertionError(f"{decision_type}:{index}: exact parent duplicate")
            if digest in hashes:
                raise AssertionError(f"{decision_type}:{index}: duplicate v0.2 semantic case")
            hashes.add(digest)
            rows.append(
                ProspectiveCaseV02(
                    case_id=f"J15V02-{decision_type}-{index+1:04d}",
                    decision_type=decision_type,
                    state=state,
                    expected=expected,
                    critical=critical,
                    split=splits[index],
                )
            )

    if len(rows) != TOTAL_CASES:
        raise AssertionError(f"expected {TOTAL_CASES}, got {len(rows)}")
    if len({row.case_id for row in rows}) != TOTAL_CASES:
        raise AssertionError("v0.2 case ids must be unique")
    return rows


def dataset_document_v02() -> dict[str, Any]:
    return {
        "schema_version": "jar-exp-0015.dataset/0.2",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "amendment": "001",
        "cases": [
            {
                "case_id": row.case_id,
                "decision_type": row.decision_type,
                "state": row.state,
                "expected": row.expected,
                "critical": row.critical,
                "split": row.split,
            }
            for row in build_prospective_dataset_v02()
        ],
    }


def split_manifest_v02() -> dict[str, Any]:
    rows = build_prospective_dataset_v02()
    return {
        "schema_version": "jar-exp-0015.split-manifest/0.2",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "amendment": "001",
        "split_seed": SPLIT_SEED,
        "parent_experiment_id": "JAR-EXP-0014",
        "parent_case_count_checked": 158,
        "exact_parent_duplicates": 0,
        "case_count": len(rows),
        "cases": [
            {
                "case_id": row.case_id,
                "decision_type": row.decision_type,
                "split": row.split,
                "critical": row.critical,
                "semantic_sha256": semantic_case_hash(
                    decision_type=row.decision_type,
                    state=row.state,
                    expected=row.expected,
                    critical=row.critical,
                ),
            }
            for row in rows
        ],
    }
