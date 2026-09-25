"""Executable condition-isolation helpers for STUDY-015."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "study015_condition_manifest.json"


class ConditionIsolationError(ValueError):
    pass


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_mechanisms(condition: str, condition_variant: str | None = None) -> frozenset[str]:
    doc = load_manifest()
    by_id = {row["id"]: set(row["enabled"]) for row in doc["conditions"]}
    if condition == "FULL_MINUS":
        if not condition_variant:
            raise ConditionIsolationError("FULL_MINUS requires condition_variant")
        full = set(by_id["FULL"])
        if condition_variant not in full:
            raise ConditionIsolationError(f"unknown FULL_MINUS mechanism: {condition_variant}")
        full.remove(condition_variant)
        return frozenset(full)
    if condition not in by_id:
        raise ConditionIsolationError(f"unknown condition: {condition}")
    return frozenset(by_id[condition])


def assert_mechanism_isolation(
    *,
    condition: str,
    observed_enabled: set[str] | frozenset[str],
    condition_variant: str | None = None,
) -> None:
    expected = expected_mechanisms(condition, condition_variant)
    observed = frozenset(observed_enabled)
    if observed != expected:
        missing = sorted(expected - observed)
        leaked = sorted(observed - expected)
        raise ConditionIsolationError(
            f"condition {condition} mechanism mismatch; missing={missing}; leaked={leaked}"
        )


def matched_input_signature(record: dict[str, Any]) -> str:
    required = (
        "provider",
        "model",
        "workload_id",
        "replicate_id",
        "budget_hash",
        "acceptance_hash",
        "prompt_hash",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise ConditionIsolationError(f"missing matched-input fields: {missing}")
    payload = {key: record[key] for key in required}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_matched_pair(left: dict[str, Any], right: dict[str, Any]) -> None:
    if matched_input_signature(left) != matched_input_signature(right):
        raise ConditionIsolationError("paired conditions do not have matched inputs")
