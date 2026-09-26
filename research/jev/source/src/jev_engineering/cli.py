from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tempfile
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from .agent import CodingAgent
from .benchmark import aggregate_records, preflight_manifest, read_jsonl, run_manifest
from .config import AppConfig
from .credentials import hermes_profile_env, load_allowed_env_file
from .decisions import DecisionEngine
from .jev_client import JevClient
from .model_registry import ModelRegistry
from .learning import (
    CounterfactualReplay,
    DecisionDistillationCompiler,
    DecisionObservation,
    LearningCandidate,
    LearningRatchet,
    LearningState,
    PromotionPolicy,
    ShadowObservation,
)
from .proof_graph import EvidenceClaim, ProofGraph
from .speculation import SpeculativeFileTransaction
from .shadow_runtime import ShadowDecisionEngine, PromotionRegistry
from .effect_transactions import FileEffectTransaction
from .authority import AuthorityLedger
from .worker_leases import LeaseManager
from .distributed_runtime import DistributedMissionRuntime
from .mission_graph import MissionGraph, MissionNode
from .provider_failover import FailureKind, ProviderFailure, ProviderFailoverRouter, ProviderRoute
from .signed_receipts import ReceiptSigner, ReceiptVerifier
from .automatic_campaign import AutoCampaignController, AutoCampaignSchedule
from .learning_campaign import LearningCampaign, OutcomeSample
from .provider_health import run_provider_smoke
from .secrets import SecretResolver
from .providers.mock import ScriptedProviderFactory
from .testing import ScriptedDecisionBackend
from .durable_state import SqliteLeaseStore
from .execution_context import WorksExecutionContext
from .networked_runtime import NetworkedMissionRuntime
from .proof_sync import SqliteProofGraphStore
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from .quorum import QuorumPolicy, QuorumVerifier
from .trust_gateway import TrustGatewayValidator
from .worker_fabric import WorkerDirectory, WorkerEndpoint
from .workload_identity import Ed25519WorkloadIssuer, WorkloadIdentityVerifier
from .circuit_breaker import CircuitBreakerRegistry
from .node_transport import InMemoryNodeEndpoint, NodeProtocol, HttpNodeTransport
from .node_gateway import NodeGateway, NodeGatewayServer, OperationRegistry, client_mtls_context, server_mtls_context
from .pki import EphemeralCertificateAuthority
from .remote_control import LeaseControlService, PreconfiguredVerifierCapability
from .execution_journal import ExecutionJournal
from .signed_proof import SignedProofReplicator
from .diverse_quorum import DiversityQuorumPolicy, DiversityQuorumVerifier
from .remote_worker import RemoteWorkerClient
from .remote_execution import RemoteExecutionCoordinator, RemoteWorkOrder, make_journaled_verification_handler, validate_execution_journal
from .proof_replication import ProofReplicator
from .streaming_journal import JournalStreamRegistry, JournalStreamService, verify_journal_pages
from .live_metrics import MissionMeasurement, summarize_measurements, paired_frontier_efficiency_ratio
from .multi_node import MultiNodeVerificationCoordinator, RemoteVerifierTarget
from .node_daemon import NodeAgent, NodeAgentConfig, build_node_gateway, generate_node_config_template
from .node_client import NodeClientConfig, NodeClientSession, generate_client_config_template
from .relay_resilience import RelayGenerationStore, JournalCheckpointStore, ResumableJournalFollower
from .campaign_runtime import BenchmarkCostModel, TokenPrice, build_campaign_report
from .evidence_campaign import (
    EvidenceCampaignPolicy, ContinuousRegressionMonitor, RegressionPolicy,
    analyze_frontier_efficiency_target, evaluate_evidence_campaign, plan_noninferiority_pairs,
)
from .campaign_evidence import CampaignEvidenceBundle
from .physical_pair import PhysicalPairManifest, generate_physical_pair_template
from .relay_fabric import (
    RelayClientConfig, RelayCoordinatorClient, RelayHubConfig, RelayHubServer,
    RelayNodeAgent, RelayNodeClientSession, RelayNodeConfig, RelayNodeService,
    generate_relay_client_config_template, generate_relay_hub_config_template,
    generate_relay_node_config_template,
)
from .efficiency_execution import EmpiricalEfficiencyExecutionEngine, EfficiencyExecutionPolicy, ExecutionAttempt
from .system_efficiency import (
    AdaptiveContextBudgeter, EarlyExitGate, EfficiencyLever, FrontierWorkloadProfile,
    RetryBudgetOptimizer, RetryCandidate, SystemEfficiencyCompiler,
)
from .context_compiler import ContextCandidate
from .verification_portfolio import (
    VerificationMethod,
    VerificationPortfolioOptimizer,
    VerificationRequirement,
    VerifierCorrelationMatrix,
)

app = typer.Typer(no_args_is_help=True, help="Jev-governed frontier coding-agent harness.")
console = Console()


