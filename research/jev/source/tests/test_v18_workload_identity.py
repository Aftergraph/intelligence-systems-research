from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jev_engineering.workload_identity import Ed25519WorkloadIssuer, WorkloadIdentityVerifier


def test_ed25519_workload_assertion_round_trip_and_tamper_detection() -> None:
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    issuer = Ed25519WorkloadIssuer.generate(key_id="wid-k1", principal="worker:a")
    assertion = issuer.issue(
        audience="aftergraph-trust-gateway", execution_context_id="exec_abc",
        ttl=timedelta(minutes=5), now=now,
    )
    verifier = WorkloadIdentityVerifier({issuer.key_id: issuer.public_key_bytes()})
    identity = verifier.verify(assertion, audience="aftergraph-trust-gateway", now=now + timedelta(seconds=1))
    assert identity.principal == "worker:a"
    assert identity.execution_context_id == "exec_abc"
    with pytest.raises(RuntimeError, match="audience"):
        verifier.verify(assertion, audience="other", now=now)
    tampered = assertion.to_dict()
    tampered["principal"] = "worker:evil"
    with pytest.raises(RuntimeError, match="signature"):
        verifier.verify(type(assertion).from_dict(tampered), audience="aftergraph-trust-gateway", now=now)


def test_expired_workload_assertion_fails_closed() -> None:
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    issuer = Ed25519WorkloadIssuer.generate(key_id="wid-k2", principal="worker:a")
    assertion = issuer.issue(audience="tg", execution_context_id="exec_x", ttl=timedelta(seconds=1), now=now)
    verifier = WorkloadIdentityVerifier({issuer.key_id: issuer.public_key_bytes()})
    with pytest.raises(RuntimeError, match="expired"):
        verifier.verify(assertion, audience="tg", now=now + timedelta(seconds=2))
