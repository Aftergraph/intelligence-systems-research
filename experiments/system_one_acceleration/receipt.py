"""Deterministic receipt construction for JAR-EXP-0014.

Only hashes of state/question contracts are persisted. Raw state is deliberately
excluded so research evidence does not become a second memory or secret store.
"""

from hashlib import sha256
import json
from typing import Any, Mapping


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_decision_receipt(
    *,
    receipt_id: str,
    mission_id: str,
    decision_type: str,
    state: Any,
    question_contract: Any,
    requested_model: str,
    returned_model: str,
    answer: Mapping[str, Any],
    routing: Mapping[str, Any],
    source_commit: str,
    generated_at: str,
    latency_ms: float | None = None,
    cost_usd: float | None = None,
) -> dict[str, Any]:
    if not receipt_id or not mission_id:
        raise ValueError("receipt_id and mission_id are required")
    if not requested_model or not returned_model:
        raise ValueError("requested_model and returned_model are required")
    if routing.get("authority_bypassed") is not False:
        raise ValueError("System One receipt cannot bypass authority")

    return {
        "schema_version": "aftergraph.system-one-decision/0.1",
        "receipt_id": receipt_id,
        "mission_id": mission_id,
        "decision_type": decision_type,
        "state_sha256": canonical_sha256(state),
        "question_contract_sha256": canonical_sha256(question_contract),
        "model": {
            "provider": "typesafe",
            "requested_model": requested_model,
            "returned_model": returned_model,
        },
        "answer": dict(answer),
        "routing": dict(routing),
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "provenance": {
            "source_commit": source_commit,
            "generated_at": generated_at,
        },
    }
