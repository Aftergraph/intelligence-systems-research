from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .authority import AuthorityLedger
from .distributed_runtime import DistributedMissionRuntime
from .execution_context import WorksExecutionContext
from .mission_graph import MissionGraph
from .proof_graph import EvidenceClaim
from .proof_sync import SqliteProofGraphStore
from .trust_gateway import TrustGatewayValidator
from .worker_fabric import WorkerDirectory
from .workload_identity import WorkloadAssertion


@dataclass(frozen=True, slots=True)
class NetworkDispatch:
    lease: object
    execution_context_id: str
    proof_revision: int
    endpoint_uri: str
    habitat_id: str


class NetworkedMissionRuntime:
    """Reference identity-bound runtime joining WORKS context, TG admission,
    durable lease fencing, worker discovery and synchronized proof state.

    Transport is deliberately out of scope: this class produces/adjudicates the
    dispatch contract but does not open SSH, RPC or an Aftergraph node channel.
    """

    def __init__(
        self,
        *,
        graph: MissionGraph,
        leases,
        authority: AuthorityLedger,
        trust_gateway: TrustGatewayValidator,
        workers: WorkerDirectory,
        proof_store: SqliteProofGraphStore,
        proof_graph_id: str,
        max_parallel_workers: int = 4,
    ) -> None:
        self.graph = graph
        self.leases = leases
        self.authority = authority
        self.trust_gateway = trust_gateway
        self.workers = workers
        self.proof_store = proof_store
        self.proof_graph_id = proof_graph_id
        self.runtime = DistributedMissionRuntime(
            graph, leases, authority, max_parallel_workers=max_parallel_workers,
        )

    def dispatch(
        self,
        *,
        node_id: str,
        worker_id: str,
        grant_id: str,
        context: WorksExecutionContext,
        assertion: WorkloadAssertion,
        ttl: timedelta,
        now: datetime,
    ) -> NetworkDispatch:
        if context.node_id != node_id:
            raise RuntimeError("execution context node mismatch")
        worker = self.workers.get(worker_id)
        if now - worker.last_seen > self.workers.stale_after:
            raise RuntimeError("worker endpoint is stale")
        if worker.identity_key_id != assertion.key_id:
            raise RuntimeError("worker identity key mismatch")
        self.trust_gateway.admit(
            assertion=assertion,
            context=context,
            grant_id=grant_id,
            scope=self.runtime._authority_scope(node_id),
            amount_usd=0,
            now=now,
        )
        lease = self.runtime.dispatch(
            node_id,
            worker_id=worker_id,
            authority_grant_id=grant_id,
            capabilities=worker.capabilities,
            ttl=ttl,
            now=now,
        )
        _, revision = self.proof_store.read(self.proof_graph_id)
        return NetworkDispatch(
            lease=lease,
            execution_context_id=context.execution_context_id,
            proof_revision=revision,
            endpoint_uri=worker.endpoint_uri,
            habitat_id=worker.habitat_id,
        )

    def publish_claim(self, claim: EvidenceClaim, *, expected_revision: int) -> int:
        graph, actual = self.proof_store.read(self.proof_graph_id)
        if actual != expected_revision:
            raise RuntimeError(f"proof graph revision conflict: expected {expected_revision}, observed {actual}")
        graph.add_claim(claim)
        return self.proof_store.compare_and_swap(
            self.proof_graph_id, expected_revision=expected_revision, graph=graph,
        )

    def mark_verified(
        self,
        node_id: str,
        lease_id: str,
        fencing_token: int,
        *,
        now: datetime,
        required_claim_ids: tuple[str, ...] | list[str],
    ) -> None:
        graph, _ = self.proof_store.read(self.proof_graph_id)
        if not graph.accepts(tuple(required_claim_ids)):
            raise RuntimeError("required synchronized proof is not accepted")
        self.runtime.mark_verified(node_id, lease_id, fencing_token, now=now)

    def commit(self, node_id: str, lease_id: str, fencing_token: int, *, now: datetime) -> None:
        self.runtime.commit(node_id, lease_id, fencing_token, now=now)
