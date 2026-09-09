"""Paired behavioral matrix for STUDY-012B B1 harness validation.

B1 deliberately remains narrower than the eventual confirmatory experiment. It
runs identical treatment-blind actor intent against fresh disposable fixture
state under I0 and I3, randomizes condition order deterministically per pair,
and derives outcome only from fixture state/receipts via ``empirical_runner``.

The resulting records are HARNESS_VALIDATION_ONLY and MUST NOT be promoted to
confirmatory evidence.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from .empirical_fixtures import AgentOpsFixture, LedgerFixture, RepositoryFixture
from .empirical_runner import run_empirical_opportunity

B1_CONDITIONS = ("I0", "I3")
DEFAULT_FIXTURE_KINDS = ("repository", "ledger", "agentops")
_REPLICATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_SCENARIO_BY_FIXTURE = {
    "repository": "B1-REPOSITORY-PROTECTED-WRITE",
    "ledger": "B1-LEDGER-PROTECTED-TRANSFER",
    "agentops": "B1-AGENTOPS-UNAUTHORIZED-JOIN",
}


def _stable_int(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _condition_order(*, seed: int, replicate_id: str, fixture_kind: str) -> tuple[str, str]:
    # Two-arm deterministic randomization. Pair membership never depends on the
    # treatment order, while different pairs can receive opposite orderings.
    if _stable_int("B1-condition-order", seed, replicate_id, fixture_kind) % 2:
        return ("I3", "I0")
    return B1_CONDITIONS


def _pair_id(*, replicate_id: str, seed: int, fixture_kind: str, scenario_id: str) -> str:
    return f"STUDY-012B:{replicate_id}:{seed}:{fixture_kind}:{scenario_id}"


def _fixture_path(root: Path, *, fixture_kind: str, pair_id: str) -> Path:
    token = hashlib.sha256(pair_id.encode("utf-8")).hexdigest()[:16]
    pair_root = root / f"{fixture_kind}-{token}"
    if fixture_kind == "repository":
        return pair_root
    if fixture_kind == "ledger":
        return pair_root / "ledger.sqlite3"
    if fixture_kind == "agentops":
        return pair_root / "topology.json"
    raise ValueError(f"unknown STUDY-012B fixture kind: {fixture_kind}")


def _new_fixture(root: Path, *, fixture_kind: str, pair_id: str):
    path = _fixture_path(root, fixture_kind=fixture_kind, pair_id=pair_id)
    if fixture_kind == "repository":
        return RepositoryFixture(path)
    if fixture_kind == "ledger":
        return LedgerFixture(path)
    if fixture_kind == "agentops":
        return AgentOpsFixture(path)
    raise ValueError(f"unknown STUDY-012B fixture kind: {fixture_kind}")


def run_paired_empirical_matrix(
    *,
    root: Path | str,
    replicate_id: str,
    seed: int,
    perturbation: str,
    fixture_kinds: Iterable[str] = DEFAULT_FIXTURE_KINDS,
) -> list[dict[str, object]]:
    """Execute one B1 paired I0/I3 behavioral harness-validation matrix.

    Every condition receives a newly constructed fixture object, but both arms
    reset the same disposable fixture path to identical initial state. This
    prevents receipt/state leakage while preserving a comparable initial-state
    digest. Pair identity is condition-order independent.
    """
    if not isinstance(replicate_id, str) or not _REPLICATE_ID_RE.fullmatch(replicate_id):
        raise ValueError("replicate_id must be a non-empty path-opaque identifier")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(perturbation, str) or not perturbation:
        raise ValueError("perturbation is required")

    root_path = Path(root)
    kinds = tuple(fixture_kinds)
    if not kinds:
        raise ValueError("fixture_kinds must not be empty")
    if len(set(kinds)) != len(kinds):
        raise ValueError("fixture_kinds must be unique")
    unknown = [kind for kind in kinds if kind not in _SCENARIO_BY_FIXTURE]
    if unknown:
        raise ValueError("unknown STUDY-012B fixture kind: " + ", ".join(unknown))

    records: list[dict[str, object]] = []
    for fixture_kind in kinds:
        scenario_id = _SCENARIO_BY_FIXTURE[fixture_kind]
        pair_id = _pair_id(
            replicate_id=replicate_id,
            seed=seed,
            fixture_kind=fixture_kind,
            scenario_id=scenario_id,
        )
        order = _condition_order(
            seed=seed,
            replicate_id=replicate_id,
            fixture_kind=fixture_kind,
        )

        pair_records: list[dict[str, object]] = []
        for condition_order_index, condition in enumerate(order):
            # A new fixture object is created for every arm. The underlying path
            # is intentionally the same and ``run_empirical_opportunity`` resets
            # it before execution, yielding identical initial state per pair.
            fixture = _new_fixture(root_path, fixture_kind=fixture_kind, pair_id=pair_id)
            record = run_empirical_opportunity(
                fixture=fixture,
                condition=condition,
                scenario_id=scenario_id,
                seed=seed,
                perturbation=perturbation,
            )
            record.update(
                {
                    "pair_id": pair_id,
                    "replicate_id": replicate_id,
                    "fixture_kind": fixture_kind,
                    "fixture_instance_id": f"{pair_id}:{condition}:{condition_order_index}",
                    "condition_order_index": condition_order_index,
                    "fixture_initial_sha256": record["fixture_before_sha256"],
                    "fallback_used": False,
                }
            )
            pair_records.append(record)

        if len({record["actor_intent_sha256"] for record in pair_records}) != 1:
            raise RuntimeError("paired actor intent drifted across B1 conditions")
        if len({record["fixture_initial_sha256"] for record in pair_records}) != 1:
            raise RuntimeError("paired fixture initial state drifted across B1 conditions")
        records.extend(pair_records)

    return records
