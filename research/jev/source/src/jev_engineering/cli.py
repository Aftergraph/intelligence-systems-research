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
            "verdict": "PASS",
        },
    )
    client = RemoteWorkerClient(
        sender_id="coordinator:demo", worker_id="worker:demo",
        protocol=cp, send=endpoint.handle,
    )
    result = client.call("verify_candidate", {"candidate_sha": "sha256:demo"})
    with tempfile.TemporaryDirectory(prefix="jev-v19-transport-") as tmp:
        store = SqliteProofGraphStore(Path(tmp) / "replica.db")
        repl = ProofReplicator(store)
        claim = EvidenceClaim.mint(
            subject="sha256:demo", predicate="verified", verifier="worker:demo",
            method="remote_signed_transport", verdict=result.ok and result.payload.get("verdict") == "PASS",
        )
        revision = repl.apply(repl.export_delta("mission:transport-demo", base_revision=0, claims=[claim]))
        graph, _ = store.read("mission:transport-demo")
        console.print_json(data={
            "mode": "offline-v1.9-signed-transport-demo",
            "request_authenticated": result.ok,
            "worker": result.worker_id,
            "operation": result.payload.get("operation"),
            "candidate_sha": result.payload.get("candidate_sha"),
            "proof_revision": revision,
            "proof_accepted": graph.accepts((claim.claim_id,)),
            "shell_authority_exposed": False,
            "network_socket_executed": False,
        })

@app.command("v2-demo")
def v2_demo() -> None:
    """Run a real loopback mTLS v2.0 distributed-fabric vertical."""
    import httpx

    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="jev-v20-fabric-") as tmp:
        root = Path(tmp)
        # Application signing keys are independent of TLS keys.
        coordinator_signer = Ed25519ReceiptSigner.generate(key_id="coord-sign")
        worker_signer = Ed25519ReceiptSigner.generate(key_id="worker-sign")
        receipt_verifier = Ed25519ReceiptVerifier({
            "coord-sign": coordinator_signer.public_key_bytes(),
            "worker-sign": worker_signer.public_key_bytes(),
        })
        coordinator_protocol = NodeProtocol(signer=coordinator_signer, verifier=receipt_verifier)
        worker_protocol = NodeProtocol(signer=worker_signer, verifier=receipt_verifier)

        # Reference mTLS material. Production must use managed workload identity.
        ca = EphemeralCertificateAuthority()
        server_identity = ca.issue(
            common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True,
        )
        client_identity = ca.issue(common_name="coordinator:demo", client=True)
        s_cert, s_key, ca_file = server_identity.write(root / "server-tls", prefix="server")
        c_cert, c_key, _ = client_identity.write(root / "client-tls", prefix="client")

        leases = SqliteLeaseStore(root / "leases.db")
        lease = leases.issue(
            node_id="node:demo", worker_id="coordinator:demo", authority_grant_id="grant:demo",
            capabilities={"verify_candidate"}, ttl=timedelta(minutes=5), now=now,
        )

        # The remote verifier command is owned/configured by the worker, not supplied by the caller.
        verifier_workspace = root / "verifier-workspace"
        verifier_workspace.mkdir()
        (verifier_workspace / "candidate.py").write_text("VALUE = 42\n", encoding="utf-8")
        candidate_sha = "sha256:" + __import__("jev_engineering.proof_graph", fromlist=["workspace_tree_hash"]).workspace_tree_hash(verifier_workspace)

        operations = OperationRegistry()
        LeaseControlService(leases).register(operations)
        PreconfiguredVerifierCapability(
            workspace=verifier_workspace,
            command=(__import__("sys").executable, "-c", "import candidate; assert candidate.VALUE == 42"),
            verifier_name="sentinel:worker",
        ).register(operations)
        gateway = NodeGateway(node_id="worker:demo", protocol=worker_protocol, operations=operations)
        server_context = server_mtls_context(
            ca_file=str(ca_file), certificate_file=str(s_cert), private_key_file=str(s_key),
        )

        with NodeGatewayServer(gateway=gateway, ssl_context=server_context) as server:
            _, port = server.address
            client_context = client_mtls_context(
                ca_file=str(ca_file), certificate_file=str(c_cert), private_key_file=str(c_key),
            )
            with httpx.Client(verify=client_context, timeout=5.0) as http:
                transport = HttpNodeTransport(client=http)
                remote = RemoteWorkerClient(
                    sender_id="coordinator:demo", worker_id="worker:demo", protocol=coordinator_protocol,
                    send=lambda message: transport.post(
                        f"https://localhost:{port}/v1/node/call", message,
                    ),
                )
                heartbeat = remote.call("lease_heartbeat", {
                    "lease_id": lease.lease_id,
                    "fencing_token": lease.fencing_token,
                })
                order = RemoteWorkOrder(
                    mission_id="mission:v2-demo", node_id="node:demo",
                    execution_context_id="ctx:v2-demo", lease_id=lease.lease_id,
                    fencing_token=lease.fencing_token, authority_grant_id="grant:demo",
                    candidate_sha=candidate_sha,
                )
                receipt = RemoteExecutionCoordinator(remote).execute(order)
                journal_head = validate_execution_journal(receipt)

        proof_store = SqliteProofGraphStore(root / "proof.db")
        base_replication = ProofReplicator(proof_store)
        proof_signer = Ed25519ReceiptSigner.generate(key_id="worker-proof")
        signed_replication = SignedProofReplicator(
            base_replication,
            signer=proof_signer,
            verifier=Ed25519ReceiptVerifier({"worker-proof": proof_signer.public_key_bytes()}),
        )
        claim_a = EvidenceClaim.mint(
            subject=candidate_sha, predicate="verified", verifier="sentinel:worker",
            method="remote_mtls", verdict=receipt.passed,
            metadata={"trust_domain": "worker-node", "journal_head_sha256": journal_head},
        )
        signed_delta = signed_replication.sign(
            base_replication.export_delta("mission:v2-demo", base_revision=0, claims=[claim_a])
        )
        revision = signed_replication.verify_and_apply(
            signed_delta, expected_signer_key_id="worker-proof",
        )
        graph, _ = proof_store.read("mission:v2-demo")
        claim_b = EvidenceClaim.mint(
            subject=candidate_sha, predicate="verified", verifier="sentinel:coordinator",
            method="independent_local", verdict=True,
            metadata={"trust_domain": "coordinator-node"},
        )
        graph.add_claim(claim_b)
        proof_store.compare_and_swap("mission:v2-demo", expected_revision=revision, graph=graph)
        graph, revision = proof_store.read("mission:v2-demo")
        quorum = DiversityQuorumVerifier(
            DiversityQuorumPolicy(min_positive=2, min_trust_domains=2)
        ).evaluate(graph, subject=candidate_sha, predicate="verified")

        console.print_json(data={
            "mode": "v2.0-real-loopback-mtls-fabric-demo",
            "network_socket_executed": True,
            "tls": "mutual",
            "application_message_signatures": "Ed25519",
            "mtls_sender_binding": True,
            "lease_heartbeat": heartbeat.ok,
            "fencing_token": lease.fencing_token,
            "remote_verdict": receipt.verdict,
            "execution_journal_events": len(receipt.evidence.get("execution_events") or []),
            "execution_journal_head_sha256": journal_head,
            "signed_proof_delta": True,
            "proof_revision": revision,
            "diverse_quorum_accepted": quorum.accepted,
            "trust_domains": list(quorum.positive_trust_domains),
            "physical_multi_machine_executed": False,
            "truth_boundary": (
                "real TCP+mTLS loopback transport executed; no claim of Jonas-Lenovo/VDS deployment "
                "or live TypeSafe/Dialagram provider success"
            ),
        })
        if not (heartbeat.ok and receipt.passed and journal_head and quorum.accepted):
            raise typer.Exit(code=3)


