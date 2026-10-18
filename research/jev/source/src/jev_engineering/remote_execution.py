from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from .remote_worker import RemoteExecutionResult, RemoteWorkerClient


def _hash_payload(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class RemoteWorkOrder:
    mission_id: str
    node_id: str
    execution_context_id: str
    lease_id: str
    fencing_token: int
    authority_grant_id: str
    candidate_sha: str
    operation: str = "verify_candidate"

    def __post_init__(self) -> None:
        for name in ("mission_id", "node_id", "execution_context_id", "lease_id", "authority_grant_id", "candidate_sha", "operation"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.fencing_token < 1:
            raise ValueError("fencing_token must be >= 1")
        if self.operation.startswith("shell"):
            raise ValueError("remote work order cannot request shell execution")

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def work_order_sha256(self) -> str:
        return _hash_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class RemoteWorkReceipt:
    worker_id: str
    request_id: str
    work_order_sha256: str
    node_id: str
    lease_id: str
    fencing_token: int
    candidate_sha: str
    verdict: str
    evidence: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.verdict.upper() == "PASS"


class RemoteExecutionCoordinator:
    """Coordinator-side binding between a fenced work order and signed node response."""

    def __init__(self, client: RemoteWorkerClient) -> None:
        self.client = client

    def execute(self, order: RemoteWorkOrder) -> RemoteWorkReceipt:
        result: RemoteExecutionResult = self.client.call(order.operation, order.to_payload())
        if not result.ok:
            raise RuntimeError("remote worker reported execution failure")
        payload = result.payload
        expected = {
            "work_order_sha256": order.work_order_sha256,
            "node_id": order.node_id,
            "lease_id": order.lease_id,
            "fencing_token": order.fencing_token,
            "candidate_sha": order.candidate_sha,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(f"remote receipt binding mismatch for {key}")
        verdict = str(payload.get("verdict", "")).upper()
        if verdict not in {"PASS", "FAIL"}:
            raise RuntimeError("remote receipt verdict must be PASS or FAIL")
        return RemoteWorkReceipt(
            worker_id=result.worker_id,
            request_id=result.request_id,
            work_order_sha256=order.work_order_sha256,
            node_id=order.node_id,
            lease_id=order.lease_id,
            fencing_token=order.fencing_token,
            candidate_sha=order.candidate_sha,
            verdict=verdict,
            evidence=dict(payload.get("evidence") or {}),
        )


def make_verification_handler(*, verifier_name: str):
    """Return a bounded worker handler for reference transport tests/demos.

    The handler does not execute arbitrary code. It verifies the exact work-order
    binding and returns a caller-supplied deterministic candidate verdict signal.
    """
    if not verifier_name.strip():
        raise ValueError("verifier_name must be non-empty")

    def handler(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        if operation != "verify_candidate":
            raise RuntimeError("unsupported remote operation")
        order = RemoteWorkOrder(**{k: payload[k] for k in (
            "mission_id", "node_id", "execution_context_id", "lease_id",
            "fencing_token", "authority_grant_id", "candidate_sha", "operation",
        )})
        # Reference worker only accepts an explicit deterministic test signal.
        expected = str(payload.get("expected_verdict", payload.get("verdict", "PASS"))).upper()
        verdict = expected if expected in {"PASS", "FAIL"} else "FAIL"
        return {
            "work_order_sha256": order.work_order_sha256,
            "node_id": order.node_id,
            "lease_id": order.lease_id,
            "fencing_token": order.fencing_token,
            "candidate_sha": order.candidate_sha,
            "verdict": verdict,
            "evidence": {"verifier": verifier_name, "mode": "reference-bounded"},
        }

    return handler


def make_journaled_verification_handler(*, verifier_name: str):
    """Bounded reference verifier that returns a hash-chained execution journal."""
    from .execution_journal import ExecutionJournal

    base = make_verification_handler(verifier_name=verifier_name)

    def handler(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        journal = ExecutionJournal()
        journal.append("work.accepted", {
            "node_id": payload.get("node_id"),
            "candidate_sha": payload.get("candidate_sha"),
        })
        result = base(operation, payload)
        journal.append("verification.completed", {
            "verdict": result["verdict"],
            "verifier": verifier_name,
        })
        evidence = dict(result.get("evidence") or {})
        evidence["execution_events"] = journal.to_list()
        evidence["execution_journal_head_sha256"] = journal.head_sha256
        result["evidence"] = evidence
        return result

    return handler


def validate_execution_journal(receipt: RemoteWorkReceipt) -> str:
    """Validate optional execution journal carried by a remote work receipt."""
    from .execution_journal import ExecutionJournal

    rows = receipt.evidence.get("execution_events")
    expected_head = receipt.evidence.get("execution_journal_head_sha256")
    if rows is None and expected_head is None:
        return ""
    if not isinstance(rows, list) or not isinstance(expected_head, str) or not expected_head:
        raise RuntimeError("remote execution journal incomplete")
    journal = ExecutionJournal.from_list(rows)
    if journal.head_sha256 != expected_head:
        raise RuntimeError("remote execution journal head mismatch")
    return journal.head_sha256
