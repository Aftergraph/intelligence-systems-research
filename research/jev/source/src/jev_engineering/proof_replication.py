from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .proof_graph import EvidenceClaim, ProofGraph
from .proof_sync import SqliteProofGraphStore


@dataclass(frozen=True, slots=True)
class ProofDelta:
    graph_id: str
    base_revision: int
    claims: tuple[EvidenceClaim, ...]


class ProofReplicator:
    """Revision-fenced replication of independently minted evidence claims."""

    def __init__(self, store: SqliteProofGraphStore) -> None:
        self.store = store

    def export_delta(self, graph_id: str, *, base_revision: int, claims: Iterable[EvidenceClaim]) -> ProofDelta:
        return ProofDelta(graph_id=graph_id, base_revision=base_revision, claims=tuple(claims))

    def apply(self, delta: ProofDelta) -> int:
        graph, actual = self.store.read(delta.graph_id)
        if actual != delta.base_revision:
            raise RuntimeError(f"proof replication revision conflict: expected {delta.base_revision}, observed {actual}")
        for claim in delta.claims:
            graph.add_claim(claim)
        return self.store.compare_and_swap(delta.graph_id, expected_revision=actual, graph=graph)