@app.command("v21-demo")
def v21_demo() -> None:
    """Run two independent mTLS verifier nodes with fenced work and streamed journals."""
    import httpx
    from .proof_graph import workspace_tree_hash
    from .remote_control import FencedPreconfiguredVerifierCapability

    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="jev-v21-multinode-") as tmp:
        root = Path(tmp)
        ca = EphemeralCertificateAuthority()
        coord_tls = ca.issue(common_name="coordinator:demo", client=True)
        c_cert, c_key, ca_file = coord_tls.write(root / "coord-tls", prefix="coord")
        coordinator_signer = Ed25519ReceiptSigner.generate(key_id="coord-sign")
        worker_signers = {
            "worker:lenovo": Ed25519ReceiptSigner.generate(key_id="lenovo-sign"),
            "worker:vds": Ed25519ReceiptSigner.generate(key_id="vds-sign"),
        }
        key_map = {"coord-sign": coordinator_signer.public_key_bytes()}
        key_map.update({s.key_id: s.public_key_bytes() for s in worker_signers.values()})
        verifier = Ed25519ReceiptVerifier(key_map)
        coordinator_protocol = NodeProtocol(signer=coordinator_signer, verifier=verifier)
        client_context = client_mtls_context(
            ca_file=str(ca_file), certificate_file=str(c_cert), private_key_file=str(c_key),
        )

        workspace_template = root / "candidate"
        workspace_template.mkdir()
        (workspace_template / "candidate.py").write_text("VALUE = 42\n", encoding="utf-8")
        candidate_sha = "sha256:" + workspace_tree_hash(workspace_template)

        servers = []
        http_clients = []
        targets = []
        remote_clients = {}
        stream_ids = {}
        try:
            for worker_id, trust_domain in (("worker:lenovo", "lenovo"), ("worker:vds", "vds")):
                node_dir = root / worker_id.replace(":", "-")
                node_dir.mkdir()
                ws = node_dir / "workspace"
                shutil.copytree(workspace_template, ws)
                lease_store = SqliteLeaseStore(node_dir / "leases.db")
                lease = lease_store.issue(
                    node_id="node:verify", worker_id="coordinator:demo",
                    authority_grant_id="grant:verify", capabilities={"verify_candidate"},
                    ttl=timedelta(minutes=5), now=now,
                )
                streams = JournalStreamRegistry()
                ops = OperationRegistry()
                LeaseControlService(lease_store).register(ops)
                JournalStreamService(streams).register(ops)
                FencedPreconfiguredVerifierCapability(
                    workspace=ws,
                    command=(__import__("sys").executable, "-c", "import candidate; assert candidate.VALUE == 42"),
                    verifier_name=f"sentinel:{trust_domain}", leases=lease_store, journal_streams=streams,
                ).register(ops)
                worker_protocol = NodeProtocol(signer=worker_signers[worker_id], verifier=verifier)
                gateway = NodeGateway(node_id=worker_id, protocol=worker_protocol, operations=ops)
                server_tls = ca.issue(
                    common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True,
                )
                s_cert, s_key, _ = server_tls.write(node_dir / "tls", prefix="server")
                server = NodeGatewayServer(
                    gateway=gateway,
                    ssl_context=server_mtls_context(
                        ca_file=str(ca_file), certificate_file=str(s_cert), private_key_file=str(s_key),
                    ),
                ).start()
                servers.append(server)
                _, port = server.address
                http = httpx.Client(verify=client_context, timeout=5.0)
                http_clients.append(http)
                transport = HttpNodeTransport(client=http)
                remote = RemoteWorkerClient(
                    sender_id="coordinator:demo", worker_id=worker_id, protocol=coordinator_protocol,
                    send=lambda message, p=port, t=transport: t.post(f"https://localhost:{p}/v1/node/call", message),
                )
                remote_clients[worker_id] = remote
                # Prove lease renewal through the real mTLS transport before work starts.
                renewed = remote.call("lease_renew", {
                    "lease_id": lease.lease_id, "fencing_token": lease.fencing_token, "ttl_seconds": 300,
                })
                if not renewed.ok:
                    raise RuntimeError(f"lease renewal failed for {worker_id}")
                targets.append(RemoteVerifierTarget(
                    worker_id=worker_id, trust_domain=trust_domain, client=remote,
                    lease_id=lease.lease_id, fencing_token=lease.fencing_token,
                    authority_grant_id="grant:verify",
                ))
                stream_ids[worker_id] = f"mission:v21:node:verify:{lease.lease_id}"

            proof_store = SqliteProofGraphStore(root / "proof.db")
            result = MultiNodeVerificationCoordinator(
                store=proof_store, graph_id="mission:v21", min_trust_domains=2,
            ).verify(
                mission_id="mission:v21", node_id="node:verify", execution_context_id="ctx:v21",
                candidate_sha=candidate_sha, targets=targets,
            )

            streamed_heads = []
            streamed_events = 0
            for worker_id, remote in remote_clients.items():
                page = remote.call("journal_poll", {"stream_id": stream_ids[worker_id], "cursor": 0, "limit": 100})
                if not page.ok:
                    raise RuntimeError("remote journal poll failed")
                rows, head = verify_journal_pages([page.payload])
                streamed_heads.append(head)
                streamed_events += len(rows)

            # Synthetic paired accounting validates the metric path only; it is not a live provider benchmark.
            measurements = [
                MissionMeasurement("m1", "frontier-control", True, True, 0.20, 4.0, 5000, 1000),
                MissionMeasurement("m1", "jev-control", True, True, 0.08, 3.0, 500, 500),
            ]
            a = summarize_measurements(measurements, condition="frontier-control")
            b = summarize_measurements(measurements, condition="jev-control")
            console.print_json(data={
                "mode": "v2.1-two-node-mtls-fabric-demo",
                "network_sockets_executed": 2,
                "physical_multi_machine_executed": False,
                "mutual_tls": True,
                "signed_application_messages": True,
                "durable_fenced_lease_renewal": True,
                "remote_verifier_subprocesses": result.receipts,
                "independent_trust_domains": list(result.positive_trust_domains),
                "quorum_accepted": result.accepted,
                "proof_revision": result.proof_revision,
                "streamed_execution_events": streamed_events,
                "streamed_journals_verified": len(streamed_heads),
                "synthetic_metric_path": {
                    "frontier_control_vsr": a.vsr,
                    "jev_control_vsr": b.vsr,
                    "frontier_efficiency_ratio": paired_frontier_efficiency_ratio(a, b),
                    "live_provider_measurement": False,
                },
                "truth_boundary": (
                    "two independent real loopback mTLS node gateways executed with fenced leases, fixed remote "
                    "verifiers, streamed hash-chained journals and diverse proof quorum; no claim of physical "
                    "Jonas-Lenovo/VDS execution or live TypeSafe/Dialagram benchmark"
                ),
            })
            if not (result.accepted and streamed_events >= 4 and len(streamed_heads) == 2):
                raise typer.Exit(code=3)
        finally:
            for http in http_clients:
                http.close()
            for server in servers:
                server.close()


