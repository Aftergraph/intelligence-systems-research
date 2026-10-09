from __future__ import annotations

from jev_engineering.proof_graph import EvidenceClaim, ProofGraph
from jev_engineering.quorum import QuorumPolicy, QuorumVerifier


def test_quorum_requires_unique_verifier_principals_and_fails_on_conflict() -> None:
    graph = ProofGraph()
    for verifier, verdict in [("sentinel:a", True), ("sentinel:b", True)]:
        graph.add_claim(EvidenceClaim.mint(subject="sha256:x", predicate="verified", verifier=verifier, method="independent", verdict=verdict))
    verdict = QuorumVerifier(QuorumPolicy(min_positive=2)).evaluate(graph, subject="sha256:x", predicate="verified")
    assert verdict.accepted is True
    assert verdict.positive_verifiers == ("sentinel:a", "sentinel:b")

    graph.add_claim(EvidenceClaim.mint(subject="sha256:x", predicate="verified", verifier="sentinel:c", method="independent", verdict=False))
    conflict = QuorumVerifier(QuorumPolicy(min_positive=2, reject_on_negative=True)).evaluate(graph, subject="sha256:x", predicate="verified")
    assert conflict.accepted is False
    assert conflict.conflict is True