@app.command()
def models(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, readable=True)],
    frontier_only: Annotated[bool, typer.Option("--frontier-only")] = False,
) -> None:
    """Show configured/imported models and frontier eligibility."""
    cfg = AppConfig.load(config)
    rows = cfg.registry.eligible(frontier_required=True) if frontier_only else cfg.registry.models
    table = Table("alias", "provider", "model", "tier", "transport", "tools")
    for model in rows:
        table.add_row(
            model.alias,
            model.provider,
            model.model,
            model.tier,
            model.transport,
            "yes" if model.supports_tools else "no",
        )
    console.print(table)


@app.command("jev-models")
def jev_models(
    api_key_env: str = typer.Option("TYPESAFE_API_KEY"),
    base_url: str = typer.Option("https://api.typesafe.ai"),
) -> None:
    """Query TypeSafe's live GET /v1/models endpoint."""
    key = os.environ.get(api_key_env, "")
    if not key:
        raise typer.BadParameter(f"{api_key_env} is not set")
    with JevClient(api_key=key, base_url=base_url) as client:
        console.print_json(data=client.models())


@app.command()
def doctor(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, readable=True)],
) -> None:
    """Validate local configuration without sending network requests."""
    cfg = AppConfig.load(config)
    decision = cfg.raw.get("decision") or cfg.raw.get("jev") or {}
    backend = str(decision.get("backend") or "jev").casefold()
    table = Table("check", "state")
    table.add_row("Python", platform.python_version())
    if backend in {"jev", "typesafe"}:
        env = str(decision.get("api_key_env") or "TYPESAFE_API_KEY")
        table.add_row("Decision backend", "TypeSafe Jev")
        table.add_row("Jev API key", "present" if os.environ.get(env) else f"missing ({env})")
    elif backend in {"openai", "chatgpt", "gpt"}:
        env = str(decision.get("api_key_env") or "OPENAI_API_KEY")
        table.add_row("Decision backend", f"OpenAI {decision.get('model') or 'gpt-5.6-sol'}")
        table.add_row("OpenAI API key", "present" if os.environ.get(env) else f"missing ({env})")
    elif backend in {"openai_compatible", "compatible", "chat_completions"}:
        env = str(decision.get("api_key_env") or "DIALAGRAM_API_KEY")
        table.add_row(
            "Decision backend",
            f"OpenAI-compatible {decision.get('model') or 'qwen-3.8-max-thinking'}",
        )
        table.add_row("Compatible API key", "present" if os.environ.get(env) else f"missing ({env})")
    else:
        table.add_row("Decision backend", "LOCAL HEURISTIC — OFFLINE ONLY")
    frontier = cfg.registry.eligible(frontier_required=True)
    table.add_row("Catalog models", str(len(cfg.registry.models)))
    table.add_row("Eligible frontier models", str(len(frontier)))
    for model in frontier[:20]:
        env = model.api_key_env
        key_state = "n/a" if not env else ("present" if os.environ.get(env) else "missing")
        table.add_row(f"model:{model.alias}", f"{model.transport}; key={key_state}")
    if len(frontier) > 20:
        table.add_row("frontier list", f"+{len(frontier) - 20} more")
    table.add_row("bash", shutil.which("bash") or "missing")
    table.add_row("git", shutil.which("git") or "missing")
    table.add_row("Network", "not probed")
    console.print(table)


def _load_cli_credentials(env_file: Path | None, hermes_profile: str | None) -> dict[str, bool]:
    if env_file is not None and hermes_profile:
        raise typer.BadParameter("Use either --env-file or --hermes-profile, not both")
    if hermes_profile:
        env_file = hermes_profile_env(hermes_profile)
    if env_file is None:
        return {}
    return load_allowed_env_file(env_file)


@app.command("benchmark-preflight")
def benchmark_preflight(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
    env_file: Annotated[Path | None, typer.Option("--env-file")] = None,
    hermes_profile: Annotated[str | None, typer.Option("--hermes-profile")] = None,
) -> None:
    """Validate paired live-benchmark configs, fixtures, and credential presence."""
    loaded = _load_cli_credentials(env_file, hermes_profile)
    report = preflight_manifest(manifest)
    if loaded:
        report["credentials_loaded"] = sorted(name for name, present in loaded.items() if present)
    console.print_json(data=report)
    if report["missing_env"]:
        raise typer.Exit(code=3)


@app.command("benchmark")
def benchmark_run(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("benchmark-results"),
    repeats: Annotated[int, typer.Option("--repeats", "-r", min=1)] = 1,
    seed: Annotated[int, typer.Option("--seed")] = 20260924,
    env_file: Annotated[Path | None, typer.Option("--env-file")] = None,
    hermes_profile: Annotated[str | None, typer.Option("--hermes-profile")] = None,
) -> None:
    """Run paired live missions with identical frontier generation across control planes."""
    _load_cli_credentials(env_file, hermes_profile)
    try:
        summary = run_manifest(manifest, output_dir=output_dir, repeats=repeats, seed=seed)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    console.print_json(data=summary)


