import copy, hashlib, json
import pytest

from jev_engineering.adaptive_swarm import (
    AdaptiveCompetenceRouter, AdaptiveTopologyRewriter, CompetenceLedger,
    CrossProviderReceiptChain, VerifiedOutcome,
)
from jev_engineering.heterogeneous_agents import (
    BackendBinding, BackendExecution, BackendIdentity, BackendKind, BackendRegistry,
    HeterogeneousSubagentExecutor, TopologyMode,
)
from jev_engineering.multi_agent import MultiAgentPlan, SubagentSpec, SubagentStatus, SubagentTask
from jev_engineering.public_receipts import Ed25519ReceiptSigner, PublicSignedReceipt


def ident(name, score):
    return BackendIdentity(name, BackendKind.LOCAL, "local", name, capabilities=frozenset({"code"}), competence={"code": score})

def fn(identity, spec, task, context, trace_id, span_id):
    return BackendExecution(SubagentStatus.SUCCESS, {"backend": identity.backend_id}, 0.9)

def evidence(seed):
    return hashlib.sha256(seed.encode()).hexdigest()


def test_verified_outcome_requires_two_independent_verifiers():
    with pytest.raises(ValueError, match="two independent"):
        VerifiedOutcome("a","code",True,1.0,("v1",),evidence("x"))


def test_ledger_updates_only_from_verified_outcome_and_is_bounded():
    ledger=CompetenceLedger(alpha=0.5)
    a=ident("a",0.8); ledger.seed(a)
    row=ledger.apply(VerifiedOutcome("a","code",True,1.0,("v1","v2"),evidence("1")))
    assert row.prior==0.8 and row.updated==pytest.approx(0.9)
    row2=ledger.apply(VerifiedOutcome("a","code",False,1.0,("v1","v3"),evidence("2")))
    assert row2.updated==pytest.approx(0.45)
    assert 0 <= ledger.score(a,"code") <= 1


def test_duplicate_evidence_cannot_train_twice():
    ledger=CompetenceLedger(); a=ident("a",0.5); ledger.seed(a)
    out=VerifiedOutcome("a","code",True,1.0,("v1","v2"),evidence("same"))
    ledger.apply(out)
    with pytest.raises(ValueError, match="duplicate"):
        ledger.apply(out)


def test_adaptive_router_changes_route_after_verified_feedback():
    reg=BackendRegistry(); reg.register(ident("a",0.9),fn); reg.register(ident("b",0.8),fn)
    ledger=CompetenceLedger(alpha=1.0)
    router=AdaptiveCompetenceRouter(reg,(BackendBinding("builder",("a","b"),frozenset({"code"}),"code",0.1),),ledger)
    assert router.select(SubagentSpec("builder","build")).backend_id=="a"
    ledger.apply(VerifiedOutcome("a","code",False,1.0,("v1","v2"),evidence("fail-a")))
    assert router.select(SubagentSpec("builder","build")).backend_id=="b"


def make_receipt(backend_id, provider="local", live=False):
    reg=BackendRegistry()
    identity=BackendIdentity(backend_id, BackendKind.LOCAL, provider, backend_id, capabilities=frozenset({"code"}), competence={"code":1.0})
    reg.register(identity,fn)
    router=AdaptiveCompetenceRouter(reg,(BackendBinding("builder",(backend_id,),frozenset({"code"}),"code"),),CompetenceLedger())
    hx=HeterogeneousSubagentExecutor(registry=reg,router=router,signer=Ed25519ReceiptSigner.generate(key_id=backend_id),persistent_signing_key=False)
    hx(SubagentSpec("builder","build"),SubagentTask("t","builder",{}),{},"trace","span")
    return hx.receipts[0]


def test_cross_provider_chain_is_order_bound_and_verifiable():
    signer=Ed25519ReceiptSigner.generate(key_id="chain")
    chain=CrossProviderReceiptChain(signer)
    chain.append(make_receipt("a")); chain.append(make_receipt("b"))
    sealed=chain.seal()
    assert chain.verify(sealed)
    assert sealed.payload["links"][1]["previous_link_sha256"]==sealed.payload["links"][0]["link_sha256"]


def test_tampered_chain_fails_verification():
    signer=Ed25519ReceiptSigner.generate(key_id="chain")
    chain=CrossProviderReceiptChain(signer); chain.append(make_receipt("a")); chain.append(make_receipt("b"))
    sealed=chain.seal(); payload=copy.deepcopy(sealed.payload); payload["links"][1]["provider"]="evil"
    tampered=PublicSignedReceipt(payload=payload,key_id=sealed.key_id,algorithm=sealed.algorithm,payload_sha256=sealed.payload_sha256,signature_b64=sealed.signature_b64)
    assert not chain.verify(tampered)


def test_chain_does_not_elevate_non_live_receipts():
    chain=CrossProviderReceiptChain(Ed25519ReceiptSigner.generate(key_id="c")); chain.append(make_receipt("a"));
    assert not chain.all_live and not chain.seal().payload["all_live"]


