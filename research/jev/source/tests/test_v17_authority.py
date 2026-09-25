from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.authority import AuthorityLedger


def _now() -> datetime:
    return datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)


def test_delegation_attenuates_scope_budget_expiry_and_depth() -> None:
    now = _now()
    ledger = AuthorityLedger()
    root = ledger.issue_root(
        authority_ref="human:jonas",
        principal="steward",
        scopes={"mission.execute", "repo.write", "deploy.staging"},
        budget_usd=10.0,
        expires_at=now + timedelta(hours=2),
        delegation_depth=2,
    )
    child = ledger.delegate(
        root.grant_id,
        principal="worker:a",
        scopes={"mission.execute", "repo.write"},
        budget_usd=3.0,
        expires_at=now + timedelta(hours=1),
        now=now,
    )
    assert child.parent_grant_id == root.grant_id
    assert child.scopes == frozenset({"mission.execute", "repo.write"})
    assert child.delegation_depth_remaining == 1
    assert child.chain_hash != root.chain_hash
    assert ledger.available_budget(root.grant_id) == pytest.approx(7.0)

    with pytest.raises(ValueError, match="scope expansion"):
        ledger.delegate(
            root.grant_id,
            principal="worker:evil",
            scopes={"iam.admin"},
            budget_usd=1,
            expires_at=now + timedelta(minutes=10),
            now=now,
        )
    with pytest.raises(ValueError, match="budget"):
        ledger.delegate(
            root.grant_id,
            principal="worker:too-expensive",
            scopes={"mission.execute"},
            budget_usd=8,
            expires_at=now + timedelta(minutes=10),
            now=now,
        )
    with pytest.raises(ValueError, match="expiry"):
        ledger.delegate(
            root.grant_id,
            principal="worker:late",
            scopes={"mission.execute"},
            budget_usd=1,
            expires_at=now + timedelta(hours=3),
            now=now,
        )


def test_revocation_cascades_and_budget_is_conserved() -> None:
    now = _now()
    ledger = AuthorityLedger()
    root = ledger.issue_root(
        authority_ref="human:jonas",
        principal="steward",
        scopes={"mission.execute"},
        budget_usd=4,
        expires_at=now + timedelta(hours=1),
        delegation_depth=2,
    )
    child = ledger.delegate(
        root.grant_id,
        principal="worker:a",
        scopes={"mission.execute"},
        budget_usd=2,
        expires_at=now + timedelta(minutes=30),
        now=now,
    )
    grandchild = ledger.delegate(
        child.grant_id,
        principal="worker:b",
        scopes={"mission.execute"},
        budget_usd=1,
        expires_at=now + timedelta(minutes=20),
        now=now,
    )
    ledger.consume(child.grant_id, 0.75, scope="mission.execute", now=now)
    assert ledger.available_budget(child.grant_id) == pytest.approx(0.25)
    ledger.revoke(child.grant_id)
    assert ledger.is_active(child.grant_id, now=now) is False
    assert ledger.is_active(grandchild.grant_id, now=now) is False
    with pytest.raises(RuntimeError, match="inactive"):
        ledger.authorize(grandchild.grant_id, scope="mission.execute", amount_usd=0, now=now)
