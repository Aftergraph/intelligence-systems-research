from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """Subject-bound evidence. A claim may be fresh while its verdict is false."""

    claim_id: str
    subject: str
    predicate: str
    verifier: str
    method: str
    verdict: bool
    dependencies: dict[str, str] = field(default_factory=dict)
    parent_claim_ids: tuple[str, ...] = ()
    observed_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("claim_id", self.claim_id),
            ("subject", self.subject),
            ("predicate", self.predicate),
            ("verifier", self.verifier),
            ("method", self.method),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must be non-empty")

    @classmethod
    def mint(
        cls,
        *,
        subject: str,
        predicate: str,
        verifier: str,
        method: str,
        verdict: bool,
        dependencies: dict[str, str] | None = None,
        parent_claim_ids: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "EvidenceClaim":
        payload = {
            "subject": subject,
            "predicate": predicate,
            "verifier": verifier,
            "method": method,
            "verdict": bool(verdict),
            "dependencies": sorted((dependencies or {}).items()),
            "parent_claim_ids": sorted(parent_claim_ids),
            "metadata": metadata or {},
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            claim_id="ev_" + digest[:24],
            subject=subject,
            predicate=predicate,
            verifier=verifier,
            method=method,
            verdict=bool(verdict),
            dependencies=dict(dependencies or {}),
            parent_claim_ids=tuple(parent_claim_ids),
            metadata=dict(metadata or {}),
        )


class ProofGraph:
    """Content-addressed evidence DAG with incremental dependency invalidation."""

    def __init__(self) -> None:
        self._claims: dict[str, EvidenceClaim] = {}
        self._status: dict[str, str] = {}

    def add_claim(self, claim: EvidenceClaim) -> None:
        for parent in claim.parent_claim_ids:
            if parent not in self._claims:
                raise KeyError(f"unknown parent evidence claim {parent!r}")
        incumbent = self._claims.get(claim.claim_id)
        if incumbent is not None and incumbent != claim:
            raise ValueError(f"claim id collision for {claim.claim_id!r}")
        self._claims[claim.claim_id] = claim
        self._status.setdefault(claim.claim_id, "active")

    def claim(self, claim_id: str) -> EvidenceClaim:
        return self._claims[claim_id]

    def claims(self) -> tuple[EvidenceClaim, ...]:
        return tuple(self._claims.values())

    def status(self, claim_id: str) -> str:
        return self._status[claim_id]

    def is_fresh(self, claim_id: str) -> bool:
        if self._status.get(claim_id) != "active":
            return False
        claim = self._claims[claim_id]
        return all(self.is_fresh(parent) for parent in claim.parent_claim_ids)

    def accepts(self, claim_ids: list[str] | tuple[str, ...]) -> bool:
        if not claim_ids:
            return False
        return all(self.is_fresh(claim_id) and self._claims[claim_id].verdict for claim_id in claim_ids)

    def find_reusable(
        self,
        *,
        subject: str,
        predicate: str,
        dependencies: dict[str, str],
        verifier: str | None = None,
        method: str | None = None,
    ) -> list[EvidenceClaim]:
        """Return exact-subject, exact-dependency fresh positive evidence.

        Reuse is deliberately strict: dependency supersets/subsets do not match,
        false/stale/revoked claims are excluded, and optional verifier/method
        constraints must match exactly.
        """
        matches = [
            claim
            for claim_id, claim in self._claims.items()
            if claim.subject == subject
            and claim.predicate == predicate
            and claim.dependencies == dependencies
            and claim.verdict
            and self.is_fresh(claim_id)
            and (verifier is None or claim.verifier == verifier)
            and (method is None or claim.method == method)
        ]
        return sorted(matches, key=lambda claim: (claim.observed_at, claim.claim_id), reverse=True)

    def observe_dependency(self, dependency: str, observed_hash: str) -> set[str]:
        directly_stale = {
            claim_id
            for claim_id, claim in self._claims.items()
            if dependency in claim.dependencies
            and claim.dependencies[dependency] != observed_hash
            and self._status.get(claim_id) == "active"
        }
        return self._propagate_stale(directly_stale)

    def observe_dependencies(self, current: dict[str, str]) -> set[str]:
        stale: set[str] = set()
        for dependency, observed_hash in current.items():
            stale |= self.observe_dependency(dependency, observed_hash)
        return stale

    def revoke(self, claim_id: str) -> set[str]:
        if claim_id not in self._claims:
            raise KeyError(claim_id)
        self._status[claim_id] = "revoked"
        return self._propagate_stale({claim_id})

    def _propagate_stale(self, roots: set[str]) -> set[str]:
        affected = set(roots)
        changed = True
        while changed:
            changed = False
            for claim_id, claim in self._claims.items():
                if claim_id in affected:
                    continue
                if any(parent in affected for parent in claim.parent_claim_ids):
                    affected.add(claim_id)
                    changed = True
        for claim_id in affected:
            if self._status.get(claim_id) != "revoked":
                self._status[claim_id] = "stale"
        return affected

    def telemetry(self) -> dict[str, int]:
        statuses = list(self._status.values())
        return {
            "claims": len(self._claims),
            "active_claims": statuses.count("active"),
            "stale_claims": statuses.count("stale"),
            "revoked_claims": statuses.count("revoked"),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "claims": [
                {
                    **asdict(claim),
                    "parent_claim_ids": list(claim.parent_claim_ids),
                    "status": self._status[claim.claim_id],
                }
                for claim in sorted(self._claims.values(), key=lambda value: value.claim_id)
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProofGraph":
        if int(payload.get("version", 0)) != 1:
            raise ValueError("unsupported proof graph version")
        graph = cls()
        rows = payload.get("claims") or []
        if not isinstance(rows, list):
            raise TypeError("proof graph claims must be a list")
        pending = list(rows)
        while pending:
            progressed = False
            for row in list(pending):
                if not isinstance(row, dict):
                    raise TypeError("proof graph claim must be an object")
                parents = tuple(str(v) for v in row.get("parent_claim_ids") or [])
                if any(parent not in graph._claims for parent in parents):
                    continue
                claim = EvidenceClaim(
                    claim_id=str(row.get("claim_id") or ""),
                    subject=str(row.get("subject") or ""),
                    predicate=str(row.get("predicate") or ""),
                    verifier=str(row.get("verifier") or ""),
                    method=str(row.get("method") or ""),
                    verdict=bool(row.get("verdict")),
                    dependencies={str(k): str(v) for k, v in dict(row.get("dependencies") or {}).items()},
                    parent_claim_ids=parents,
                    observed_at=float(row.get("observed_at", 0.0)),
                    metadata=dict(row.get("metadata") or {}),
                )
                graph.add_claim(claim)
                status = str(row.get("status") or "active")
                if status not in {"active", "stale", "revoked"}:
                    raise ValueError(f"unsupported proof status {status!r}")
                graph._status[claim.claim_id] = status
                pending.remove(row)
                progressed = True
            if not progressed:
                raise ValueError("proof graph contains unknown/cyclic parent claim references")
        return graph

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "ProofGraph":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("proof graph root must be an object")
        return cls.from_dict(payload)


def workspace_tree_hash(root: str | Path) -> str:
    """Hash repository-visible files for exact-subject verification binding."""
    root_path = Path(root).resolve()
    skip = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".jev", ".jev-one"}
    digest = hashlib.sha256()
    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or any(part in skip for part in path.relative_to(root_path).parts):
            continue
        try:
            rel = path.relative_to(root_path).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
        digest.update(b"\0")
    return digest.hexdigest()
