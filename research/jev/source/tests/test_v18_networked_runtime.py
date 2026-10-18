from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jev_engineering.authority import AuthorityLedger
from jev_engineering.durable_state import SqliteLeaseStore
from jev_engineering.execution_context import WorksExecutionContext
from jev_engineering.mission_graph import MissionGraph, MissionNode, NodeState
from jev_engineering.networked_runtime import NetworkedMissionRuntime
from jev_engineering.proof_graph import EvidenceClaim
from jev_engineering.proof_sync import SqliteProofGraphStore
from jev_engineering.trust_gateway import TrustGatewayValidator
from jev_engineering.worker_fabric import WorkerDirectory, WorkerEndpoint
from jev_engineering.workload_identity import Ed25519WorkloadIssuer, WorkloadIdentityVerifier


def test_networked_runtime_binds_worker_identity_lease_authority_and_proof_revision(tmp_path) -> None:
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    issuer = Ed25519WorkloadIssuer.generate(key_id="wid-k1", principal="worker:lenovo")
    identities = WorkloadIdentityVerifier({issuer.key_id: issuer.public_key_bytes()})
    authority = AuthorityLedger()
    grant = authority.issue_root(authority_ref="human:jonas", principal="worker:lenovo", scopes={"mission.execute"}, budget_usd=1, expires_at=now+timedelta(hours=1), delegation_depth=0)
    graph = MissionGraph([MissionNode("n1", metadata={"required_capabilities": ["python"]})])
    directory = WorkerDirectory()
    directory.register(WorkerEndpoint("lenovo", "habitat:lenovo", "aftergraph://jonas-lenovo", frozenset({"python"}), issuer.key_id, now))
    context = WorksExecutionContext.create(mission_id="m1", node_id="n1", principal="worker:lenovo")
    assertion = issuer.issue(audience="aftergraph-trust-gateway", execution_context_id=context.execution_context_id, ttl=timedelta(minutes=5), now=now)
    runtime = NetworkedMissionRuntime(
        graph=graph,
        leases=SqliteLeaseStore(tmp_path / "leases.db"),
        authority=authority,
        trust_gateway=TrustGatewayValidator(identity_verifier=identities, authority=authority),
        workers=directory,
        proof_store=SqliteProofGraphStore(tmp_path / "proof.db"),
        proof_graph_id="mission:m1",
    )
    dispatch = runtime.dispatch(node_id="n1", worker_id="lenovo", grant_id=grant.grant_id, context=context, assertion=assertion, ttl=timedelta(minutes=5), now=now)
    assert dispatch.lease.worker_id == "lenovo"
    assert dispatch.execution_context_id == context.execution_context_id
    claim = EvidenceClaim.mint(subject="node:n1", predicate="verified", verifier="sentinel:a", method="unit", verdict=True)
    revision = runtime.publish_claim(claim, expected_revision=dispatch.proof_revision)
    assert revision == dispatch.proof_revision + 1
    runtime.mark_verified("n1", dispatch.lease.lease_id, dispatch.lease.fencing_token, now=now, required_claim_ids=(claim.claim_id,))
    runtime.commit("n1", dispatch.lease.lease_id, dispatch.lease.fencing_token, now=now)
    assert graph.nodes["n1"].state is NodeState.COMMITTED
