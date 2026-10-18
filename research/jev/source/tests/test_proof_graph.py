from __future__ import annotations

from jev_engineering.proof_graph import EvidenceClaim, ProofGraph


def _claim(claim_id: str, *, deps=None, parents=(), verdict=True) -> EvidenceClaim:
    return EvidenceClaim(
        claim_id=claim_id,
        subject=f"sha256:{claim_id}",
        predicate="tests_pass",
        verifier="sentinel:test",
        method="pytest",
        verdict=verdict,
        dependencies=deps or {},
        parent_claim_ids=parents,
    )


def test_dependency_change_invalidates_only_affected_claim_and_transitive_children() -> None:
    graph = ProofGraph()
    graph.add_claim(_claim("a", deps={"src/a.py": "h1"}))
    graph.add_claim(_claim("b", deps={"src/b.py": "h2"}))
    graph.add_claim(_claim("mission", parents=("a", "b")))

    stale = graph.observe_dependency("src/a.py", "changed")

    assert stale == {"a", "mission"}
    assert graph.status("a") == "stale"
    assert graph.status("mission") == "stale"
    assert graph.status("b") == "active"
    assert graph.is_fresh("b") is True
    assert graph.is_fresh("mission") is False


def test_failed_claim_never_satisfies_acceptance_even_when_fresh() -> None:
    graph = ProofGraph()
    graph.add_claim(_claim("failed", verdict=False))
    assert graph.is_fresh("failed") is True
    assert graph.accepts(["failed"]) is False


def test_proof_graph_round_trip_preserves_status_and_dependencies(tmp_path) -> None:
    path = tmp_path / "proof.json"
    graph = ProofGraph()
    graph.add_claim(_claim("a", deps={"tree": "v1"}))
    graph.observe_dependency("tree", "v2")
    graph.save(path)

    loaded = ProofGraph.load(path)
    assert loaded.status("a") == "stale"
    assert loaded.claim("a").dependencies == {"tree": "v1"}


def test_persisted_workspace_claim_is_invalidated_when_workspace_changes(tmp_path) -> None:
    from jev_engineering.proof_graph import workspace_tree_hash

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    tree_v1 = workspace_tree_hash(repo)
    graph = ProofGraph()
    claim = EvidenceClaim.mint(
        subject=f"sha256:{tree_v1}",
        predicate="tests_pass",
        verifier="sentinel:test",
        method="pytest",
        verdict=True,
        dependencies={"workspace_tree": tree_v1},
    )
    graph.add_claim(claim)
    path = tmp_path / "proof.json"
    graph.save(path)

    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    loaded = ProofGraph.load(path)
    stale = loaded.observe_dependency("workspace_tree", workspace_tree_hash(repo))
    assert claim.claim_id in stale
    assert loaded.status(claim.claim_id) == "stale"
