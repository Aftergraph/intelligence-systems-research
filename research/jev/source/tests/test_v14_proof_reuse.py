from __future__ import annotations

from jev_engineering.proof_graph import EvidenceClaim, ProofGraph


def test_exact_dependency_match_reuses_fresh_positive_evidence_only() -> None:
    graph = ProofGraph()
    claim = EvidenceClaim.mint(
        subject="sha256:abc",
        predicate="tests_pass",
        verifier="sentinel",
        method="pytest",
        verdict=True,
        dependencies={"workspace_tree": "abc", "tests": "v1"},
    )
    graph.add_claim(claim)

    reusable = graph.find_reusable(
        subject="sha256:abc",
        predicate="tests_pass",
        dependencies={"workspace_tree": "abc", "tests": "v1"},
    )
    assert [item.claim_id for item in reusable] == [claim.claim_id]

    graph.observe_dependency("tests", "v2")
    assert graph.find_reusable(
        subject="sha256:abc",
        predicate="tests_pass",
        dependencies={"workspace_tree": "abc", "tests": "v1"},
    ) == []


def test_reuse_can_require_specific_verifier_and_method() -> None:
    graph = ProofGraph()
    a = EvidenceClaim.mint(
        subject="artifact:x",
        predicate="safe",
        verifier="sentinel",
        method="static",
        verdict=True,
        dependencies={"artifact": "x"},
    )
    b = EvidenceClaim.mint(
        subject="artifact:x",
        predicate="safe",
        verifier="judge",
        method="semantic",
        verdict=True,
        dependencies={"artifact": "x"},
    )
    graph.add_claim(a)
    graph.add_claim(b)
    reusable = graph.find_reusable(
        subject="artifact:x",
        predicate="safe",
        dependencies={"artifact": "x"},
        verifier="sentinel",
        method="static",
    )
    assert [item.claim_id for item in reusable] == [a.claim_id]
