from __future__ import annotations

from pathlib import Path

import pytest

from jev_engineering.proof_graph import EvidenceClaim, ProofGraph
from jev_engineering.speculation import SpeculativeFileTransaction


def _accepted_graph() -> tuple[ProofGraph, str]:
    graph = ProofGraph()
    claim = EvidenceClaim.mint(
        subject="node:n1",
        predicate="verified",
        verifier="sentinel",
        method="tests",
        verdict=True,
    )
    graph.add_claim(claim)
    return graph, claim.claim_id


def test_speculative_write_is_invisible_until_proof_gated_commit(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    tx = SpeculativeFileTransaction(tmp_path)
    tx.stage_write("app.py", "value = 2\n")
    assert target.read_text(encoding="utf-8") == "value = 1\n"

    graph, claim_id = _accepted_graph()
    committed = tx.commit(graph, prerequisite_claim_ids=(claim_id,))
    assert committed == ["app.py"]
    assert target.read_text(encoding="utf-8") == "value = 2\n"


def test_speculative_commit_fails_closed_without_accepted_prerequisite(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    tx = SpeculativeFileTransaction(tmp_path)
    tx.stage_write("app.py", "value = 2\n")
    graph = ProofGraph()
    with pytest.raises(RuntimeError, match="prerequisite proof"):
        tx.commit(graph, prerequisite_claim_ids=("missing",))
    assert target.read_text(encoding="utf-8") == "value = 1\n"


def test_speculative_commit_detects_workspace_drift(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    tx = SpeculativeFileTransaction(tmp_path)
    tx.stage_write("app.py", "value = 2\n")
    target.write_text("value = 3\n", encoding="utf-8")
    graph, claim_id = _accepted_graph()
    with pytest.raises(RuntimeError, match="preimage changed"):
        tx.commit(graph, prerequisite_claim_ids=(claim_id,))
    assert target.read_text(encoding="utf-8") == "value = 3\n"


def test_speculative_transaction_rejects_path_escape(tmp_path: Path) -> None:
    tx = SpeculativeFileTransaction(tmp_path)
    with pytest.raises(ValueError, match="workspace"):
        tx.stage_write("../escape.txt", "no")