@app.command("v22-demo")
def v22_demo() -> None:
    """Prove the deployable node daemon/client path over a real mTLS socket."""
    import base64
    with tempfile.TemporaryDirectory(prefix="jev-v22-") as td:
        root = Path(td)
        ca = EphemeralCertificateAuthority()
        server_tls = ca.issue(common_name="localhost", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True)
        client_tls = ca.issue(common_name="coordinator", client=True)
        s_cert, s_key, ca_file = server_tls.write(root / "server", prefix="node")
        c_cert, c_key, _ = client_tls.write(root / "client", prefix="coord")
        node_signer = Ed25519ReceiptSigner.generate(key_id="worker:v22")
        coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
        node_signer.write_private_key(root / "node.ed25519")
        coord_signer.write_private_key(root / "coord.ed25519")
        workspace = root / "workspace"; workspace.mkdir()
        (workspace / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        node_cfg = root / "node.json"
        node_cfg.write_text(json.dumps({
            "node_id":"worker:v22", "host":"127.0.0.1", "port":0,
            "ca_file":str(ca_file), "certificate_file":str(s_cert), "private_key_file":str(s_key),
            "signing_key_file":str(root / "node.ed25519"), "signing_key_id":"worker:v22",
            "peer_public_keys":{"coordinator":base64.b64encode(coord_signer.public_key_bytes()).decode("ascii")},
            "lease_db":str(root / "leases.db"), "verifier_workspace":str(workspace),
            "verifier_command":["python","-m","pytest","-q"], "verifier_name":"v22-pytest"
        }), encoding="utf-8")
        cfg = NodeAgentConfig.load_json(node_cfg)
        with NodeAgent(cfg) as node:
            _, port = node.address
            client_cfg = root / "client.json"
            client_cfg.write_text(json.dumps({
                "sender_id":"coordinator", "worker_id":"worker:v22",
                "endpoint_url":f"https://localhost:{port}/v1/node/call",
                "ca_file":str(ca_file), "certificate_file":str(c_cert), "private_key_file":str(c_key),
                "signing_key_file":str(root / "coord.ed25519"), "signing_key_id":"coordinator",
                "worker_public_key_b64":base64.b64encode(node_signer.public_key_bytes()).decode("ascii")
            }), encoding="utf-8")
            with NodeClientSession(NodeClientConfig.load_json(client_cfg)) as session:
                desc = session.describe()
            console.print_json(data={
                "mode":"v2.2-deployable-node-demo",
                "real_tcp_socket":True, "mutual_tls":True, "ed25519_application_signing":True,
                "persistent_signing_keys_reloaded":True, "node_describe_authenticated":True,
                "arbitrary_shell":desc.get("arbitrary_shell"), "capabilities":desc.get("capabilities"),
                "physical_multi_machine_executed":False,
                "truth_boundary":"deployable file-configured node and coordinator client executed on one host over real mTLS; no claim of Jonas-Lenovo/VDS execution"
            })



@app.command("node-client-template")
def node_client_template(
    output: Annotated[Path, typer.Option("--output", "-o")],
    sender_id: Annotated[str, typer.Option("--sender-id")],
    worker_id: Annotated[str, typer.Option("--worker-id")],
    endpoint_url: Annotated[str, typer.Option("--endpoint-url")],
) -> None:
    """Write a secret-free coordinator/client config template for a physical node."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = generate_client_config_template(sender_id=sender_id, worker_id=worker_id, endpoint_url=endpoint_url)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("node-probe")
def node_probe(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Perform an authenticated mTLS + Ed25519 probe of a physical Aftergraph node."""
    cfg = NodeClientConfig.load_json(config)
    with NodeClientSession(cfg) as session:
        description = session.describe()
    console.print_json(data={
        "status": "VERIFIED_REACHABLE",
        "sender_id": cfg.sender_id,
        "worker_id": cfg.worker_id,
        "endpoint_url": cfg.endpoint_url,
        "node": description,
    })



@app.command("node-keygen")
def node_keygen(
    output: Annotated[Path, typer.Option("--output", "-o")],
    key_id: Annotated[str, typer.Option("--key-id")],
) -> None:
    """Generate a persistent Ed25519 node signing key; print public material only."""
    signer = Ed25519ReceiptSigner.generate(key_id=key_id)
    target = signer.write_private_key(output)
    import base64
    console.print_json(data={
        "key_id": key_id,
        "private_key_file": str(target),
        "public_key_b64": base64.b64encode(signer.public_key_bytes()).decode("ascii"),
        "private_key_printed": False,
    })


@app.command("node-template")
def node_template(
    output: Annotated[Path, typer.Option("--output", "-o")],
    node_id: Annotated[str, typer.Option("--node-id")],
) -> None:
    """Write a secret-free deployable node-agent configuration template."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(generate_node_config_template(node_id=node_id), indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("node-doctor")
def node_doctor(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Validate a physical-node deployment config without starting network service."""
    cfg = NodeAgentConfig.load_json(config)
    summary = cfg.public_summary()
    summary["status"] = "READY"
    console.print_json(data=summary)


@app.command("node-serve")
def node_serve(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Run the bounded mTLS Aftergraph node gateway until interrupted."""
    cfg = NodeAgentConfig.load_json(config)
    agent = NodeAgent(cfg)
    host, port = agent.address
    console.print_json(data={
        "status": "SERVING", "node_id": cfg.node_id, "host": host, "port": port,
        "mutual_tls": True, "arbitrary_shell": False,
    })
    try:
        agent.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()



@app.command("relay-hub-template")
def relay_hub_template(
    output: Annotated[Path, typer.Option("--output", "-o")],
) -> None:
    """Write a secret-free outbound relay-hub configuration template."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(generate_relay_hub_config_template(), indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("relay-node-template")
def relay_node_template(
    output: Annotated[Path, typer.Option("--output", "-o")],
    node_config_file: Annotated[str, typer.Option("--node-config-file")] = "node.json",
) -> None:
    """Write a secret-free outbound relay-node configuration template."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = generate_relay_node_config_template(node_config_file=node_config_file)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("relay-client-template")
def relay_client_template(
    output: Annotated[Path, typer.Option("--output", "-o")],
    sender_id: Annotated[str, typer.Option("--sender-id")],
    worker_id: Annotated[str, typer.Option("--worker-id")],
) -> None:
    """Write a secret-free relay coordinator configuration template."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = generate_relay_client_config_template(sender_id=sender_id, worker_id=worker_id)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("relay-hub-serve")
def relay_hub_serve(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Run the mTLS outbound-node relay hub until interrupted."""
    cfg = RelayHubConfig.load_json(config)
    hub = RelayHubServer(
        host=cfg.host,
        port=cfg.port,
        ca_file=cfg.ca_file,
        certificate_file=cfg.certificate_file,
        private_key_file=cfg.private_key_file,
        allowed_node_ids=set(cfg.allowed_node_ids),
        allowed_coordinator_ids=set(cfg.allowed_coordinator_ids),
        call_timeout_s=cfg.call_timeout_s,
        generation_store=(RelayGenerationStore(cfg.generation_store_file) if cfg.generation_store_file else None),
    ).start()
    host, port = hub.address
    console.print_json(data={
        "status": "SERVING",
        "mode": "outbound-node-relay",
        "host": host,
        "port": port,
        "mutual_tls": True,
        "arbitrary_shell": False,
        "allowed_nodes": sorted(cfg.allowed_node_ids),
        "allowed_coordinators": sorted(cfg.allowed_coordinator_ids),
    })
    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        hub.close()


@app.command("relay-node-serve")
def relay_node_serve(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Connect a bounded node to a relay using outbound-only mTLS."""
    cfg = RelayNodeConfig.load_json(config)
    service = RelayNodeService(cfg).start()
    try:
        import time
        deadline = time.monotonic() + max(5.0, cfg.connect_timeout_s + 1.0)
        while not service.registered and time.monotonic() < deadline:
            if service.last_error is not None:
                break
            time.sleep(0.05)
        if not service.registered:
            raise RuntimeError(f"relay node registration failed: {service.last_error}")
        console.print_json(data={
            "status": "REGISTERED",
            "node_id": service.node_config.node_id,
            "relay_host": cfg.relay_host,
            "relay_port": cfg.relay_port,
            "outbound_only": True,
            "local_listen_port": None,
            "application_sender_key_binding": bool(service.node_config.peer_sender_key_ids),
            "arbitrary_shell": False,
        })
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        service.close()


@app.command("relay-probe")
def relay_probe(
    config: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Probe a relay-connected node with mTLS plus end-to-end Ed25519 signing."""
    cfg = RelayClientConfig.load_json(config)
    session = RelayNodeClientSession(cfg)
    description = session.describe()
    console.print_json(data={
        "status": "VERIFIED_REACHABLE",
        "transport": "outbound-relay",
        "sender_id": cfg.sender_id,
        "worker_id": cfg.worker_id,
        "relay_host": cfg.relay_host,
        "relay_port": cfg.relay_port,
        "node": description,
    })


@app.command("v23-demo")
def v23_demo() -> None:
    """Prove outbound-only relay, remote lease admission, verification and journal identity."""
    import base64
    import sys
    import time
    from .proof_graph import workspace_tree_hash

    with tempfile.TemporaryDirectory(prefix="jev-v23-relay-") as td:
        root = Path(td)
        ca = EphemeralCertificateAuthority()
        relay_tls = ca.issue(
            common_name="relay.local", dns_names=["localhost"], ip_addresses=["127.0.0.1"], server=True,
        )
        node_tls = ca.issue(common_name="worker:v23", client=True)
        coord_tls = ca.issue(common_name="coordinator", client=True)
        rcert, rkey, ca_file = relay_tls.write(root / "relay-tls", prefix="relay")
        ncert, nkey, _ = node_tls.write(root / "node-tls", prefix="node")
        ccert, ckey, _ = coord_tls.write(root / "coord-tls", prefix="coord")

        node_signer = Ed25519ReceiptSigner.generate(key_id="worker:v23")
        coord_signer = Ed25519ReceiptSigner.generate(key_id="coordinator")
        node_signer.write_private_key(root / "node.ed25519")
        coord_signer.write_private_key(root / "coord.ed25519")
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "candidate.py").write_text("VALUE = 42\n", encoding="utf-8")
        node_cfg_path = root / "node.json"
        node_cfg_path.write_text(json.dumps({
            "node_id": "worker:v23",
            "host": "127.0.0.1",
            "port": 0,
            "ca_file": str(ca_file),
            "certificate_file": str(ncert),
            "private_key_file": str(nkey),
            "signing_key_file": str(root / "node.ed25519"),
            "signing_key_id": "worker:v23",
            "peer_public_keys": {
                "coordinator": base64.b64encode(coord_signer.public_key_bytes()).decode("ascii"),
            },
            "peer_sender_key_ids": {"coordinator": "coordinator"},
            "lease_issuer_ids": ["coordinator"],
            "lease_allowed_capabilities": [
                "verify_candidate", "journal_poll", "lease_heartbeat", "lease_renew",
            ],
            "lease_db": str(root / "leases.db"),
            "verifier_workspace": str(workspace),
            "verifier_command": [sys.executable, "-c", "import candidate; assert candidate.VALUE == 42"],
            "verifier_name": "v23-relay-verifier",
        }), encoding="utf-8")
        gateway = build_node_gateway(NodeAgentConfig.load_json(node_cfg_path))
        coord_protocol = NodeProtocol(
            signer=coord_signer,
            verifier=Ed25519ReceiptVerifier({
                "coordinator": coord_signer.public_key_bytes(),
                "worker:v23": node_signer.public_key_bytes(),
            }),
        )

        with RelayHubServer(
            host="127.0.0.1", port=0, ca_file=ca_file,
            certificate_file=rcert, private_key_file=rkey,
            allowed_node_ids={"worker:v23"}, allowed_coordinator_ids={"coordinator"},
        ) as hub:
            host, port = hub.address
            with RelayNodeAgent(
                node_id="worker:v23", relay_host=host, relay_port=port,
                ca_file=ca_file, certificate_file=ncert, private_key_file=nkey,
                gateway=gateway,
            ) as node:
                deadline = time.monotonic() + 3.0
                while not node.registered and time.monotonic() < deadline:
                    time.sleep(0.02)
                if not node.registered:
                    raise RuntimeError(f"relay node failed to register: {node.last_error}")
                relay = RelayCoordinatorClient(
                    coordinator_id="coordinator", relay_host=host, relay_port=port,
                    ca_file=ca_file, certificate_file=ccert, private_key_file=ckey,
                )
                remote = RemoteWorkerClient(
                    sender_id="coordinator", worker_id="worker:v23",
                    protocol=coord_protocol, send=relay.send,
                )
                description = remote.call("node_describe", {})
                issued = remote.call("lease_issue", {
                    "node_id": "node:verify",
                    "authority_grant_id": "grant:verify",
                    "capabilities": ["verify_candidate", "journal_poll", "lease_heartbeat", "lease_renew"],
                    "ttl_seconds": 300,
                })
                if not issued.ok:
                    raise RuntimeError(str(issued.payload))
                lease = issued.payload
                candidate_sha = "sha256:" + workspace_tree_hash(workspace)
                order = RemoteWorkOrder(
                    mission_id="mission:v23", node_id="node:verify", execution_context_id="ctx:v23",
                    lease_id=str(lease["lease_id"]), fencing_token=int(lease["fencing_token"]),
                    authority_grant_id="grant:verify", candidate_sha=candidate_sha,
                )
                receipt = RemoteExecutionCoordinator(remote).execute(order)
                page = remote.call("journal_poll", {
                    "stream_id": receipt.evidence["stream_id"], "cursor": 0, "limit": 100,
                    "lease_id": lease["lease_id"], "fencing_token": lease["fencing_token"],
                })
                if not page.ok:
                    raise RuntimeError(str(page.payload))
                rows, stream_head = verify_journal_pages([page.payload])
                receipt_head = str(receipt.evidence["execution_journal_head_sha256"])
                console.print_json(data={
                    "mode": "v2.3-outbound-relay-demo",
                    "real_tcp_socket": True,
                    "mutual_tls": True,
                    "node_connection_direction": "worker-outbound-to-relay",
                    "node_inbound_listener": False,
                    "relay_session_generation": node.session_generation,
                    "end_to_end_ed25519": True,
                    "application_sender_key_binding": description.payload.get("application_sender_key_binding"),
                    "remote_lease_issued": True,
                    "fencing_token": lease["fencing_token"],
                    "remote_verifier_subprocess": receipt.verdict,
                    "journal_events": len(rows),
                    "receipt_stream_same_head": stream_head == receipt_head,
                    "arbitrary_shell": description.payload.get("arbitrary_shell"),
                    "physical_multi_machine_executed": False,
                    "truth_boundary": (
                        "real outbound-only mTLS relay path executed on one host, including signed remote lease "
                        "admission, fixed verifier subprocess and hash-identical streamed journal; physical "
                        "Jonas-Lenovo/VDS deployment remains unexecuted because the available remote connector is quota-blocked"
                    ),
                })
                if not (receipt.passed and stream_head == receipt_head and len(rows) == 2):
                    raise typer.Exit(code=3)


@app.command("physical-pair-template")
def physical_pair_template(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("physical-pair.json"),
) -> None:
    """Write a secret-free Jonas-Lenovo/VDS physical-pair manifest template."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(generate_physical_pair_template(), indent=2) + "\n", encoding="utf-8")
    console.print_json(data={"written": str(output), "contains_secrets": False})


@app.command("physical-pair-doctor")
def physical_pair_doctor(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Validate two physical-node configs without claiming network reachability."""
    report = PhysicalPairManifest.load_json(manifest).doctor()
    console.print_json(data=report)


def _load_campaign_cost_model(path: Path) -> BenchmarkCostModel:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("pricing file must be a JSON object")
    if raw.get("replace_before_use") is True:
        raise ValueError("pricing file is a placeholder; replace_before_use must be false before campaign execution")

    def price(value: Any) -> TokenPrice:
        if not isinstance(value, dict):
            raise TypeError("pricing entries must be JSON objects")
        return TokenPrice(
            input_per_million=float(value["input_per_million"]),
            output_per_million=float(value["output_per_million"]),
            cached_input_per_million=(
                float(value["cached_input_per_million"])
                if value.get("cached_input_per_million") is not None else None
            ),
        )

    decisions = raw.get("decision_by_condition")
    if not isinstance(decisions, dict) or not decisions:
        raise ValueError("pricing file requires decision_by_condition")
    return BenchmarkCostModel(
        generator=price(raw["generator"]),
        decision_by_condition={str(k): price(v) for k, v in decisions.items()},
        frontier_decision_conditions=frozenset(str(v) for v in (raw.get("frontier_decision_conditions") or [])),
    )


@app.command("live-campaign")
def live_campaign(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
    pricing: Annotated[Path, typer.Option("--pricing", exists=True, readable=True)],
    incumbent: Annotated[str, typer.Option("--incumbent")],
    candidate: Annotated[str, typer.Option("--candidate")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("live-campaign-results"),
    repeats: Annotated[int, typer.Option("--repeats")] = 3,
    shadow_pairs: Annotated[int, typer.Option("--shadow-pairs")] = 5,
    experiment_pairs: Annotated[int, typer.Option("--experiment-pairs")] = 5,
    holdout_pairs: Annotated[int, typer.Option("--holdout-pairs")] = 5,
    min_holdout_trials: Annotated[int, typer.Option("--min-holdout-trials")] = 15,
    noninferiority_margin: Annotated[float, typer.Option("--noninferiority-margin")] = 0.02,
    max_fcr: Annotated[float, typer.Option("--max-fcr")] = 0.0,
) -> None:
    """Run the real paired provider benchmark, then apply the statistical promotion gate.

    Provider credentials are resolved by the benchmark configs from runtime environment
    variables. Pricing is explicit operator-supplied evidence rather than a baked-in claim.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest(manifest, output_dir=output_dir, repeats=repeats)
    rows = read_jsonl(output_dir / "results.jsonl")
    report = build_campaign_report(
        rows,
        incumbent_condition=incumbent,
        candidate_condition=candidate,
        cost_model=_load_campaign_cost_model(pricing),
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout_pairs,
        min_holdout_trials=min_holdout_trials,
        noninferiority_margin=noninferiority_margin,
        max_fcr=max_fcr,
    )
    report["provider_execution_performed"] = True
    report["live_provider_measurement"] = False
    report["authenticated_live_ab_executed"] = False
    report["truth_boundary"] = "provider-backed benchmark executed, but v2.9 authenticated signed paired receipts were not produced"
    target = output_dir / "campaign-report.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    console.print_json(data={**report, "report": str(target)})


@app.command("v24-demo")
def v24_demo() -> None:
    """Prove restart-durable relay generations, resumable journals and promotion accounting."""
    with tempfile.TemporaryDirectory(prefix="jev-v24-") as td:
        root = Path(td)
        generations = RelayGenerationStore(root / "relay.db")
        first_generation = generations.next_generation("worker:jonas-lenovo")
        # Re-open the SQLite store to model relay-process restart.
        second_generation = RelayGenerationStore(root / "relay.db").next_generation("worker:jonas-lenovo")

        journal = ExecutionJournal()
        first_event = journal.append("verification.started", {"verifier": "demo"}, observed_at="2026-09-25T00:00:00+00:00")
        second_event = journal.append("verification.completed", {"verdict": "PASS"}, observed_at="2026-09-25T00:00:01+00:00")
        all_rows = journal.to_list()

        class DemoClient:
            def __init__(self, page: dict[str, Any]) -> None:
                self.page = page
                self.cursor_seen = -1
            def call(self, operation: str, payload: dict[str, Any]):
                self.cursor_seen = int(payload["cursor"])
                return type("DemoResult", (), {"ok": True, "payload": self.page})()

        store = JournalCheckpointStore(root / "journal.db")
        first_page = {
            "worker_id": "worker:jonas-lenovo", "stream_id": "mission:node:lease",
            "cursor": 0, "next_cursor": 1, "head_sha256": first_event.event_sha256,
            "events": [all_rows[0]], "complete": False,
        }
        ResumableJournalFollower(DemoClient(first_page), store).poll_once(
            worker_id="worker:jonas-lenovo", stream_id="mission:node:lease",
            lease_id="lease", fencing_token=1,
        )
        second_page = {
            "worker_id": "worker:jonas-lenovo", "stream_id": "mission:node:lease",
            "cursor": 1, "next_cursor": 2, "head_sha256": second_event.event_sha256,
            "events": [all_rows[1]], "complete": True,
        }
        resumed_client = DemoClient(second_page)
        ResumableJournalFollower(resumed_client, JournalCheckpointStore(root / "journal.db")).poll_once(
            worker_id="worker:jonas-lenovo", stream_id="mission:node:lease",
            lease_id="lease", fencing_token=1,
        )
        checkpoint = store.get("worker:jonas-lenovo", "mission:node:lease")

        rows: list[dict[str, Any]] = []
        for repeat in range(1, 4):
            for case in ("a", "b"):
                common = {
                    "case_id": case, "repeat": repeat, "status": "verified",
                    "metrics": {"completion_claims": 1, "false_completion_claims": 0,
                                "provider_input_tokens": 1000, "provider_output_tokens": 100,
                                "provider_cached_input_tokens": 0},
                }
                rows.append({**common, "condition": "frontier", "metrics": {**common["metrics"], "decision_input_tokens": 1000, "decision_output_tokens": 100}})
                rows.append({**common, "condition": "jev", "metrics": {**common["metrics"], "decision_input_tokens": 100, "decision_output_tokens": 0}})
        campaign = build_campaign_report(
            rows,
            incumbent_condition="frontier", candidate_condition="jev",
            cost_model=BenchmarkCostModel(
                generator=TokenPrice(4.0, 20.0, 0.4),
                decision_by_condition={"frontier": TokenPrice(4.0, 20.0), "jev": TokenPrice(0.042, 0.0)},
                frontier_decision_conditions=frozenset({"frontier"}),
            ),
            shadow_pairs=2, experiment_pairs=2, holdout_pairs=2,
            min_holdout_trials=6, noninferiority_margin=0.0, max_fcr=0.0,
        )
        console.print_json(data={
            "mode": "v2.4-resilience-and-live-campaign-demo",
            "relay_generation_before_restart": first_generation,
            "relay_generation_after_restart": second_generation,
            "relay_generation_monotonic": second_generation > first_generation,
            "journal_resume_cursor_seen": resumed_client.cursor_seen,
            "journal_checkpoint_complete": checkpoint.complete,
            "journal_checkpoint_cursor": checkpoint.cursor,
            "journal_head_verified": checkpoint.last_event_sha256 == second_event.event_sha256,
            "campaign_state": campaign["state"],
            "campaign_paired_missions": campaign["paired_missions"],
            "candidate_cpvo_lower": campaign["promotion"]["candidate_cpvo"] < campaign["promotion"]["incumbent_cpvo"],
            "synthetic_frontier_intelligence_efficiency_ratio": campaign["frontier_intelligence_efficiency_ratio"],
            "live_provider_measurement": False,
            "physical_multi_machine_executed": False,
            "truth_boundary": "demo proves durable continuation and campaign math with synthetic paired measurements; it does not claim a physical Lenovo/VDS or live provider run",
        })


@app.command("campaign-plan-v25")
def campaign_plan_v25(
    baseline_vsr: Annotated[float, typer.Option("--baseline-vsr", min=0.000001, max=0.999999)] = 0.90,
    margin: Annotated[float, typer.Option("--margin", min=0.000001, max=0.999999)] = 0.02,
    alpha: Annotated[float, typer.Option("--alpha", min=0.000001, max=0.499999)] = 0.05,
    power: Annotated[float, typer.Option("--power", min=0.500001, max=0.999999)] = 0.80,
) -> None:
    """Plan a conservative paired-campaign sample size before provider execution."""
    console.print_json(data=plan_noninferiority_pairs(
        baseline_vsr=baseline_vsr, margin=margin, alpha=alpha, power=power
    ))


@app.command("campaign-report-v25")
def campaign_report_v25(
    results: Annotated[Path, typer.Argument(exists=True, readable=True)],
    pricing: Annotated[Path, typer.Option("--pricing", exists=True, readable=True)],
    incumbent: Annotated[str, typer.Option("--incumbent")],
    candidate: Annotated[str, typer.Option("--candidate")],
    shadow_pairs: Annotated[int, typer.Option("--shadow-pairs", min=1)] = 5,
    experiment_pairs: Annotated[int, typer.Option("--experiment-pairs", min=1)] = 5,
    holdout_pairs: Annotated[int, typer.Option("--holdout-pairs", min=1)] = 20,
    noninferiority_margin: Annotated[float, typer.Option("--noninferiority-margin", min=0.0, max=1.0)] = 0.02,
    max_fcr: Annotated[float, typer.Option("--max-fcr", min=0.0, max=1.0)] = 0.0,
    min_fie_ratio: Annotated[float, typer.Option("--min-fie-ratio", min=0.000001)] = 1.0,
    target_fie_ratio: Annotated[float, typer.Option("--target-fie-ratio", min=0.000001)] = 10.0,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Evaluate existing paired evidence with a reserved holdout-only promotion gate."""
    rows = read_jsonl(results)
    policy = EvidenceCampaignPolicy(
        min_holdout_pairs=holdout_pairs,
        noninferiority_margin=noninferiority_margin,
        max_fcr=max_fcr,
        min_fie_ratio=min_fie_ratio,
        target_fie_ratio=target_fie_ratio,
    )
    report = evaluate_evidence_campaign(
        rows, incumbent_condition=incumbent, candidate_condition=candidate,
        cost_model=_load_campaign_cost_model(pricing),
        shadow_pairs=shadow_pairs, experiment_pairs=experiment_pairs, holdout_pairs=holdout_pairs,
        policy=policy,
    )
    report["live_provider_measurement"] = False
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report["report"] = str(output)
    console.print_json(data=report)


@app.command("live-campaign-v25")
def live_campaign_v25(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
    pricing: Annotated[Path, typer.Option("--pricing", exists=True, readable=True)],
    incumbent: Annotated[str, typer.Option("--incumbent")],
    candidate: Annotated[str, typer.Option("--candidate")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("live-campaign-v25-results"),
    repeats: Annotated[int, typer.Option("--repeats", min=1)] = 6,
    shadow_pairs: Annotated[int, typer.Option("--shadow-pairs", min=1)] = 5,
    experiment_pairs: Annotated[int, typer.Option("--experiment-pairs", min=1)] = 5,
    holdout_pairs: Annotated[int, typer.Option("--holdout-pairs", min=1)] = 20,
    noninferiority_margin: Annotated[float, typer.Option("--noninferiority-margin", min=0.0, max=1.0)] = 0.02,
    max_fcr: Annotated[float, typer.Option("--max-fcr", min=0.0, max=1.0)] = 0.0,
    min_fie_ratio: Annotated[float, typer.Option("--min-fie-ratio", min=0.000001)] = 1.0,
    target_fie_ratio: Annotated[float, typer.Option("--target-fie-ratio", min=0.000001)] = 10.0,
) -> None:
    """Run live paired missions and seal an evidence-grade v2.5 campaign bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # Pricing is validated before any provider-backed mission can start. This prevents
    # the checked-in zero-price placeholder from accidentally launching a live run.
    cost_model = _load_campaign_cost_model(pricing)
    run_manifest(manifest, output_dir=output_dir, repeats=repeats)
    results = output_dir / "results.jsonl"
    rows = read_jsonl(results)
    report = evaluate_evidence_campaign(
        rows, incumbent_condition=incumbent, candidate_condition=candidate,
        cost_model=cost_model,
        shadow_pairs=shadow_pairs, experiment_pairs=experiment_pairs, holdout_pairs=holdout_pairs,
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=holdout_pairs, noninferiority_margin=noninferiority_margin,
            max_fcr=max_fcr, min_fie_ratio=min_fie_ratio, target_fie_ratio=target_fie_ratio,
        ),
    )
    report["provider_execution_performed"] = True
    report["live_provider_measurement"] = False
    report["authenticated_live_ab_executed"] = False
    report["truth_boundary"] = "provider-backed benchmark executed, but legacy v2.5 evidence lacks v2.9 authenticated signed paired receipts"
    report_path = output_dir / "campaign-report.v25.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from . import __version__
    bundle_path = output_dir / "campaign-evidence.v1.json"
    bundle = CampaignEvidenceBundle.create(
        manifest=manifest, pricing=pricing, results=results, report=report_path,
        output=bundle_path, package_version=__version__,
    )
    evidence = bundle.verify(base_dir=bundle_path.parent)
    console.print_json(data={**report, "evidence_bundle": str(bundle_path), "evidence_verified": evidence["valid"]})


@app.command("campaign-verify-v25")
def campaign_verify_v25(
    bundle: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Verify hashes in a sealed v2.5 campaign evidence bundle."""
    result = CampaignEvidenceBundle.load(bundle).verify()
    console.print_json(data=result)
    if not result["valid"]:
        raise typer.Exit(code=3)


@app.command("v25-demo")
def v25_demo() -> None:
    """Prove holdout isolation, 10x feasibility analysis, evidence sealing and regression quarantine."""
    with tempfile.TemporaryDirectory(prefix="jev-v25-") as td:
        root = Path(td)
        rows: list[dict[str, Any]] = []
        # Six paired synthetic missions: same generator, much cheaper Jev control.
        for repeat in range(1, 4):
            for case in ("a", "b"):
                common = {
                    "case_id": case, "repeat": repeat, "status": "verified",
                    "metrics": {
                        "completion_claims": 1, "false_completion_claims": 0,
                        "provider_input_tokens": 1000, "provider_output_tokens": 100,
                        "provider_cached_input_tokens": 0, "wall_time_ms": 1000,
                    },
                }
                rows.append({**common, "condition": "frontier", "metrics": {**common["metrics"], "decision_input_tokens": 1000, "decision_output_tokens": 100}})
                rows.append({**common, "condition": "jev", "metrics": {**common["metrics"], "decision_input_tokens": 100, "decision_output_tokens": 0}})
        costs = BenchmarkCostModel(
            generator=TokenPrice(4.0, 20.0, 0.4),
            decision_by_condition={"frontier": TokenPrice(4.0, 20.0), "jev": TokenPrice(0.042, 0.0)},
            frontier_decision_conditions=frozenset({"frontier"}),
        )
        report = evaluate_evidence_campaign(
            rows, incumbent_condition="frontier", candidate_condition="jev", cost_model=costs,
            shadow_pairs=2, experiment_pairs=2, holdout_pairs=2,
            policy=EvidenceCampaignPolicy(
                min_holdout_pairs=2, noninferiority_margin=0.0, max_fcr=0.0,
                min_fie_ratio=1.0, target_fie_ratio=10.0, bootstrap_samples=1000, bootstrap_seed=25,
            ),
        )
        manifest = root / "manifest.yaml"; manifest.write_text("name: synthetic-v25\n", encoding="utf-8")
        pricing = root / "pricing.json"; pricing.write_text("{}\n", encoding="utf-8")
        results = root / "results.jsonl"; results.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
        report_path = root / "report.json"; report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
        from . import __version__
        evidence = CampaignEvidenceBundle.create(
            manifest=manifest, pricing=pricing, results=results, report=report_path,
            output=root / "evidence.json", package_version=__version__,
        ).verify(base_dir=root)
        monitor = ContinuousRegressionMonitor(RegressionPolicy(window_size=4, min_vsr=0.75, max_fcr=0.0, max_cpvo_usd=1.0))
        for _ in range(3):
            monitor.observe(OutcomeSample(True, False, 0.2))
        quarantine = monitor.observe(OutcomeSample(False, True, 0.2))
        console.print_json(data={
            "mode": "v2.5-evidence-grade-frontier-efficiency-gate",
            "holdout_only_promotion": report["promotion"]["evidence_scope"] == "holdout-only",
            "campaign_promoted": report["promotion"]["promote"],
            "observed_synthetic_fie_ratio": report["all"]["frontier_intelligence_efficiency_ratio"],
            "target_ratio": report["efficiency_target"]["target_ratio"],
            "control_plane_only_ceiling_ratio": report["efficiency_target"]["control_plane_only_ceiling_ratio"],
            "target_attainable_by_control_plane_only": report["efficiency_target"]["target_attainable_by_control_plane_only"],
            "requires_generator_or_context_reduction": report["efficiency_target"]["requires_generator_or_context_reduction"],
            "evidence_bundle_verified": evidence["valid"],
            "post_promotion_quarantine_triggered": quarantine["quarantine"],
            "live_provider_measurement": False,
            "truth_boundary": "all v25-demo campaign records are synthetic and prove measurement/promotion mechanics only",
        })


@app.command("efficiency-plan-v26")
def efficiency_plan_v26(
    profile: Annotated[Path, typer.Argument(exists=True, readable=True)],
    levers: Annotated[Path, typer.Option("--levers", exists=True, readable=True)],
    target_ratio: Annotated[float, typer.Option("--target-ratio", min=0.000001)] = 10.0,
    min_quality: Annotated[float, typer.Option("--min-quality", min=0.0, max=1.0)] = 0.95,
    min_evidence: Annotated[str, typer.Option("--min-evidence")] = "hypothesis",
) -> None:
    """Compile a bounded whole-system frontier-token plan without claiming measured gains."""
    raw_profile = json.loads(profile.read_text(encoding="utf-8"))
    raw_levers = json.loads(levers.read_text(encoding="utf-8"))
    workload = FrontierWorkloadProfile(
        profile_id=str(raw_profile["profile_id"]),
        categories={str(k): int(v) for k, v in dict(raw_profile["categories"]).items()},
        verified_outcomes=int(raw_profile.get("verified_outcomes", 0)),
        missions=int(raw_profile.get("missions", 0)),
        metadata=dict(raw_profile.get("metadata") or {}),
    )
    mechanisms = [
        EfficiencyLever(
            lever_id=str(item["lever_id"]),
            reductions={str(k): float(v) for k, v in dict(item["reductions"]).items()},
            quality_retention_lower_bound=float(item.get("quality_retention_lower_bound", 1.0)),
            evidence_level=str(item.get("evidence_level", "hypothesis")),
            complexity_cost=float(item.get("complexity_cost", 1.0)),
            metadata=dict(item.get("metadata") or {}),
        )
        for item in raw_levers
    ]
    compiler = SystemEfficiencyCompiler()
    region = compiler.attainable_region(
        workload, mechanisms, target_ratio=target_ratio,
        minimum_quality_retention=min_quality, minimum_evidence_level=min_evidence,
    )
    plan = compiler.compile(
        workload, mechanisms, target_ratio=target_ratio,
        minimum_quality_retention=min_quality, minimum_evidence_level=min_evidence,
    )
    console.print_json(data={"attainable_region": region.to_dict(), "plan": plan.to_dict()})


@app.command("v26-demo")
def v26_demo() -> None:
    """Demonstrate bounded whole-system 10x planning with explicit synthetic truth boundaries."""
    workload = FrontierWorkloadProfile(
        profile_id="synthetic-v26",
        categories={
            "context_input": 80_000,
            "generation_output": 20_000,
            "frontier_control": 20_000,
            "retry": 20_000,
        },
        verified_outcomes=90, missions=100,
    )
    mechanisms = [
        EfficiencyLever("context-compiler", {"context_input": 0.75}, 0.995, "benchmarked"),
        EfficiencyLever("jev-control", {"frontier_control": 0.95}, 0.998, "observed"),
        EfficiencyLever("retry-pruning", {"retry": 0.75}, 0.995, "observed"),
        EfficiencyLever(
            "cheap-first-escalation",
            {"context_input": 0.70, "generation_output": 0.70, "retry": 0.70},
            0.99, "modeled",
        ),
        EfficiencyLever(
            "verified-early-exit",
            {"context_input": 0.20, "generation_output": 0.20, "retry": 0.20},
            0.995, "modeled",
        ),
    ]
    compiler = SystemEfficiencyCompiler()
    observed_region = compiler.attainable_region(
        workload, mechanisms, target_ratio=10.0,
        minimum_quality_retention=0.97, minimum_evidence_level="observed",
    )
    modeled_region = compiler.attainable_region(
        workload, mechanisms, target_ratio=10.0,
        minimum_quality_retention=0.97, minimum_evidence_level="modeled",
    )
    plan = compiler.compile(
        workload, mechanisms, target_ratio=10.0,
        minimum_quality_retention=0.97, minimum_evidence_level="modeled",
    )

    context_rows = [
        ContextCandidate("mission", "goal", 5000, relevance=1.0, information_gain=1.0),
        ContextCandidate("code", "relevant-code", 7000, relevance=0.95, information_gain=1.0),
        ContextCandidate("history", "old-history", 20_000, relevance=0.10, information_gain=0.5),
    ]
    context_plan = AdaptiveContextBudgeter().plan(context_rows, minimum_utility_retention=0.95)
    early_exit = EarlyExitGate().decide(
        predicted_vsr=0.97, required_vsr=0.95, risk_class="normal",
        assurance_level=2, cheap_path_verified=True,
    )
    retry_plan = RetryBudgetOptimizer().plan(
        [
            RetryCandidate(1, 0.10, 2000),
            RetryCandidate(2, 0.03, 2000),
            RetryCandidate(3, 0.005, 2000),
        ],
        frontier_token_budget=6000, min_vsr_gain_per_1k_tokens=0.01,
    )
    console.print_json(data={
        "mode": "v2.6-system-efficiency-compiler",
        "baseline_frontier_tokens": workload.total_frontier_tokens,
        "observed_evidence_10x_attainable": observed_region.target_attainable,
        "modeled_10x_attainable": modeled_region.target_attainable,
        "modeled_maximum_ratio": modeled_region.maximum_ratio,
        "compiled_plan": plan.to_dict(),
        "adaptive_context_budget": context_plan.to_dict(),
        "verified_early_exit_uses_frontier": early_exit.use_frontier,
        "retry_plan": {
            "admitted_retries": list(retry_plan.admitted_retries),
            "frontier_tokens_reserved": retry_plan.frontier_tokens_reserved,
            "stop_reason": retry_plan.stop_reason,
        },
        "live_provider_measurement": False,
        "truth_boundary": (
            "all v26-demo token reductions are synthetic planning inputs; they demonstrate compiler mechanics, "
            "not an observed 10x Jev or frontier-model result"
        ),
    })


@app.command("v27-demo")
def v27_demo() -> None:
    """Execute the v2.7 cheap-first/frontier escalation path with deterministic synthetic adapters."""
    from .context_compiler import ContextCandidate
    from .system_efficiency import RetryCandidate
    context = [
        ContextCandidate("mission", "goal", 4_000, relevance=1.0, information_gain=1.0),
        ContextCandidate("code", "relevant-code", 8_000, relevance=.95, information_gain=1.0),
        ContextCandidate("history", "low-value-history", 28_000, relevance=.02, information_gain=.1),
    ]
    engine = EmpiricalEfficiencyExecutionEngine()
    cheap_receipt = engine.run(
        mission_id="synthetic-cheap", context=context,
        policy=EfficiencyExecutionPolicy(required_vsr=.95, frontier_token_budget=20_000),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", True, .97, evidence_ids=("synthetic-proof:cheap",)),
        frontier_attempt=lambda keys, retry: ExecutionAttempt("frontier", True, .99, 8_000, 2_000),
    )
    escalated = engine.run(
        mission_id="synthetic-escalated", context=context,
        policy=EfficiencyExecutionPolicy(required_vsr=.95, frontier_token_budget=20_000),
        cheap_attempt=lambda keys: ExecutionAttempt("cheap", False, .80),
        frontier_attempt=lambda keys, retry: ExecutionAttempt("frontier", True, .99, 8_000, 2_000, .10, ("synthetic-proof:frontier",)),
        retry_candidates=[RetryCandidate(1,.03,2_000)],
    )
    console.print_json(data={
        "mode":"v2.7-empirical-efficiency-execution-engine",
        "cheap_path":cheap_receipt.to_dict(), "escalated_path":escalated.to_dict(),
        "live_provider_measurement":False,
        "truth_boundary":"deterministic synthetic adapters prove runtime mechanics only; no live Jev/frontier 10x performance claim",
    })


@app.command("v28-demo")
def v28_demo() -> None:
    """Run a deterministic paired holdout campaign without making a live-provider claim."""
    from .campaign_runtime import BenchmarkCostModel, TokenPrice
    from .evidence_campaign import EvidenceCampaignPolicy
    from .paired_holdout import PairedHoldoutCampaignRunner, PairedMission

    missions = [
        PairedMission("fixture-a", 1, "shadow", {"task": "repair-a"}),
        PairedMission("fixture-b", 1, "experiment", {"task": "repair-b"}),
        PairedMission("fixture-c", 1, "holdout", {"task": "repair-c"}),
        PairedMission("fixture-d", 1, "holdout", {"task": "repair-d"}),
    ]
    runner = PairedHoldoutCampaignRunner(
        incumbent_condition="frontier", candidate_condition="jev", seed=20260925
    )

    def run_condition(mission, condition):
        frontier = condition == "frontier"
        return {
            "status": "verified",
            "metrics": {
                "completion_claims": 1,
                "false_completion_claims": 0,
                "provider_input_tokens": 9000 if frontier else 700,
                "provider_output_tokens": 1000 if frontier else 100,
                "decision_input_tokens": 1000 if frontier else 100,
                "decision_output_tokens": 100 if frontier else 0,
                "wall_time_ms": 1500 if frontier else 900,
            },
            "evidence_ids": [f"synthetic:{mission.case_id}:{condition}"],
        }

    execution = runner.run(
        missions=missions,
        run_condition=run_condition,
        live_provider_measurement=False,
    )
    costs = BenchmarkCostModel(
        generator=TokenPrice(4.0, 20.0, 0.4),
        decision_by_condition={
            "frontier": TokenPrice(4.0, 20.0, 0.4),
            "jev": TokenPrice(0.042, 0.0, 0.042),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )
    report = execution.evaluate(
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=costs,
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=2,
            noninferiority_margin=0.05,
            max_fcr=0.0,
            min_fie_ratio=1.0,
            target_fie_ratio=10.0,
            bootstrap_samples=1000,
            bootstrap_seed=20260925,
        ),
    )
    console.print_json(data={
        "mode": "v2.8-paired-provider-holdout-execution",
        "execution": execution.to_dict(),
        "report": report,
        "live_provider_measurement": False,
        "truth_boundary": (
            "synthetic paired adapters validate campaign mechanics only; authenticated provider "
            "measurement and a live 10x claim remain unproven"
        ),
    })


@app.command("v29-demo")
def v29_demo() -> None:
    """Prove signed paired-provider evidence without mislabeling synthetic execution as live."""
    from .live_holdout import AuthenticatedLiveHoldoutRunner
    from .paired_holdout import PairedMission
    from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier

    signer = Ed25519ReceiptSigner.generate(key_id="v29-demo-ephemeral")
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    missions = [
        PairedMission("fixture-a", 1, "shadow", {"task": "repair-a"}),
        PairedMission("fixture-b", 1, "experiment", {"task": "repair-b"}),
        PairedMission("fixture-c", 1, "holdout", {"task": "repair-c"}),
    ]
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer, seed=20260925
    )

    def synthetic_provider(mission, condition):
        frontier = condition == "frontier"
        return {
            "status": "verified",
            "metrics": {
                "completion_claims": 1, "false_completion_claims": 0,
                "provider_input_tokens": 9000 if frontier else 700,
                "provider_output_tokens": 1000 if frontier else 100,
                "decision_input_tokens": 1000 if frontier else 100,
                "decision_output_tokens": 100 if frontier else 0,
                "wall_time_ms": 1500 if frontier else 900,
            },
            "attestation": {
                "provider": "synthetic-demo", "model": "fixture-model",
                "provider_request_id": f"synthetic:{mission.case_id}:{condition}",
                "evidence_origin": "synthetic", "transport_security": "https",
                "authenticated": True,
            },
        }

    bundle = runner.run(missions=missions, run_condition=synthetic_provider)
    console.print_json(data={
        "mode": "v2.9-authenticated-live-ab-evidence-gate",
        "signed_receipts": len(bundle.signed_executions),
        "receipts_verify": bundle.verify(verifier),
        "live_provider_measurement": bundle.live_provider_measurement,
        "authenticated_live_ab_executed": False,
        "campaign_sha256": bundle.campaign_sha256,
        "truth_boundary": "synthetic receipts verify cryptographically but are not live-provider evidence",
    })


@app.command("live-campaign-v210")
def live_campaign_v210(
    manifest: Annotated[Path, typer.Argument(exists=True, readable=True)],
    incumbent: Annotated[str, typer.Option("--incumbent")],
    candidate: Annotated[str, typer.Option("--candidate")],
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("live-campaign-v210-results"),
    repeats: Annotated[int, typer.Option("--repeats", min=1)] = 6,
    shadow_pairs: Annotated[int, typer.Option("--shadow-pairs", min=0)] = 5,
    experiment_pairs: Annotated[int, typer.Option("--experiment-pairs", min=0)] = 5,
    holdout_pairs: Annotated[int, typer.Option("--holdout-pairs", min=1)] = 20,
    signing_key: Annotated[Path | None, typer.Option("--signing-key")] = None,
    key_id: Annotated[str, typer.Option("--key-id")] = "aftergraph-jev-live-v210",
    seed: Annotated[int, typer.Option("--seed")] = 20260925,
) -> None:
    """Run the real paired coding benchmark and seal provider request lineage as signed evidence."""
    import base64
    import os

    from .authenticated_benchmark import run_and_seal_authenticated_benchmark
    from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier

    if signing_key is not None:
        signer = Ed25519ReceiptSigner.load_private_key(key_id=key_id, path=signing_key)
    else:
        encoded = os.environ.get("JEV_EVIDENCE_SIGNING_KEY_B64", "")
        if not encoded:
            raise typer.BadParameter(
                "provide --signing-key or JEV_EVIDENCE_SIGNING_KEY_B64; ephemeral keys are forbidden for live evidence"
            )
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise typer.BadParameter("JEV_EVIDENCE_SIGNING_KEY_B64 is not valid base64") from exc
        if len(raw) != 32:
            raise typer.BadParameter("Ed25519 private key must decode to exactly 32 raw bytes")
        signer = Ed25519ReceiptSigner.from_private_key_bytes(key_id=key_id, raw=raw)

    bundle = run_and_seal_authenticated_benchmark(
        manifest_path=manifest,
        output_dir=output_dir,
        signer=signer,
        incumbent_condition=incumbent,
        candidate_condition=candidate,
        repeats=repeats,
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout_pairs,
        seed=seed,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    console.print_json(data={
        "mode": "v2.10-authenticated-live-benchmark",
        "bundle": str(output_dir / "authenticated-live-evidence.v1.json"),
        "public_key": str(output_dir / "evidence-public-key.raw"),
        "campaign_sha256": bundle.campaign_sha256,
        "signed_executions": len(bundle.signed_executions),
        "receipts_verify": bundle.verify(verifier),
        "live_provider_measurement": bundle.live_provider_measurement,
        "authenticated_live_ab_executed": bundle.live_provider_measurement and bundle.verify(verifier),
        "truth_boundary": (
            "live means deterministic coding verifier + provider-issued request lineage + authenticated HTTPS "
            "transport + locally signed evidence; it does not mean the provider itself signed the benchmark verdict"
        ),
    })


@app.command("verify-live-v210")
def verify_live_v210(
    bundle: Annotated[Path, typer.Argument(exists=True, readable=True)],
    public_key: Annotated[Path, typer.Option("--public-key", exists=True, readable=True)],
) -> None:
    """Verify a persisted v2.10 signed evidence bundle without provider credentials."""
    from .authenticated_benchmark import bundle_from_dict
    from .public_receipts import Ed25519ReceiptVerifier

    payload = json.loads(bundle.read_text(encoding="utf-8"))
    evidence = bundle_from_dict(payload)
    verifier = Ed25519ReceiptVerifier({evidence.signer_key_id: public_key.read_bytes()})
    ok = evidence.verify(verifier)
    console.print_json(data={
        "verified": ok,
        "campaign_sha256": evidence.campaign_sha256,
        "live_provider_measurement": evidence.live_provider_measurement,
        "signed_executions": len(evidence.signed_executions),
    })
    if not ok:
        raise typer.Exit(code=1)


@app.command("v212-demo")
def v212_demo() -> None:
    """Exercise the governed hierarchical/parallel multi-agent runtime without provider calls."""
    from .multi_agent import JoinMode, JoinPolicy, MultiAgentOrchestrator, MultiAgentPlan, SubagentSpec, SubagentTask

    agents = (
        SubagentSpec("researcher", "research", context_keys=frozenset({"mission"})),
        SubagentSpec("builder", "implementation", context_keys=frozenset({"mission"})),
        SubagentSpec("reviewer", "evaluation", context_keys=frozenset({"dependency_outputs"})),
    )
    tasks = (
        SubagentTask("research", "researcher", {"goal": "identify constraints"}, required_context_keys=frozenset({"mission"})),
        SubagentTask("build", "builder", {"goal": "produce candidate"}, required_context_keys=frozenset({"mission"})),
        SubagentTask("review", "reviewer", {"goal": "evaluate independent outputs"}, dependencies=("research", "build"), required_context_keys=frozenset({"dependency_outputs"})),
    )

    def executor(spec, task, context, trace_id, span_id):
        if task.task_id == "review":
            deps = context["dependency_outputs"]
            return {"status": "success", "confidence": 0.99, "output": {"reviewed": sorted(deps)}}
        return {"status": "success", "confidence": 0.9, "output": {"role": spec.role, "task": task.task_id}}

    result = MultiAgentOrchestrator(executor=executor).run(
        MultiAgentPlan(
            mission_id="v212-demo",
            orchestrator_id="jev-orchestrator",
            agents=agents,
            tasks=tasks,
            join_policy=JoinPolicy(JoinMode.ALL, min_confidence=0.5),
            join_task_ids=("review",),
            max_parallelism=2,
        ),
        context={"mission": "demonstrate governed multi-agent scheduling"},
    )
    console.print_json(data={
        "mode": "v2.12-governed-multi-agent",
        "accepted": result.accepted,
        "degraded": result.degraded,
        "trace_id": result.trace_id,
        "selected_task_ids": list(result.selected_task_ids),
        "total_attempts": result.total_attempts,
        "state_sha256": result.state_sha256,
        "provider_calls": 0,
        "live_provider_measurement": False,
        "truth_boundary": "demo validates orchestration semantics only; it does not execute real provider subagents or establish performance gains",
    })


if __name__ == "__main__":
    app()

@app.command("v213-demo")
def v213_demo() -> None:
    """Exercise heterogeneous routed subagents without provider calls or live claims."""
    from .heterogeneous_agents import (
        BackendBinding, BackendExecution, BackendIdentity, BackendKind, BackendRegistry,
        CompetenceRouter, DynamicTopologySelector, HeterogeneousSubagentExecutor, TopologyMode,
    )
    from .multi_agent import MultiAgentOrchestrator, MultiAgentPlan, SubagentSpec, SubagentStatus, SubagentTask
    from .public_receipts import Ed25519ReceiptSigner

    registry = BackendRegistry()
    def local_exec(identity, spec, task, context, trace_id, span_id):
        return BackendExecution(SubagentStatus.SUCCESS, {"backend": identity.backend_id, "task": task.task_id}, 0.9)
    registry.register(BackendIdentity("research-fast", BackendKind.LOCAL, "local", "research-fixture", capabilities=frozenset({"research"}), competence={"research": 0.8}), local_exec)
    registry.register(BackendIdentity("builder-strong", BackendKind.WORKER, "aftergraph-worker", "builder-fixture", capabilities=frozenset({"code"}), competence={"code": 0.95}), local_exec)
    router = CompetenceRouter(registry, (
        BackendBinding("researcher", ("research-fast",), frozenset({"research"}), "research", 0.5),
        BackendBinding("builder", ("builder-strong",), frozenset({"code"}), "code", 0.5),
    ))
    routed = HeterogeneousSubagentExecutor(
        registry=registry, router=router, signer=Ed25519ReceiptSigner.generate(key_id="v213-demo-ephemeral"),
        persistent_signing_key=False,
    )
    plan = MultiAgentPlan(
        mission_id="v213-demo", orchestrator_id="jev-orchestrator",
        agents=(SubagentSpec("researcher","research"), SubagentSpec("builder","implementation")),
        tasks=(SubagentTask("research","researcher",{}), SubagentTask("build","builder",{})),
        max_parallelism=2,
    )
    plan, topology = DynamicTopologySelector(max_parallelism=2).apply(plan, TopologyMode.AUTO)
    result = MultiAgentOrchestrator(executor=routed).run(plan, context={})
    console.print_json(data={
        "mode":"v2.13-heterogeneous-subagents",
        "accepted":result.accepted,
        "topology":topology.selected.value,
        "backend_count":len({r.receipt.payload["backend"]["backend_id"] for r in routed.receipts}),
        "receipts_verify":routed.verify_receipts(),
        "authenticated_live_provider_execution":routed.authenticated_live_provider_execution,
        "provider_calls":0,
        "live_provider_measurement":False,
        "truth_boundary":"heterogeneous routing and signed subagent receipts are verified locally; no live provider execution or performance claim is established",
    })
