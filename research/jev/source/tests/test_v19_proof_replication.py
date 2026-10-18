import pytest

from jev_engineering.proof_graph import EvidenceClaim
from jev_engineering.proof_replication import ProofReplicator
from jev_engineering.proof_sync import SqliteProofGraphStore


def test_proof_replication_is_revision_fenced(tmp_path):
    store = SqliteProofGraphStore(tmp_path / "proof.db")
    repl = ProofReplicator(store)
    a = EvidenceClaim.mint(subject="node:n1", predicate="unit", verifier="sentinel:a", method="pytest", verdict=True)
    delta = repl.export_delta("mission:m1", base_revision=0, claims=[a])
    assert repl.apply(delta) == 1
    graph, revision = store.read("mission:m1")
    assert revision == 1 and graph.accepts((a.claim_id,))
    b = EvidenceClaim.mint(subject="node:n2", predicate="unit", verifier="sentinel:b", method="pytest", verdict=True)
    stale = repl.export_delta("mission:m1", base_revision=0, claims=[b])
    with pytest.raises(RuntimeError, match="revision conflict"):
        repl.apply(stale)
