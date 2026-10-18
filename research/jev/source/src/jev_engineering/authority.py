from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _canonical_hash(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(slots=True)
class AuthorityGrant:
    grant_id: str
    principal: str
    scopes: frozenset[str]
    budget_usd: float
    spent_usd: float
    expires_at: datetime
    delegation_depth_remaining: int
    authority_ref: str
    parent_grant_id: str | None
    chain_hash: str
    revoked: bool = False


class AuthorityLedger:
    """Deterministic purpose-bound authority attenuation ledger.

    Budget delegated to a child is conservatively reserved from the parent and is
    not automatically reclaimed on revocation. This prevents a revoke/redelegate
    cycle from silently increasing total delegated budget.
    """

    def __init__(self) -> None:
        self._grants: dict[str, AuthorityGrant] = {}
        self._children: dict[str, list[str]] = {}

    def issue_root(
        self,
        *,
        authority_ref: str,
        principal: str,
        scopes: set[str] | frozenset[str],
        budget_usd: float,
        expires_at: datetime,
        delegation_depth: int,
    ) -> AuthorityGrant:
        _require_aware(expires_at, "expires_at")
        if not authority_ref.strip() or not principal.strip():
            raise ValueError("authority_ref and principal must be non-empty")
        if not scopes or any(not str(scope).strip() for scope in scopes):
            raise ValueError("scopes must be non-empty")
        if budget_usd < 0:
            raise ValueError("budget_usd must be non-negative")
        if delegation_depth < 0:
            raise ValueError("delegation_depth must be non-negative")
        grant_id = "auth_" + uuid.uuid4().hex[:24]
        normalized = frozenset(str(scope) for scope in scopes)
        chain_hash = _canonical_hash({
            "grant_id": grant_id,
            "authority_ref": authority_ref,
            "principal": principal,
            "scopes": sorted(normalized),
            "budget_usd": budget_usd,
            "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
            "delegation_depth": delegation_depth,
        })
        grant = AuthorityGrant(
            grant_id=grant_id,
            principal=principal,
            scopes=normalized,
            budget_usd=float(budget_usd),
            spent_usd=0.0,
            expires_at=expires_at,
            delegation_depth_remaining=delegation_depth,
            authority_ref=authority_ref,
            parent_grant_id=None,
            chain_hash=chain_hash,
        )
        self._grants[grant_id] = grant
        self._children[grant_id] = []
        return grant

    def get(self, grant_id: str) -> AuthorityGrant:
        try:
            return self._grants[grant_id]
        except KeyError as exc:
            raise KeyError(f"unknown authority grant {grant_id}") from exc

    def children(self, grant_id: str) -> tuple[AuthorityGrant, ...]:
        self.get(grant_id)
        return tuple(self._grants[c] for c in self._children.get(grant_id, []))

    def available_budget(self, grant_id: str) -> float:
        grant = self.get(grant_id)
        delegated = sum(self._grants[c].budget_usd for c in self._children.get(grant_id, []))
        return max(0.0, grant.budget_usd - grant.spent_usd - delegated)

    def is_active(self, grant_id: str, *, now: datetime) -> bool:
        _require_aware(now, "now")
        grant = self.get(grant_id)
        if grant.revoked or now >= grant.expires_at:
            return False
        if grant.parent_grant_id is not None:
            return self.is_active(grant.parent_grant_id, now=now)
        return True

    def authorize(self, grant_id: str, *, scope: str, amount_usd: float, now: datetime) -> AuthorityGrant:
        if amount_usd < 0:
            raise ValueError("amount_usd must be non-negative")
        grant = self.get(grant_id)
        if not self.is_active(grant_id, now=now):
            raise RuntimeError("authority grant is inactive")
        if scope not in grant.scopes:
            raise RuntimeError(f"scope {scope!r} is not authorized")
        if amount_usd > self.available_budget(grant_id) + 1e-12:
            raise RuntimeError("authority budget exceeded")
        return grant

    def consume(self, grant_id: str, amount_usd: float, *, scope: str, now: datetime) -> None:
        grant = self.authorize(grant_id, scope=scope, amount_usd=amount_usd, now=now)
        grant.spent_usd += amount_usd

    def delegate(
        self,
        parent_grant_id: str,
        *,
        principal: str,
        scopes: set[str] | frozenset[str],
        budget_usd: float,
        expires_at: datetime,
        now: datetime,
    ) -> AuthorityGrant:
        _require_aware(expires_at, "expires_at")
        _require_aware(now, "now")
        parent = self.get(parent_grant_id)
        if not self.is_active(parent_grant_id, now=now):
            raise RuntimeError("parent authority grant is inactive")
        if parent.delegation_depth_remaining <= 0:
            raise RuntimeError("delegation depth exhausted")
        if not principal.strip():
            raise ValueError("principal must be non-empty")
        normalized = frozenset(str(scope) for scope in scopes)
        if not normalized:
            raise ValueError("scopes must be non-empty")
        if not normalized.issubset(parent.scopes):
            raise ValueError("scope expansion is forbidden")
        if budget_usd < 0 or budget_usd > self.available_budget(parent_grant_id) + 1e-12:
            raise ValueError("delegated budget exceeds parent available budget")
        if expires_at > parent.expires_at:
            raise ValueError("child expiry may not exceed parent expiry")
        if expires_at <= now:
            raise ValueError("child expiry must be in the future")
        grant_id = "auth_" + uuid.uuid4().hex[:24]
        chain_hash = _canonical_hash({
            "grant_id": grant_id,
            "parent_grant_id": parent.grant_id,
            "parent_chain_hash": parent.chain_hash,
            "principal": principal,
            "scopes": sorted(normalized),
            "budget_usd": budget_usd,
            "expires_at": expires_at.astimezone(timezone.utc).isoformat(),
            "delegation_depth_remaining": parent.delegation_depth_remaining - 1,
        })
        child = AuthorityGrant(
            grant_id=grant_id,
            principal=principal,
            scopes=normalized,
            budget_usd=float(budget_usd),
            spent_usd=0.0,
            expires_at=expires_at,
            delegation_depth_remaining=parent.delegation_depth_remaining - 1,
            authority_ref=parent.authority_ref,
            parent_grant_id=parent.grant_id,
            chain_hash=chain_hash,
        )
        self._grants[grant_id] = child
        self._children.setdefault(parent.grant_id, []).append(grant_id)
        self._children[grant_id] = []
        return child

    def revoke(self, grant_id: str) -> None:
        self.get(grant_id).revoked = True
        for child_id in self._children.get(grant_id, []):
            self.revoke(child_id)
