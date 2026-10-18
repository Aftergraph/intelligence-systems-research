from jev_engineering.diverse_quorum import DiversityQuorumPolicy, DiversityQuorumVerifier
from jev_engineering.proof_graph import EvidenceClaim, ProofGraph


def _claim(verifier, domain, verdict=True):
    return EvidenceClaim.mint(subject="sha", predicate="valid", verifier=verifier, method="test", verdict=verdict, metadata={"trust_domain": domain})


def test_quorum_requires_independent_trust_domains():
    graph = ProofGraph(); graph.add_claim(_claim("v1","same")); graph.add_claim(_claim("v2","same"))
    q = DiversityQuorumVerifier(DiversityQuorumPolicy(min_positive=2, min_trust_domains=2))
    assert q.evaluate(graph, subject="sha", predicate="valid").accepted is False
    graph.add_claim(_claim("v3","other"))
    verdict = q.evaluate(graph, subject="sha", predicate="valid")
    assert verdict.accepted is True
    assert verdict.positive_trust_domains == ("other", "same")


def test_negative_vote_fails_closed():
    graph = ProofGraph(); graph.add_claim(_claim("v1","a")); graph.add_claim(_claim("v2","b")); graph.add_claim(_claim("v3","c", False))
    q = DiversityQuorumVerifier(DiversityQuorumPolicy())
    verdict = q.evaluate(graph, subject="sha", predicate="valid")
    assert verdict.conflict is True and verdict.accepted is False
