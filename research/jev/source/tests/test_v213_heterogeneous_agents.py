import copy

import pytest

from jev_engineering.heterogeneous_agents import (
    BackendBinding,
    BackendExecution,
    BackendIdentity,
    BackendKind,
    BackendRegistry,
    CompetenceRouter,
    DynamicTopologySelector,
    HeterogeneousSubagentExecutor,
    TopologyMode,
)
from jev_engineering.multi_agent import (
    JoinMode,
    JoinPolicy,
    MultiAgentOrchestrator,
    MultiAgentPlan,
    SubagentSpec,
    SubagentStatus,
    SubagentTask,
)
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


def identity(backend_id, *, kind=BackendKind.LOCAL, provider="local", model="m", caps=(), competence=None,
             endpoint="", authenticated=False, live=False):
    return BackendIdentity(
        backend_id=backend_id, kind=kind, provider=provider, model=model,
        endpoint=endpoint, authenticated=authenticated, live_provider=live,
        capabilities=frozenset(caps), competence=competence or {},
    )


def ok_backend(backend, spec, task, context, trace_id, span_id):
    return BackendExecution(
        status=SubagentStatus.SUCCESS,
        output={"backend": backend.backend_id, "task": task.task_id},
        confidence=0.9,
    )


def test_backend_identity_rejects_invalid_live_provider():
    with pytest.raises(ValueError, match="provider backend kind"):
        identity("x", live=True, authenticated=True, endpoint="https://x")
    with pytest.raises(ValueError, match="authenticated"):
        identity("x", kind=BackendKind.PROVIDER, live=True, endpoint="https://x")
    with pytest.raises(ValueError, match="https"):
        identity("x", kind=BackendKind.PROVIDER, live=True, authenticated=True, endpoint="http://x")


def test_competence_scores_are_bounded():
    with pytest.raises(ValueError, match="competence score"):
        identity("x", competence={"code": 1.1})


def test_registry_rejects_duplicate_backend():
    reg = BackendRegistry()
    reg.register(identity("a"), ok_backend)
    with pytest.raises(ValueError, match="duplicate backend_id"):
        reg.register(identity("a"), ok_backend)


def test_router_selects_highest_competence_backend():
    reg = BackendRegistry()
    reg.register(identity("fast", caps=("code",), competence={"code": 0.7}), ok_backend)
    reg.register(identity("strong", caps=("code",), competence={"code": 0.95}), ok_backend)
    router = CompetenceRouter(reg, (BackendBinding("builder", ("fast", "strong"), frozenset({"code"}), "code", 0.5),))
    decision = router.select(SubagentSpec("builder", "build"))
    assert decision.backend_id == "strong"
    assert decision.score == 0.95


def test_router_tie_breaks_deterministically_by_backend_id():
    reg = BackendRegistry()
    reg.register(identity("z", caps=("code",), competence={"code": 0.9}), ok_backend)
    reg.register(identity("a", caps=("code",), competence={"code": 0.9}), ok_backend)
    router = CompetenceRouter(reg, (BackendBinding("builder", ("z", "a"), frozenset({"code"}), "code"),))
    assert router.select(SubagentSpec("builder", "build")).backend_id == "a"


def test_router_fails_closed_when_capability_missing():
    reg = BackendRegistry()
    reg.register(identity("a", caps=("read",), competence={"code": 1.0}), ok_backend)
    router = CompetenceRouter(reg, (BackendBinding("builder", ("a",), frozenset({"write"}), "code"),))
    with pytest.raises(RuntimeError, match="no eligible backend"):
        router.select(SubagentSpec("builder", "build"))


def test_router_fails_closed_below_minimum_competence():
    reg = BackendRegistry()
    reg.register(identity("a", caps=("code",), competence={"code": 0.6}), ok_backend)
    router = CompetenceRouter(reg, (BackendBinding("builder", ("a",), frozenset({"code"}), "code", 0.7),))
    with pytest.raises(RuntimeError, match="no eligible backend"):
        router.select(SubagentSpec("builder", "build"))


