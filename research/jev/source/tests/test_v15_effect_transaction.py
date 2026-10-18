from pathlib import Path

import pytest

from jev_engineering.effect_transactions import EffectState, FileEffectTransaction
from jev_engineering.proof_graph import EvidenceClaim, ProofGraph


def _proof_for(path: Path) -> tuple[ProofGraph, str]:
    graph = ProofGraph()
    data = path.read_bytes()
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    claim = EvidenceClaim.mint(
        subject=f"sha256:{digest}",
        predicate="effect_verified",
        verifier="test:independent",
        method="readback+test",
        verdict=True,
        dependencies={"target": digest},
    )
    graph.add_claim(claim)
    return graph, claim.claim_id


def test_effect_transaction_requires_full_state_machine_and_proof(tmp_path: Path):
    target = tmp_path / "app.txt"
    target.write_text("before", encoding="utf-8")

    tx = FileEffectTransaction(tmp_path)
    proposal = tx.prepare("app.txt", "after", expected_effect="app.txt contains after")
    assert proposal.kind == "file_write"
    assert target.read_text() == "before"
    assert tx.state is EffectState.PREPARED

    tx.authorize(principal="tester", authority_ref="lease:test")
    tx.speculate()
    assert target.read_text() == "before"

    tx.execute()
    assert target.read_text() == "after"
    readback = tx.readback()
    assert readback.matches_expected is True

    graph, claim_id = _proof_for(target)
    tx.verify(graph, claim_ids=[claim_id])
    receipt = tx.commit()
    assert tx.state is EffectState.COMMITTED
    assert receipt.state == "committed"
    assert receipt.verifier_claim_ids == (claim_id,)
    assert receipt.preimage_sha256 != receipt.postimage_sha256


def test_failed_verification_can_compensate_without_clobbering_newer_state(tmp_path: Path):
    target = tmp_path / "app.txt"
    target.write_text("before", encoding="utf-8")
    tx = FileEffectTransaction(tmp_path)
    tx.prepare("app.txt", "after", expected_effect="change")
    tx.authorize(principal="tester", authority_ref="lease:test")
    tx.speculate()
    tx.execute()
    tx.readback()

    empty = ProofGraph()
    with pytest.raises(RuntimeError, match="verification proof"):
        tx.verify(empty, claim_ids=["missing"])
    tx.compensate()
    assert target.read_text() == "before"
    assert tx.state is EffectState.COMPENSATED

    tx2 = FileEffectTransaction(tmp_path)
    tx2.prepare("app.txt", "after", expected_effect="change")
    tx2.authorize(principal="tester", authority_ref="lease:test")
    tx2.speculate(); tx2.execute(); tx2.readback()
    target.write_text("newer actor", encoding="utf-8")
    with pytest.raises(RuntimeError, match="workspace drift"):
        tx2.compensate()
    assert target.read_text() == "newer actor"
