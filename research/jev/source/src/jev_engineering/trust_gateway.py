from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .authority import AuthorityLedger
from .execution_context import WorksExecutionContext
from .workload_identity import WorkloadAssertion, WorkloadIdentityVerifier


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    allowed: bool
    principal: str
    grant_id: str
    scope: str
    execution_context_id: str
    identity_key_id: str


class TrustGatewayValidator:
    """Local reference admission gate binding identity + WORKS context + authority.

    This is not a networked Trust Gateway implementation and does not claim SPIFFE
    or OIDC conformance. It defines the fail-closed contract that adapters can call.
    """

    def __init__(self, *, identity_verifier: WorkloadIdentityVerifier, authority: AuthorityLedger, audience: str = "aftergraph-trust-gateway") -> None:
        self.identity_verifier = identity_verifier
        self.authority = authority
        self.audience = audience

    def admit(self, *, assertion: WorkloadAssertion, context: WorksExecutionContext, grant_id: str, scope: str, amount_usd: float, now: datetime) -> AdmissionDecision:
        identity = self.identity_verifier.verify(assertion, audience=self.audience, now=now)
        if identity.execution_context_id != context.execution_context_id:
            raise RuntimeError("workload identity execution context mismatch")
        if identity.principal != context.principal:
            raise RuntimeError("workload identity principal mismatch")
        grant = self.authority.authorize(grant_id, scope=scope, amount_usd=amount_usd, now=now)
        if grant.principal != context.principal:
            raise RuntimeError("authority principal mismatch")
        return AdmissionDecision(True, context.principal, grant_id, scope, context.execution_context_id, identity.key_id)
