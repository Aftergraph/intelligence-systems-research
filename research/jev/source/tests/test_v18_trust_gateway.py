from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.authority import AuthorityLedger
from jev_engineering.execution_context import WorksExecutionContext
from jev_engineering.trust_gateway import TrustGatewayValidator
from jev_engineering.workload_identity import Ed25519WorkloadIssuer, WorkloadIdentityVerifier


def test_trust_gateway_binds_identity_execution_context_and_authority() -> None:
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    ctx = WorksExecutionContext.create(mission_id="m1", node_id="n1", principal="worker:a")
    issuer = Ed25519WorkloadIssuer.generate(key_id="wid-k1", principal="worker:a")
    assertion = issuer.issue(audience="aftergraph-trust-gateway", execution_context_id=ctx.execution_context_id, ttl=timedelta(minutes=5), now=now)
    ids = WorkloadIdentityVerifier({issuer.key_id: issuer.public_key_bytes()})
    ledger = AuthorityLedger()
    grant = ledger.issue_root(authority_ref="human:jonas", principal="worker:a", scopes={"mission.execute"}, budget_usd=1, expires_at=now+timedelta(hours=1), delegation_depth=0)
    gate = TrustGatewayValidator(identity_verifier=ids, authority=ledger)
    decision = gate.admit(assertion=assertion, context=ctx, grant_id=grant.grant_id, scope="mission.execute", amount_usd=0, now=now)
    assert decision.allowed is True
    bad_ctx = WorksExecutionContext.create(mission_id="m1", node_id="n1", principal="worker:b", execution_context_id=ctx.execution_context_id, trace_id=ctx.trace_id)
    with pytest.raises(RuntimeError, match="principal"):
        gate.admit(assertion=assertion, context=bad_ctx, grant_id=grant.grant_id, scope="mission.execute", amount_usd=0, now=now)