def plan(roots=2):
    agents=tuple(SubagentSpec(f"a{i}","r") for i in range(roots))
    tasks=tuple(SubagentTask(f"t{i}",f"a{i}",{}) for i in range(roots))
    return MultiAgentPlan("m","o",agents,tasks,max_parallelism=4)


def test_topology_rewriter_degrades_to_hierarchical_on_verified_failures():
    p,d=AdaptiveTopologyRewriter(failure_threshold=0.2).rewrite(plan(),recent_successes=2,recent_failures=1,current=TopologyMode.PARALLEL)
    assert d.to_mode is TopologyMode.HIERARCHICAL and p.max_parallelism==1


def test_topology_rewriter_allows_parallel_when_failure_rate_low():
    p,d=AdaptiveTopologyRewriter(failure_threshold=0.3).rewrite(plan(),recent_successes=9,recent_failures=1,current=TopologyMode.HIERARCHICAL)
    assert d.to_mode is TopologyMode.PARALLEL and p.max_parallelism==2


def test_topology_rewriter_does_not_mutate_dependencies_or_agents():
    original=plan(); rewritten,_=AdaptiveTopologyRewriter().rewrite(original,recent_successes=5,recent_failures=0,current=TopologyMode.AUTO)
    assert rewritten.tasks==original.tasks and rewritten.agents==original.agents

def test_ledger_history_is_append_only_snapshot():
    ledger=CompetenceLedger(alpha=0.2); a=ident("a",0.5); ledger.seed(a)
    ledger.apply(VerifiedOutcome("a","code",True,0.7,("v1","v2"),evidence("h1")))
    snap=ledger.history
    assert len(snap)==1 and snap[0].backend_id=="a"


def test_failed_outcome_uses_zero_observed_quality():
    ledger=CompetenceLedger(alpha=0.5); a=ident("a",1.0); ledger.seed(a)
    row=ledger.apply(VerifiedOutcome("a","code",False,1.0,("v1","v2"),evidence("f")))
    assert row.observed==0.0 and row.updated==pytest.approx(0.5)


def test_router_respects_min_competence_after_learning_drop():
    reg=BackendRegistry(); reg.register(ident("a",0.8),fn)
    ledger=CompetenceLedger(alpha=1.0)
    router=AdaptiveCompetenceRouter(reg,(BackendBinding("builder",("a",),frozenset({"code"}),"code",0.5),),ledger)
    ledger.apply(VerifiedOutcome("a","code",False,0.9,("v1","v2"),evidence("drop")))
    with pytest.raises(RuntimeError,match="no eligible"):
        router.select(SubagentSpec("builder","build"))


def test_router_preserves_capability_gate_despite_high_learned_score():
    reg=BackendRegistry(); bad=BackendIdentity("a",BackendKind.LOCAL,"local","a",capabilities=frozenset({"read"}),competence={"code":1.0}); reg.register(bad,fn)
    router=AdaptiveCompetenceRouter(reg,(BackendBinding("builder",("a",),frozenset({"code"}),"code"),),CompetenceLedger())
    with pytest.raises(RuntimeError): router.select(SubagentSpec("builder","build"))


def test_verified_outcome_rejects_bad_digest_length():
    with pytest.raises(ValueError,match="SHA-256"):
        VerifiedOutcome("a","code",True,1.0,("v1","v2"),"abc")


def test_chain_seal_rejects_empty_as_verified():
    chain=CrossProviderReceiptChain(Ed25519ReceiptSigner.generate(key_id="empty"))
    sealed=chain.seal()
    assert not chain.verify(sealed)


def test_chain_link_indices_are_monotonic():
    chain=CrossProviderReceiptChain(Ed25519ReceiptSigner.generate(key_id="mono"))
    for x in ("a","b","c"): chain.append(make_receipt(x))
    assert [x.index for x in chain.links]==[0,1,2]


def test_chain_previous_hash_connects_every_link():
    chain=CrossProviderReceiptChain(Ed25519ReceiptSigner.generate(key_id="prev"))
    for x in ("a","b","c"): chain.append(make_receipt(x))
    assert chain.links[1].previous_link_sha256==chain.links[0].link_sha256
    assert chain.links[2].previous_link_sha256==chain.links[1].link_sha256


def test_topology_rewriter_zero_history_is_deterministic():
    p,d=AdaptiveTopologyRewriter().rewrite(plan(),recent_successes=0,recent_failures=0,current=TopologyMode.AUTO)
    assert d.to_mode is TopologyMode.PARALLEL and p.max_parallelism==2


def test_topology_rewriter_caps_parallelism():
    p=plan(4)
    rewritten,d=AdaptiveTopologyRewriter(max_parallelism=2).rewrite(p,recent_successes=10,recent_failures=0,current=TopologyMode.AUTO)
    assert d.max_parallelism==2 and rewritten.max_parallelism==2


def test_topology_rewriter_validates_policy():
    with pytest.raises(ValueError): AdaptiveTopologyRewriter(failure_threshold=1.1)
    with pytest.raises(ValueError): AdaptiveTopologyRewriter(max_parallelism=0)