def test_topology_auto_parallelizes_multiple_independent_roots():
    plan = MultiAgentPlan(
        mission_id="m", orchestrator_id="o",
        agents=(SubagentSpec("a", "r"), SubagentSpec("b", "r")),
        tasks=(SubagentTask("a", "a", {}), SubagentTask("b", "b", {})),
        max_parallelism=8,
    )
    applied, decision = DynamicTopologySelector(max_parallelism=4).apply(plan)
    assert decision.selected is TopologyMode.PARALLEL
    assert applied.max_parallelism == 2


def test_topology_auto_uses_hierarchical_for_single_root():
    plan = MultiAgentPlan(
        mission_id="m", orchestrator_id="o", agents=(SubagentSpec("a", "r"),),
        tasks=(SubagentTask("root", "a", {}), SubagentTask("child", "a", {}, dependencies=("root",))),
        max_parallelism=4,
    )
    applied, decision = DynamicTopologySelector().apply(plan)
    assert decision.selected is TopologyMode.HIERARCHICAL
    assert applied.max_parallelism == 1


def test_explicit_hierarchical_overrides_independent_roots():
    plan = MultiAgentPlan(
        mission_id="m", orchestrator_id="o",
        agents=(SubagentSpec("a", "r"), SubagentSpec("b", "r")),
        tasks=(SubagentTask("a", "a", {}), SubagentTask("b", "b", {})),
        max_parallelism=4,
    )
    applied, decision = DynamicTopologySelector().apply(plan, TopologyMode.HIERARCHICAL)
    assert applied.max_parallelism == 1
    assert decision.selected is TopologyMode.HIERARCHICAL


def make_executor(*, persistent=False, live_identity=False, backend_fn=ok_backend):
    reg = BackendRegistry()
    ident = identity(
        "backend",
        kind=BackendKind.PROVIDER if live_identity else BackendKind.LOCAL,
        provider="provider" if live_identity else "local",
        model="model",
        caps=("code",), competence={"code": 0.9},
        endpoint="https://provider.example/v1" if live_identity else "",
        authenticated=live_identity, live=live_identity,
    )
    reg.register(ident, backend_fn)
    router = CompetenceRouter(reg, (BackendBinding("builder", ("backend",), frozenset({"code"}), "code", 0.5),))
    signer = Ed25519ReceiptSigner.generate(key_id="test")
    return HeterogeneousSubagentExecutor(registry=reg, router=router, signer=signer, persistent_signing_key=persistent), signer


def test_local_backend_emits_signed_non_live_receipt():
    executor, signer = make_executor()
    outcome = executor(SubagentSpec("builder", "build"), SubagentTask("t", "builder", {}), {}, "trace", "span")
    assert outcome.status is SubagentStatus.SUCCESS
    assert executor.verify_receipts()
    assert not executor.receipts[0].live_provider_evidence
    assert not executor.authenticated_live_provider_execution
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    assert verifier.verify(executor.receipts[0].receipt)


def test_ephemeral_key_prevents_live_evidence_even_with_live_attestation():
    def live_backend(*args):
        return BackendExecution(
            status=SubagentStatus.SUCCESS, output={"ok": True}, confidence=0.9,
            provider_request_ids=("req-1",), evidence_origin="live-provider",
            authenticated=True, transport_security="https",
        )
    executor, _ = make_executor(persistent=False, live_identity=True, backend_fn=live_backend)
    outcome = executor(SubagentSpec("builder", "build"), SubagentTask("t", "builder", {}), {}, "trace", "span")
    assert outcome.status is SubagentStatus.FAILURE
    assert "invalid_live_provider_attestation" in outcome.errors
    assert not executor.receipts[0].live_provider_evidence


def test_persistent_key_plus_complete_live_attestation_is_live_evidence():
    def live_backend(*args):
        return BackendExecution(
            status=SubagentStatus.SUCCESS, output={"ok": True}, confidence=0.91,
            provider_request_ids=("req-1", "req-2"), evidence_origin="live-provider",
            authenticated=True, transport_security="https",
        )
    executor, _ = make_executor(persistent=True, live_identity=True, backend_fn=live_backend)
    outcome = executor(SubagentSpec("builder", "build"), SubagentTask("t", "builder", {}), {}, "trace", "span")
    assert outcome.status is SubagentStatus.SUCCESS
    assert executor.receipts[0].live_provider_evidence
    assert executor.authenticated_live_provider_execution


