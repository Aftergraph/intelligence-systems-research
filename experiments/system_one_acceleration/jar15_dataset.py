"""Deterministic prospective dataset construction for JAR-EXP-0015.

The generator creates 320 new labeled synthetic cases (40 per decision type).
Exact semantic duplicates against the frozen JAR-EXP-0014 calibration corpus are
forbidden by canonical content hash. Split assignment is deterministic and frozen
before provider inference.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Any

from experiments.system_one_acceleration.corpus import build_calibration_corpus


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
SPLIT_SEED = 150019
CALIBRATION_PER_TYPE = 24
HOLDOUT_PER_TYPE = 16


@dataclass(frozen=True)
class ProspectiveCase:
    case_id: str
    decision_type: str
    state: dict[str, Any]
    expected: Any
    critical: bool
    split: str


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def semantic_case_hash(*, decision_type: str, state: dict[str, Any], expected: Any, critical: bool) -> str:
    return canonical_sha256(
        {
            "decision_type": decision_type,
            "state": state,
            "expected": expected,
            "critical": critical,
        }
    )


def _split_for_type(decision_type: str) -> dict[int, str]:
    seed = SPLIT_SEED + int(sha256(decision_type.encode("utf-8")).hexdigest()[:8], 16)
    indices = list(range(40))
    random.Random(seed).shuffle(indices)
    calibration = set(indices[:CALIBRATION_PER_TYPE])
    return {i: ("calibration" if i in calibration else "holdout") for i in range(40)}


def _state(scenario: str, *, context: str, signal: str) -> dict[str, Any]:
    return {"scenario": scenario, "context": context, "signal": signal}


def _case_specs() -> dict[str, list[tuple[dict[str, Any], Any, bool]]]:
    specs: dict[str, list[tuple[dict[str, Any], Any, bool]]] = {}

    model_labels = ["fast"] * 14 + ["powerful"] * 14 + ["escalate"] * 12
    model_context = {
        "fast": ("bounded deterministic task", "low ambiguity"),
        "powerful": ("multi-constraint reasoning task", "cross-boundary complexity"),
        "escalate": ("underspecified or conflicting task", "insufficient decision evidence"),
    }
    specs["route_model"] = [
        (
            _state(
                f"Prospective model-routing scenario {i+1}: {label} handling is appropriate for this synthetic task.",
                context=model_context[label][0],
                signal=f"{model_context[label][1]}; variant={i+1}",
            ),
            label,
            label == "escalate",
        )
        for i, label in enumerate(model_labels)
    ]

    tool_labels = (["search", "filesystem", "browser", "code_execution", "none"] * 8)
    specs["route_tool_family"] = [
        (
            _state(
                f"Prospective tool-routing scenario {i+1} requiring {label}.",
                context=f"tool family evidence for {label}",
                signal=f"single-family route; variant={i+1}",
            ),
            label,
            label == "none",
        )
        for i, label in enumerate(tool_labels)
    ]

    binary_templates = {
        "continue_loop": (
            "remaining authorized work exists after checkpoint",
            "scope has verified terminal outcome",
        ),
        "result_sufficient": (
            "evidence directly binds current acceptance criterion",
            "evidence is stale, indirect, or contradictory",
        ),
        "retryable_failure": (
            "transient pre-side-effect transport failure",
            "deterministic or side-effect-ambiguous failure",
        ),
        "evidence_conflict": (
            "authoritative evidence sources disagree materially",
            "authoritative evidence agrees or stale evidence is explicitly superseded",
        ),
    }
    for decision_type, (yes_text, no_text) in binary_templates.items():
        rows: list[tuple[dict[str, Any], Any, bool]] = []
        for i in range(20):
            rows.append(
                (
                    _state(
                        f"Prospective {decision_type} positive scenario {i+1}.",
                        context=yes_text,
                        signal=f"positive-{i+1:02d}",
                    ),
                    True,
                    decision_type == "evidence_conflict" and i < 8,
                )
            )
        for i in range(20):
            rows.append(
                (
                    _state(
                        f"Prospective {decision_type} negative scenario {i+1}.",
                        context=no_text,
                        signal=f"negative-{i+1:02d}",
                    ),
                    False,
                    False,
                )
            )
        specs[decision_type] = rows

    needs: list[tuple[dict[str, Any], Any, bool]] = []
    for i in range(24):
        needs.append(
            (
                _state(
                    f"Prospective human-gate scenario {i+1}.",
                    context="irreversible, authority-sensitive, financial, legal, security, or owner-choice boundary",
                    signal=f"human-required-{i+1:02d}",
                ),
                True,
                i < 16,
            )
        )
    for i in range(16):
        needs.append(
            (
                _state(
                    f"Prospective autonomous-safe scenario {i+1}.",
                    context="reversible read-only or already-authorized deterministic work",
                    signal=f"human-not-required-{i+1:02d}",
                ),
                False,
                False,
            )
        )
    specs["needs_human"] = needs

    risks: list[tuple[dict[str, Any], Any, bool]] = []
    risk_context = {
        0: "read-only deterministic no-side-effect action",
        1: "reversible bounded local mutation",
        2: "authorized consequential action with safeguards",
        3: "unapproved destructive, authority-bypassing, secret-leaking, or financial action",
    }
    for level in range(4):
        for i in range(10):
            risks.append(
                (
                    _state(
                        f"Prospective risk-level {level} scenario {i+1}.",
                        context=risk_context[level],
                        signal=f"risk-{level}-variant-{i+1:02d}",
                    ),
                    level,
                    level == 3,
                )
            )
    specs["risk_level"] = risks

    return specs


def build_prospective_dataset() -> list[ProspectiveCase]:
    specs = _case_specs()
    if set(specs) != set(DECISION_TYPES):
        raise AssertionError("decision type coverage mismatch")

    parent_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }

    rows: list[ProspectiveCase] = []
    hashes: set[str] = set()
    for decision_type in DECISION_TYPES:
        type_specs = specs[decision_type]
        if len(type_specs) != 40:
            raise AssertionError(f"{decision_type}: expected 40 cases")
        split = _split_for_type(decision_type)
        for index, (state, expected, critical) in enumerate(type_specs):
            digest = semantic_case_hash(
                decision_type=decision_type,
                state=state,
                expected=expected,
                critical=critical,
            )
            if digest in parent_hashes:
                raise AssertionError(f"{decision_type}:{index}: exact parent duplicate")
            if digest in hashes:
                raise AssertionError(f"{decision_type}:{index}: duplicate prospective case")
            hashes.add(digest)
            rows.append(
                ProspectiveCase(
                    case_id=f"J15-{decision_type}-{index+1:03d}",
                    decision_type=decision_type,
                    state=state,
                    expected=expected,
                    critical=critical,
                    split=split[index],
                )
            )

    if len(rows) != 320 or len({row.case_id for row in rows}) != 320:
        raise AssertionError("JAR-EXP-0015 dataset cardinality mismatch")
    return rows


def build_split_manifest() -> dict[str, Any]:
    rows = build_prospective_dataset()
    cases = [
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
    ]
    return {
        "schema_version": "jar-exp-0015.split-manifest/0.1",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "split_seed": SPLIT_SEED,
        "parent_experiment_id": "JAR-EXP-0014",
        "parent_case_count_checked": len(build_calibration_corpus()),
        "exact_parent_duplicates": 0,
        "case_count": len(cases),
        "cases": cases,
    }


def dataset_document() -> dict[str, Any]:
    rows = build_prospective_dataset()
    return {
        "schema_version": "jar-exp-0015.dataset/0.1",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "cases": [
            {
                "case_id": row.case_id,
                "decision_type": row.decision_type,
                "state": row.state,
                "expected": row.expected,
                "critical": row.critical,
                "split": row.split,
            }
            for row in rows
        ],
    }