@app.command("benchmark-report")
def benchmark_report(
    results: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Aggregate an existing benchmark results.jsonl without rerunning providers."""
    console.print_json(data=aggregate_records(read_jsonl(results)))


@app.command("intelligence-plan")
def intelligence_plan(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, readable=True)],
    capability: Annotated[str, typer.Option("--capability")] = "generation",
    required_vsr: Annotated[float | None, typer.Option("--required-vsr", min=0.0, max=1.0)] = None,
) -> None:
    """Plan one minimum-sufficient intelligence selection without provider calls."""
    cfg = AppConfig.load(config)
    fabric = cfg.intelligence_fabric()
    if fabric is None:
        raise typer.BadParameter("intelligence_fabric is not enabled in this configuration")
    threshold = cfg.required_vsr(capability) if required_vsr is None else float(required_vsr)
    try:
        bid = fabric.select(capability=capability, required_vsr=threshold)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    console.print_json(
        data={
            "capability": capability,
            "required_vsr": threshold,
            "selected": {
                "strategy_id": bid.strategy_id,
                "source": bid.source,
                "predicted_vsr": bid.predicted_vsr,
                "estimated_cost_usd": bid.estimated_cost_usd,
                "estimated_latency_ms": bid.estimated_latency_ms,
                "uncertainty": bid.uncertainty,
                "risk": bid.risk,
                "frontier_input_tokens": bid.frontier_input_tokens,
                "frontier_output_tokens": bid.frontier_output_tokens,
                "model_alias": bid.metadata.get("model_alias"),
            },
            "frontier_budget_remaining": fabric.frontier_budget.remaining,
        }
    )


@app.command("proof-inspect")
def proof_inspect(
    proof_graph: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Inspect persisted proof claims and freshness without executing work."""
    graph = ProofGraph.load(proof_graph)
    payload = graph.to_dict()
    console.print_json(data={
        "telemetry": graph.telemetry(),
        "claims": payload["claims"],
    })


@app.command("verification-plan")
def verification_plan(
    config: Annotated[Path, typer.Option("--config", "-c", exists=True, readable=True)],
) -> None:
    """Plan the cheapest configured verification portfolio without executing commands."""
    cfg = AppConfig.load(config)
    optimizer, requirement = cfg.verification_portfolio()
    if optimizer is None or requirement is None:
        raise typer.BadParameter("verification_fabric is not enabled in this configuration")
    try:
        plan = optimizer.plan(requirement)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    console.print_json(data={
        "requirement": {
            "required_assurance": requirement.required_assurance,
            "required_detection": requirement.required_detection,
            "defect_probability": requirement.defect_probability,
            "impact_usd": requirement.impact_usd,
            "max_cost_usd": requirement.max_cost_usd,
        },
        "plan": plan.to_dict(),
    })


@app.command("learning-demo")
def learning_demo() -> None:
    """Run an offline v1.4 learning-ratchet and proof-gated speculation demonstration."""
    compiler = DecisionDistillationCompiler(min_observations=4, min_teacher_vsr=0.75)
    for index in range(4):
        compiler.observe(
            DecisionObservation(
                observation_id=f"demo-{index}",
                decision_family="scope",
                teacher_strategy="frontier-teacher",
                teacher_decision="src/target.py",
                verified_outcome=True,
                estimated_cost_usd=0.01,
            )
        )
    candidate = compiler.compile_candidate(
        decision_family="scope",
        candidate_strategy="jev-scope",
        candidate_cost_usd=0.0001,
    )
    if candidate is None:
        raise typer.Exit(code=2)

    replay = CounterfactualReplay()
    for index in range(4):
        replay.record(
            ShadowObservation(
                decision_id=f"shadow-{index}",
                incumbent_strategy="frontier-teacher",
                candidate_strategy="jev-scope",
                incumbent_decision="src/target.py",
                candidate_decision="src/target.py",
                incumbent_verified_outcome=True,
                candidate_verified_outcome=True,
                incumbent_cost_usd=0.01,
                candidate_cost_usd=0.0001,
            )
        )
    cf = replay.evaluate(candidate_strategy="jev-scope")
    candidate = candidate.with_metrics(
        replay_runs=4,
        shadow_runs=4,
        experimental_runs=4,
        holdout_runs=4,
        holdout_successes=4,
        candidate_vsr=cf.candidate_vsr,
        candidate_fcr=0.0,
        candidate_cpvo=cf.candidate_cpvo,
    )
    ratchet = LearningRatchet(candidate)
    for state in (
        LearningState.REPLAYED,
        LearningState.SHADOWED,
        LearningState.EXPERIMENTAL,
        LearningState.HOLDOUT_VERIFIED,
    ):
        ratchet.transition(state)
    policy = PromotionPolicy(vsr_noninferiority_margin=0.01, max_fcr=0.0)
    promotion = policy.evaluate(ratchet.candidate)
    if promotion.promote:
        ratchet.transition(LearningState.PROMOTED)

    correlations = VerifierCorrelationMatrix()
    correlations.set("unit", "integration", 0.6)
    methods = [
        VerificationMethod("unit", 2, 0.80, 0.01, 20, "pytest unit"),
        VerificationMethod("integration", 3, 0.75, 0.02, 40, "pytest integration"),
    ]
    verifier = VerificationPortfolioOptimizer(methods, correlations=correlations)
    plan = verifier.plan(VerificationRequirement(required_assurance=3, required_detection=0.84))

    graph = ProofGraph()
    proof = EvidenceClaim.mint(
        subject="node:demo",
        predicate="verified",
        verifier="sentinel",
        method="demo",
        verdict=True,
    )
    graph.add_claim(proof)
    with tempfile.TemporaryDirectory(prefix="jev-learning-demo-") as tmp:
        root = Path(tmp)
        (root / "artifact.txt").write_text("before\n", encoding="utf-8")
        with SpeculativeFileTransaction(root) as tx:
            tx.stage_write("artifact.txt", "after\n")
            before = (root / "artifact.txt").read_text(encoding="utf-8").strip()
            committed = tx.commit(graph, prerequisite_claim_ids=(proof.claim_id,))
            after = (root / "artifact.txt").read_text(encoding="utf-8").strip()

    console.print_json(data={
        "mode": "offline-v1.4-learning-proof-demo",
        "learning_state": ratchet.candidate.state.value,
        "promotion": promotion.promote,
        "counterfactual_coverage": cf.coverage,
        "candidate_vsr": cf.candidate_vsr,
        "candidate_cpvo": cf.candidate_cpvo,
        "verification_detection": plan.combined_detection,
        "verification_methods": [method.method_id for method in plan.methods],
        "speculative_before_commit": before,
        "speculative_after_commit": after,
        "committed_files": committed,
    })


@app.command("shadow-inspect")
def shadow_inspect(
    log_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Summarize shadow-decision missions without imputing unobserved outcomes."""
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    observable = [row for row in rows if bool(row.get("candidate_outcome_observable"))]
    incumbent_verified = sum(1 for row in rows if bool(row.get("incumbent_verified_outcome")))
    candidate_verified = sum(1 for row in observable if bool(row.get("candidate_verified_outcome")))
    calls = sum(int(row.get("shadow_calls", 0) or 0) for row in rows)
    agreements = sum(int(row.get("agreements", 0) or 0) for row in rows)
    console.print_json(data={
        "missions": len(rows),
        "shadow_calls": calls,
        "agreement_rate": (agreements / calls) if calls else 0.0,
        "counterfactual_observable_missions": len(observable),
        "counterfactual_coverage": (len(observable) / len(rows)) if rows else 0.0,
        "incumbent_vsr": (incumbent_verified / len(rows)) if rows else None,
        "candidate_vsr_observed_only": (candidate_verified / len(observable)) if observable else None,
        "note": "candidate VSR excludes divergent/unobservable counterfactual missions",
    })


@app.command("promotion-inspect")
def promotion_inspect(
    registry_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Inspect evidence-gated promoted routes."""
    registry = PromotionRegistry.load(registry_path)
    console.print_json(data=registry.to_dict())


@app.command("effect-demo")
def effect_demo() -> None:
    """Run an offline PREPARE→AUTHORIZE→EXECUTE→VERIFY→COMMIT effect proof."""
    with tempfile.TemporaryDirectory(prefix="jev-effect-demo-") as tmp:
        root = Path(tmp)
        target = root / "artifact.txt"
        target.write_text("before\n", encoding="utf-8")
        tx = FileEffectTransaction(root)
        proposal = tx.prepare("artifact.txt", "after\n", expected_effect="artifact content changes")
        tx.authorize(principal="demo:operator", authority_ref="lease:demo")
        tx.speculate()
        before_execute = target.read_text(encoding="utf-8").strip()
        tx.execute()
        readback = tx.readback()
        graph = ProofGraph()
        claim = EvidenceClaim.mint(
            subject=f"sha256:{proposal.proposed_sha256}",
            predicate="effect_verified",
            verifier="demo:independent-readback",
            method="exact-byte-readback",
            verdict=readback.matches_expected,
            dependencies={"target": proposal.proposed_sha256},
        )
        graph.add_claim(claim)
        tx.verify(graph, claim_ids=[claim.claim_id])
        receipt = tx.commit()
        console.print_json(data={
            "mode": "offline-v1.5-effect-transaction-demo",
            "before_execute": before_execute,
            "after_commit": target.read_text(encoding="utf-8").strip(),
            "proposal": {
                "action_id": proposal.action_id,
                "kind": proposal.kind,
                "target": proposal.target,
                "preimage_sha256": proposal.preimage_sha256,
                "proposed_sha256": proposal.proposed_sha256,
            },
            "receipt": {
                "state": receipt.state,
                "readback_sha256": receipt.readback_sha256,
                "verifier_claim_ids": list(receipt.verifier_claim_ids),
            },
        })



@app.command("distributed-demo")
def distributed_demo() -> None:
    """Run the offline v1.7 distributed/authority/failover vertical slice."""
    now = datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)
    authority = AuthorityLedger()
    root = authority.issue_root(
        authority_ref="human:demo",
        principal="steward",
        scopes={"mission.execute"},
        budget_usd=5.0,
        expires_at=now + timedelta(hours=1),
        delegation_depth=1,
    )
    graph = MissionGraph([
        MissionNode("a", metadata={"required_capabilities": ["python"]}),
        MissionNode("b", metadata={"required_capabilities": ["python"]}),
        MissionNode(
            "join",
            dependencies=("a", "b"),
            speculative_allowed=True,
            metadata={"required_capabilities": ["python"]},
        ),
    ])
    runtime = DistributedMissionRuntime(graph, LeaseManager(), authority, max_parallel_workers=2)
    a = runtime.dispatch(
        "a", worker_id="worker:a", authority_grant_id=root.grant_id,
        capabilities={"python"}, ttl=timedelta(minutes=5), now=now,
    )
    b = runtime.dispatch(
        "b", worker_id="worker:b", authority_grant_id=root.grant_id,
        capabilities={"python"}, ttl=timedelta(minutes=5), now=now,
    )
    runtime.mark_verified("a", a.lease_id, a.fencing_token, now=now)
    runtime.commit("a", a.lease_id, a.fencing_token, now=now)
    join = runtime.dispatch(
        "join", worker_id="worker:join", authority_grant_id=root.grant_id,
        capabilities={"python"}, ttl=timedelta(minutes=5), now=now,
    )
    runtime.mark_verified("b", b.lease_id, b.fencing_token, now=now)
    runtime.commit("b", b.lease_id, b.fencing_token, now=now)
    runtime.mark_verified("join", join.lease_id, join.fencing_token, now=now)
    runtime.commit("join", join.lease_id, join.fencing_token, now=now)

    routes = ProviderFailoverRouter([
        ProviderRoute("primary", "provider-a", "model-x", "logical-x", priority=1),
        ProviderRoute("secondary", "provider-b", "model-x", "logical-x", priority=2),
    ])
    def operation(route: ProviderRoute) -> str:
        if route.route_id == "primary":
            raise ProviderFailure(FailureKind.TRANSIENT, "synthetic transient outage")
        return "provider-ok"
    failover = routes.execute(operation, logical_model="logical-x")

    campaign = LearningCampaign(
        LearningCandidate("demo-candidate", "safe_to_run", "frontier", "jev"),
        PromotionPolicy(max_fcr=0.0),
        min_holdout_trials=3,
        noninferiority_margin=0.1,
    )
    auto = AutoCampaignController(campaign, AutoCampaignSchedule(1, 1, 1))
    for _ in range(3):
        auto.record_pair(
            incumbent=OutcomeSample(True, False, 0.10),
            candidate=OutcomeSample(True, False, 0.001),
        )

    signer = ReceiptSigner(key_id="demo-key", secret=b"v1.7-demo-key-material-not-production"[:32])
    signed = signer.sign({"node_id": "join", "state": graph.nodes["join"].state.value})
    signature_valid = ReceiptVerifier({"demo-key": b"v1.7-demo-key-material-not-production"[:32]}).verify(signed)

    console.print_json(data={
        "mode": "offline-v1.7-distributed-verified-intelligence-demo",
        "join_state": graph.nodes["join"].state.value,
        "lease_fencing": {"a": a.fencing_token, "b": b.fencing_token, "join": join.fencing_token},
        "authority_chain_hash": root.chain_hash,
        "provider_route": failover.route.route_id,
        "provider_attempts": [attempt.outcome for attempt in failover.attempts],
        "learning_campaign_state": campaign.state.value,
        "signed_receipt_valid": signature_valid,
        "truth_boundary": "demo uses synthetic providers, synthetic outcomes, and an in-process HMAC key",
    })


@app.command("sync-models")
def sync_models(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("configs/litellm-model-catalog.json"),
    source: Annotated[str, typer.Option("--source")] = (
        "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    ),
) -> None:
    """Fetch LiteLLM's data-driven model/provider catalog."""
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(source, timeout=30) as response:  # noqa: S310
            raw = response.read()
        parsed = json.loads(raw)
    except Exception as exc:
        console.print(f"[red]Catalog sync failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    if not isinstance(parsed, dict) or not parsed:
        console.print("[red]Catalog is not a non-empty JSON object.[/red]")
        raise typer.Exit(code=2)
    output.write_bytes(raw)
    console.print(
        f"Saved {len(parsed)} entries → {output} "
        f"(sha256:{hashlib.sha256(raw).hexdigest()})"
    )


@app.command("export-litellm-catalog")
def export_litellm_catalog(
    output: Path = typer.Option(Path("litellm-model-catalog.json"), "--output", "-o"),
) -> None:
    """Export the model catalog exposed by the installed LiteLLM version."""
    try:
        import litellm  # type: ignore
    except ImportError as exc:
        raise typer.BadParameter(
            "LiteLLM is optional. Install `aftergraph-jev-engineering[all-providers]` first."
        ) from exc
    catalog = getattr(litellm, "model_cost", None) or getattr(litellm, "model_cost_map", None)
    if not isinstance(catalog, dict):
        raise typer.BadParameter("Installed LiteLLM does not expose a model catalog mapping")
    output.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")
    console.print(f"Wrote {len(catalog)} model records to {output}")


@app.command()
def run(
    task: Annotated[str, typer.Argument(help="Coding task in natural language")],
    workspace: Annotated[
        Path, typer.Option("--workspace", "-w", exists=True, file_okay=False)
    ] = Path("."),
    config: Annotated[
        Path, typer.Option("--config", "-c", exists=True, readable=True)
    ] = Path("jev-one.yaml"),
    verify: Annotated[str | None, typer.Option("--verify")] = None,
    interactive_approvals: Annotated[
        bool, typer.Option("--interactive-approvals")
    ] = False,
    env_file: Annotated[Path | None, typer.Option("--env-file")] = None,
    hermes_profile: Annotated[str | None, typer.Option("--hermes-profile")] = None,
) -> None:
    """Run one governed coding mission. VERIFIED requires fresh verifier evidence."""
    _load_cli_credentials(env_file, hermes_profile)
    cfg = AppConfig.load(config)
    runtime = cfg.runtime
    verify_command = verify or str(runtime.get("verify_command") or "python -m pytest -q")
    backend = cfg.decision_backend()
    decision_cfg = cfg.raw.get("decision") or cfg.raw.get("jev") or {}
    fabric = cfg.intelligence_fabric()
    engine: Any = DecisionEngine(backend, decision_model=decision_cfg.get("model"))
    shadow_cfg = cfg.shadow_decision_backend()
    if shadow_cfg is not None:
        shadow_backend, shadow_meta = shadow_cfg
        candidate_engine = DecisionEngine(shadow_backend, decision_model=shadow_meta.get("model"))
        engine = ShadowDecisionEngine(
            incumbent=engine,
            candidate=candidate_engine,
            incumbent_strategy=str(shadow_meta["incumbent_strategy"]),
            candidate_strategy=str(shadow_meta["candidate_strategy"]),
            log_path=workspace / ".jev-one" / "shadow-decisions.jsonl",
            promotion_registry=(fabric.promotion_registry if fabric is not None else None),
        )

    def approve(tool: str, arguments: dict[str, object], reason: str) -> bool:
        if not interactive_approvals:
            return False
        safe_summary = {
            "tool": tool,
            "argument_keys": sorted(arguments.keys()),
            "reason": reason,
        }
        console.print_json(data=safe_summary)
        return typer.confirm("Approve this consequential action?", default=False)

    audit_path = workspace / ".jev-one" / "audit.jsonl"
    context_compiler, context_token_budget = cfg.context_compiler()
    verification_optimizer, verification_requirement = cfg.verification_portfolio()
    agent = CodingAgent(
        workspace=workspace,
        decisions=engine,
        registry=cfg.registry,
        provider_factory=cfg.provider_factory(),
        verify_command=verify_command,
        max_turns=int(runtime.get("max_turns", 24)),
        scope_top_k=int(runtime.get("scope_top_k", 8)),
        # This executable intentionally has no non-frontier coding mode.
        frontier_required=True,
        command_mode=str(runtime.get("command_mode", "verify_only")),
        audit_path=audit_path,
        retention_every=int(runtime.get("retention_every", 6)),
        loop_check_every=int(runtime.get("loop_check_every", 4)),
        policy=dict(runtime.get("policy") or {}),
        approval_handler=approve if interactive_approvals else None,
        intelligence_fabric=fabric,
        generation_required_vsr=cfg.required_vsr("generation"),
        context_compiler=context_compiler,
        context_token_budget=context_token_budget,
        proof_graph_path=workspace / ".jev-one" / "proof-graph.json",
        verification_optimizer=verification_optimizer,
        verification_requirement=verification_requirement,
    )
    result = agent.run(task)
    console.print_json(
        data={
            "status": result.status.value,
            "trace_id": result.trace_id,
            "model_alias": result.model_alias,
            "model": result.model,
            "turns": result.turns,
            "verification_exit_code": result.verification_exit_code,
            "verification_output_tail": result.verification_output[-4000:],
            "final_text": result.final_text,
            "message": result.message,
            "audit": result.audit_path,
            "proof_graph": str(workspace / ".jev-one" / "proof-graph.json"),
            "metrics": result.metrics,
        }
    )
    if result.status.value != "verified":
        raise typer.Exit(code=2)


@app.command()
def demo() -> None:
    """Run a zero-network vertical proof with scripted typed decisions and coding turns."""
    with tempfile.TemporaryDirectory(prefix="jev-one-demo-") as tmp:
        workspace = Path(tmp)
        (workspace / "calc.py").write_text(
            "def add(a, b):\n    return a - b\n", encoding="utf-8"
        )
        (workspace / "test_calc.py").write_text(
            "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )
        decisions = ScriptedDecisionBackend(
            [
                {
                    "answers": {
                        "f0": {"type": "score", "score": 4.0, "confidence": 1.0},
                        "f1": {"type": "score", "score": 4.0, "confidence": 1.0},
                    }
                },
                {
                    "answers": {
                        "model": {
                            "type": "choice",
                            "choice": "offline-frontier-contract-simulator",
                            "confidence": 1.0,
                        }
                    }
                },
                {
                    "answers": {
                        "destructive": {"type": "noul", "noul": 0.01},
                        "needs_human": {"type": "noul", "noul": 0.01},
                    }
                },
                {
                    "answers": {
                        "destructive": {"type": "noul", "noul": 0.01},
                        "needs_human": {"type": "noul", "noul": 0.01},
                    }
                },
                {
                    "answers": {
                        "done": {"type": "noul", "noul": 0.99},
                        "judgeable": {"type": "noul", "noul": 0.99},
                    }
                },
            ]
        )
        registry = ModelRegistry.from_dict(
            {
                "models": {
                    "offline-frontier-contract-simulator": {
                        "provider": "mock",
                        "model": "deterministic-scripted-model",
                        "tier": "frontier",
                        "transport": "mock",
                    }
                }
            }
        )
        provider = ScriptedProviderFactory(
            turns=[
                {
                    "tool_calls": [
                        {
                            "id": "edit-1",
                            "name": "write_file",
                            "arguments": {
                                "path": "calc.py",
                                "content": "def add(a, b):\n    return a + b\n",
                            },
                        }
                    ]
                },
                {
                    "tool_calls": [
                        {
                            "id": "test-1",
                            "name": "run_command",
                            "arguments": {"command": "python -m pytest -q"},
                        }
                    ]
                },
                {"text": "Candidate complete; outer verifier must decide."},
            ]
        )
        result = CodingAgent(
            workspace=workspace,
            decisions=DecisionEngine(decisions),
            registry=registry,
            provider_factory=provider,
            verify_command="python -m pytest -q",
            max_turns=6,
            retention_every=0,
            loop_check_every=0,
            audit_path=workspace / ".jev-one" / "audit.jsonl",
        ).run("Fix add() so the test passes")
        console.print_json(
            data={
                "mode": "offline-contract-proof-not-live-jev-or-frontier-api",
                "status": result.status.value,
                "verification_exit_code": result.verification_exit_code,
                "verification_output": result.verification_output.strip(),
                "edited_source": (workspace / "calc.py").read_text(encoding="utf-8"),
                "typed_decision_calls": len(decisions.requests),
            }
        )
        if result.status.value != "verified":
            raise typer.Exit(code=2)


@app.command("secret-status")
def secret_status(
    env_file: Annotated[Path | None, typer.Option("--env-file")] = None,
    hermes_profile: Annotated[str | None, typer.Option("--hermes-profile")] = None,
    fingerprint: Annotated[bool, typer.Option("--fingerprint")] = False,
) -> None:
    """Report credential presence/source without printing secret values."""
    if env_file is not None and hermes_profile:
        raise typer.BadParameter("Use either --env-file or --hermes-profile, not both")
    if hermes_profile:
        env_file = hermes_profile_env(hermes_profile)
    resolver = SecretResolver(env_file=env_file)
    rows = [
        resolver.status("TYPESAFE_API_KEY", include_fingerprint=fingerprint).to_dict(),
        resolver.status("DIALAGRAM_API_KEY", include_fingerprint=fingerprint).to_dict(),
    ]
    console.print_json(data={"secrets": rows, "github_actions": os.environ.get("GITHUB_ACTIONS") == "true"})


@app.command("live-smoke")
def live_smoke(
    env_file: Annotated[Path | None, typer.Option("--env-file")] = None,
    hermes_profile: Annotated[str | None, typer.Option("--hermes-profile")] = None,
    typesafe_base_url: str = typer.Option("https://api.typesafe.ai"),
    dialagram_base_url: str = typer.Option("https://dialagram.me/router/v1"),
    dialagram_model: str = typer.Option("qwen-3.8-max-thinking"),
) -> None:
    """Run minimal authenticated provider checks with redacted output."""
    if env_file is not None and hermes_profile:
        raise typer.BadParameter("Use either --env-file or --hermes-profile, not both")
    if hermes_profile:
        env_file = hermes_profile_env(hermes_profile)
    resolver = SecretResolver(env_file=env_file)
    try:
        typesafe_key = resolver.get("TYPESAFE_API_KEY")
        dialagram_key = resolver.get("DIALAGRAM_API_KEY")
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=3) from exc
    report = run_provider_smoke(
        typesafe_api_key=typesafe_key,
        dialagram_api_key=dialagram_key,
        typesafe_base_url=typesafe_base_url,
        dialagram_base_url=dialagram_base_url,
        dialagram_model=dialagram_model,
    )
    console.print_json(data=report)
    if not report["ok"]:
        raise typer.Exit(code=4)


@app.command("networked-demo")
def networked_demo() -> None:
    """Run a zero-network v1.8 identity/lease/proof/quorum/circuit-breaker vertical."""
    now = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="jev-v18-networked-") as tmp:
        root = Path(tmp)
        issuer = Ed25519WorkloadIssuer.generate(key_id="wid-demo", principal="worker:demo")
        identity_verifier = WorkloadIdentityVerifier({issuer.key_id: issuer.public_key_bytes()})
        authority = AuthorityLedger()
        grant = authority.issue_root(
            authority_ref="human:demo",
            principal="worker:demo",
            scopes={"mission.execute"},
            budget_usd=1.0,
            expires_at=now + timedelta(hours=1),
            delegation_depth=0,
        )
        graph = MissionGraph([MissionNode("n1", metadata={"required_capabilities": ["python"]})])
        workers = WorkerDirectory()
        workers.register(WorkerEndpoint(
            "demo", "habitat:demo", "aftergraph://demo", frozenset({"python"}), issuer.key_id, now,
        ))
        context = WorksExecutionContext.create(mission_id="m-demo", node_id="n1", principal="worker:demo")
        assertion = issuer.issue(
            audience="aftergraph-trust-gateway",
            execution_context_id=context.execution_context_id,
            ttl=timedelta(minutes=5),
            now=now,
        )
        runtime = NetworkedMissionRuntime(
            graph=graph,
            leases=SqliteLeaseStore(root / "leases.db"),
            authority=authority,
            trust_gateway=TrustGatewayValidator(identity_verifier=identity_verifier, authority=authority),
            workers=workers,
            proof_store=SqliteProofGraphStore(root / "proof.db"),
            proof_graph_id="mission:m-demo",
        )
        dispatch = runtime.dispatch(
            node_id="n1", worker_id="demo", grant_id=grant.grant_id,
            context=context, assertion=assertion, ttl=timedelta(minutes=5), now=now,
        )
        claims = []
        revision = dispatch.proof_revision
        for verifier_name in ("sentinel:a", "sentinel:b"):
            claim = EvidenceClaim.mint(
                subject="node:n1", predicate="verified", verifier=verifier_name,
                method="independent", verdict=True,
            )
            revision = runtime.publish_claim(claim, expected_revision=revision)
            claims.append(claim.claim_id)
        proof, _ = runtime.proof_store.read(runtime.proof_graph_id)
        quorum = QuorumVerifier(QuorumPolicy(min_positive=2)).evaluate(
            proof, subject="node:n1", predicate="verified",
        )
        if not quorum.accepted:
            raise typer.Exit(code=3)
        runtime.mark_verified(
            "n1", dispatch.lease.lease_id, dispatch.lease.fencing_token,
            now=now, required_claim_ids=tuple(claims),
        )
        runtime.commit("n1", dispatch.lease.lease_id, dispatch.lease.fencing_token, now=now)

        signer = Ed25519ReceiptSigner.generate(key_id="receipt-demo")
        receipt = signer.sign({
            "mission_id": "m-demo",
            "node_id": "n1",
            "execution_context_id": context.execution_context_id,
            "state": "committed",
        })
        public_receipt_valid = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()}).verify(receipt)

        clock = [100.0]
        breakers = CircuitBreakerRegistry(failure_threshold=1, recovery_seconds=30, clock=lambda: clock[0])
        router = ProviderFailoverRouter([
            ProviderRoute("p1", "provider-a", "m", "logical", priority=1),
            ProviderRoute("p2", "provider-b", "m", "logical", priority=2),
        ], circuit_breakers=breakers)
        failover = router.execute(
            lambda route: (_ for _ in ()).throw(ProviderFailure(FailureKind.TRANSIENT, "synthetic")) if route.route_id == "p1" else "ok",
            logical_model="logical",
        )
        console.print_json(data={
            "mode": "offline-v1.8-networked-reference-demo",
            "worker": dispatch.endpoint_uri,
            "execution_context_id": context.execution_context_id,
            "lease_fencing_token": dispatch.lease.fencing_token,
            "proof_revision": revision,
            "quorum_accepted": quorum.accepted,
            "positive_verifiers": list(quorum.positive_verifiers),
            "mission_state": graph.nodes["n1"].state.value,
            "public_receipt_valid": public_receipt_valid,
            "provider_route_after_failure": failover.route.route_id,
            "network_transport_executed": False,
        })


@app.command("transport-demo")
def transport_demo() -> None:
    """Run a zero-network v1.9 signed node-transport/proof-replication vertical."""
    coordinator = Ed25519ReceiptSigner.generate(key_id="coord-demo")
    worker = Ed25519ReceiptSigner.generate(key_id="worker-demo")
    verifier = Ed25519ReceiptVerifier({
        coordinator.key_id: coordinator.public_key_bytes(),
        worker.key_id: worker.public_key_bytes(),
    })
    cp = NodeProtocol(signer=coordinator, verifier=verifier)
    wp = NodeProtocol(signer=worker, verifier=verifier)
    endpoint = InMemoryNodeEndpoint(
        node_id="worker:demo",
        protocol=wp,
        handler=lambda operation, payload: {
            "operation": operation,
            "candidate_sha": payload.get("candidate_sha"),