@pytest.mark.parametrize("field,value", [
    ("request_ids", ()),
    ("origin", "synthetic"),
    ("authenticated", False),
    ("transport", "http"),
])
def test_live_provider_attestation_fails_closed(field, value):
    def backend(*args):
        data = {
            "request_ids": ("req-1",), "origin": "live-provider",
            "authenticated": True, "transport": "https",
        }
        data[field] = value
        return BackendExecution(
            status=SubagentStatus.SUCCESS, output={"ok": True}, confidence=0.9,
            provider_request_ids=data["request_ids"], evidence_origin=data["origin"],
            authenticated=data["authenticated"], transport_security=data["transport"],
        )
    executor, _ = make_executor(persistent=True, live_identity=True, backend_fn=backend)
    outcome = executor(SubagentSpec("builder", "build"), SubagentTask("t", "builder", {}), {}, "trace", "span")
    assert outcome.status is SubagentStatus.FAILURE
    assert not executor.authenticated_live_provider_execution


def test_tampered_receipt_fails_verification():
    executor, signer = make_executor()
    executor(SubagentSpec("builder", "build"), SubagentTask("t", "builder", {}), {}, "trace", "span")
    original = executor.receipts[0].receipt
    payload = copy.deepcopy(original.payload)
    payload["status"] = "failure"
    tampered = PublicSignedReceipt(
        payload=payload, key_id=original.key_id, algorithm=original.algorithm,
        payload_sha256=original.payload_sha256, signature_b64=original.signature_b64,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    assert not verifier.verify(tampered)


def test_mixed_backends_execute_in_same_mission_and_emit_distinct_receipts():
    reg = BackendRegistry()
    reg.register(identity("research-model", caps=("research",), competence={"research": 0.8}), ok_backend)
    reg.register(identity("code-model", kind=BackendKind.WORKER, provider="aftergraph-worker", model="code", caps=("code",), competence={"code": 0.95}), ok_backend)
    bindings = (
        BackendBinding("researcher", ("research-model",), frozenset({"research"}), "research", 0.5),
        BackendBinding("builder", ("code-model",), frozenset({"code"}), "code", 0.5),
    )
    hx = HeterogeneousSubagentExecutor(
        registry=reg, router=CompetenceRouter(reg, bindings),
        signer=Ed25519ReceiptSigner.generate(key_id="mixed"), persistent_signing_key=False,
    )
    result = MultiAgentOrchestrator(executor=hx).run(
        MultiAgentPlan(
            mission_id="m", orchestrator_id="o",
            agents=(SubagentSpec("researcher", "research"), SubagentSpec("builder", "build")),
            tasks=(SubagentTask("r", "researcher", {}), SubagentTask("b", "builder", {})),
            join_policy=JoinPolicy(JoinMode.ALL), max_parallelism=2,
        ),
        context={},
    )
    assert result.accepted
    assert {row.receipt.payload["backend"]["backend_id"] for row in hx.receipts} == {"research-model", "code-model"}
    assert hx.verify_receipts()


def test_heterogeneous_executor_integrates_with_dependency_graph():
    reg = BackendRegistry()
    reg.register(identity("a", caps=("research",), competence={"research": 0.9}), ok_backend)
    reg.register(identity("b", caps=("code",), competence={"code": 0.9}), ok_backend)
    hx = HeterogeneousSubagentExecutor(
        registry=reg,
        router=CompetenceRouter(reg, (
            BackendBinding("researcher", ("a",), frozenset({"research"}), "research"),
            BackendBinding("builder", ("b",), frozenset({"code"}), "code"),
        )),
        signer=Ed25519ReceiptSigner.generate(key_id="dep"), persistent_signing_key=False,
    )
    plan = MultiAgentPlan(
        mission_id="m", orchestrator_id="o",
        agents=(
            SubagentSpec("researcher", "research"),
            SubagentSpec("builder", "build", context_keys=frozenset({"dependency_outputs"})),
        ),
        tasks=(
            SubagentTask("research", "researcher", {}),
            SubagentTask("build", "builder", {}, dependencies=("research",), required_context_keys=frozenset({"dependency_outputs"})),
        ),
        join_task_ids=("build",),
    )
    result = MultiAgentOrchestrator(executor=hx).run(plan, context={})
    assert result.accepted
    assert len(hx.receipts) == 2
    assert hx.receipts[1].receipt.payload["task_id"] == "build"