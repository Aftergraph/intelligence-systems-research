from __future__ import annotations

import pytest

from jev_engineering.proof_graph import EvidenceClaim, ProofGraph
from jev_engineering.proof_sync import SqliteProofGraphStore


def test_proof_graph_store_uses_optimistic_revision_fencing(tmp_path) -> None:
    store = SqliteProofGraphStore(tmp_path / "proof.db")
    g1, rev1 = store.read("mission:1")
    claim = EvidenceClaim.mint(subject="sha256:a", predicate="verified", verifier="v1", method="unit", verdict=True)
    g1.add_claim(claim)
    rev2 = store.compare_and_swap("mission:1", expected_revision=rev1, graph=g1)
    assert rev2 == rev1 + 1
    stale = ProofGraph()
    with pytest.raises(RuntimeError, match="revision"):
        store.compare_and_swap("mission:1", expected_revision=rev1, graph=stale)
    loaded, loaded_rev = store.read("mission:1")
    assert loaded_rev == rev2
    assert loaded.accepts([claim.claim_id])
