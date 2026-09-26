from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .diverse_quorum import DiversityQuorumPolicy, DiversityQuorumVerifier
from .proof_graph import EvidenceClaim
from .proof_replication import ProofReplicator
from .proof_sync import SqliteProofGraphStore
from .remote_execution import RemoteExecutionCoordinator, RemoteWorkOrder, validate_execution_journal
from .remote_worker import RemoteWorkerClient


@dataclass(frozen=True, slots=True)
class RemoteVerifierTarget:
    worker_id: str
    trust_domain: str
    client: RemoteWorkerClient
    lease_id: str
    fencing_token: int
    authority_grant_id: str


@dataclass(frozen=True, slots=True)
class MultiNodeResult:
    mission_id: str
    subject: str
    receipts: int
    proof_revision: int
    accepted: bool
    positive_trust_domains: tuple[str, ...]
    journal_heads: tuple[str, ...]


class MultiNodeVerificationCoordinator:
    """Coordinate identical candidate verification across independent worker nodes."""

    def __init__(self, *, store: SqliteProofGraphStore, graph_id: str, min_trust_domains: int = 2) -> None:
        if min_trust_domains < 1:
            raise ValueError("min_trust_domains must be >= 1")
        self.store = store
        self.graph_id = graph_id
        self.policy = DiversityQuorumPolicy(min_positive=min_trust_domains, min_trust_domains=min_trust_domains)

    def verify(
        self,
        *,
        mission_id: str,
        node_id: str,
        execution_context_id: str,
        candidate_sha: str,
        targets: Iterable[RemoteVerifierTarget],
    ) -> MultiNodeResult:
        target_list = list(targets)
        if len({t.trust_domain for t in target_list}) < self.policy.min_trust_domains:
            raise RuntimeError("insufficient independent trust domains")
        graph, revision = self.store.read(self.graph_id)
        heads: list[str] = []
        receipts = 0
        for target in target_list:
            order = RemoteWorkOrder(
                mission_id=mission_id,
                node_id=node_id,
                execution_context_id=execution_context_id,
                lease_id=target.lease_id,
                fencing_token=target.fencing_token,
                authority_grant_id=target.authority_grant_id,
                candidate_sha=candidate_sha,
            )
            receipt = RemoteExecutionCoordinator(target.client).execute(order)
            head = validate_execution_journal(receipt)
            heads.append(head)
            receipts += 1
            claim = EvidenceClaim.mint(
                subject=candidate_sha,
                predicate="verified",
                verifier=target.worker_id,
                method="remote_multi_node",
                verdict=receipt.passed,
                metadata={"trust_domain": target.trust_domain, "journal_head_sha256": head},
            )
            graph.add_claim(claim)
            revision = self.store.compare_and_swap(self.graph_id, expected_revision=revision, graph=graph)
            graph, revision = self.store.read(self.graph_id)
        verdict = DiversityQuorumVerifier(self.policy).evaluate(
            graph, subject=candidate_sha, predicate="verified",
        )
        return MultiNodeResult(
            mission_id=mission_id,
            subject=candidate_sha,
            receipts=receipts,
            proof_revision=revision,
            accepted=verdict.accepted,
            positive_trust_domains=tuple(verdict.positive_trust_domains),
            journal_heads=tuple(heads),
        )
