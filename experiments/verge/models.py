from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
from typing import Any


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_canonical(v) for v in value]
    return value


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class PolicyGenome:
    routing_policy: tuple[str, ...]
    parallelism: int
    retry_ceiling: int
    confidence_threshold: float
    verification_depth: int
    operator_weights: tuple[tuple[str, float], ...]

    def payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def identity(self) -> str:
        return stable_hash(self.payload())


@dataclass(frozen=True)
class MutationReceipt:
    parent_ids: tuple[str, ...]
    operator_id: str
    seed: int
    changed_fields: tuple[str, ...]
    child_id: str


    def payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def identity(self) -> str:
        return stable_hash(self.payload())


@dataclass(frozen=True)
class EvaluationReceipt:
    candidate_id: str
    benchmark_case: str
    seed: int
    environment: str
    mission_complete: bool
    verifier_pass: bool
    evidence_admitted: bool
    unauthorized_actions: int
    evidence_integrity_failures: int
    cost: float
    latency: float
    human_interventions: int
    recovery_success: bool


    def payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def identity(self) -> str:
        return stable_hash(self.payload())
