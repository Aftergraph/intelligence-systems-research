from __future__ import annotations

import httpx
import pytest

from jev_engineering.http_effects import HttpEffectState, HttpJsonEffectTransaction
from jev_engineering.proof_graph import EvidenceClaim, ProofGraph


def test_http_effect_requires_allowlisted_https_and_exact_readback() -> None:
    state = {'value': 1}
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal state
        if request.method == 'PATCH':
            state = {'value': 2}
            return httpx.Response(200, json=state)
        return httpx.Response(200, json=state)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    tx = HttpJsonEffectTransaction(client=client, allowed_hosts={'api.example.test'})
    proposal = tx.prepare(
        method='PATCH',
        url='https://api.example.test/resource/1',
        payload={'value': 2},
        readback_url='https://api.example.test/resource/1',
        expected_readback={'value': 2},
    )
    tx.authorize(principal='worker:1', authority_ref='lease:1')
    tx.execute()
    readback_sha = tx.readback()
    graph = ProofGraph()
    claim = EvidenceClaim.mint(
        subject=f'sha256:{readback_sha}', predicate='effect_correct', verifier='sentinel', method='readback', verdict=True
    )
    graph.add_claim(claim)
    tx.verify(graph, claim_ids=[claim.claim_id])
    receipt = tx.commit()
    assert receipt.state == 'committed'
    assert receipt.action_id == proposal.action_id


def test_http_effect_rejects_non_https_or_unlisted_host() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    tx = HttpJsonEffectTransaction(client=client, allowed_hosts={'good.test'})
    with pytest.raises(ValueError):
        tx.prepare(method='POST', url='http://good.test/x', payload={}, readback_url='https://good.test/x')
    tx = HttpJsonEffectTransaction(client=client, allowed_hosts={'good.test'})
    with pytest.raises(ValueError):
        tx.prepare(method='POST', url='https://evil.test/x', payload={}, readback_url='https://good.test/x')


def test_http_compensation_must_be_explicit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'ok': True})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    tx = HttpJsonEffectTransaction(client=client, allowed_hosts={'api.test'})
    tx.prepare(method='POST', url='https://api.test/x', payload={}, readback_url='https://api.test/x')
    tx.authorize(principal='p', authority_ref='a')
    tx.execute()
    with pytest.raises(RuntimeError):
        tx.compensate()
