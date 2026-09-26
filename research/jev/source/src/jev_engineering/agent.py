from __future__ import annotations

import hashlib
import json
import re
import uuid
from time import perf_counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .context import collect_candidates, format_selected_context
from .context_compiler import ContextCompiler, compile_candidate_files
from .decisions import DecisionEngine
from .model_registry import ModelRegistry
from .intelligence_fabric import IntelligenceFabric
from .proof_graph import EvidenceClaim, ProofGraph, workspace_tree_hash
from .providers.base import ProviderFactory
from .tools import ApprovalRequired, RepoTools, ToolPolicyError
from .telemetry import extract_provider_request_id, extract_token_usage
from .verification_portfolio import VerificationPortfolioOptimizer, VerificationRequirement
from .types import AgentResult, AgentStatus, DoneVerdict, SafetyDecision, ToolCall


SYSTEM_INSTRUCTIONS = """You are the frontier coding model inside a Jev-governed harness.
Your job is to implement the user's coding task using repository tools.
Rules:
- Read before writing when context is insufficient.
- Make minimal coherent edits; preserve unrelated work.
- Never claim success merely because you emitted text. The harness independently verifies.
- Do not request or expose secrets. Do not write outside the repository.
- If a tool is blocked, adapt using safe repository-local methods; do not bypass policy.
- When implementation is complete, return a concise factual summary and let the harness verify it.
"""

_READ_ONLY = {"read_file", "search_text", "list_files", "git_diff"}
_MUTATING = {"write_file", "replace_text", "run_command"}


class CodingAgent:
    def __init__(
        self,
        *,
        workspace: str | Path,
        decisions: DecisionEngine,
        registry: ModelRegistry,
        provider_factory: ProviderFactory,
        verify_command: str,
        max_turns: int = 24,
        scope_top_k: int = 8,
        frontier_required: bool = True,
        command_mode: str = "verify_only",
        audit_path: str | Path | None = None,
        retention_every: int = 6,
        loop_check_every: int = 4,
        policy: dict[str, float] | None = None,
        approval_handler: Callable[[str, dict[str, Any], str], bool] | None = None,
        intelligence_fabric: IntelligenceFabric | None = None,
        generation_required_vsr: float = 0.0,
        context_compiler: ContextCompiler | None = None,
        context_token_budget: int = 0,
        proof_graph: ProofGraph | None = None,
        proof_graph_path: str | Path | None = None,
        verification_optimizer: VerificationPortfolioOptimizer | None = None,
        verification_requirement: VerificationRequirement | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.decisions = decisions
        self.registry = registry
        self.provider_factory = provider_factory
        self.verify_command = verify_command
        self.max_turns = max_turns
        self.scope_top_k = scope_top_k
        self.frontier_required = frontier_required
        self.tools = RepoTools(self.workspace, command_mode=command_mode)
        self.audit = AuditLog(audit_path)
        self.retention_every = retention_every
        self.loop_check_every = loop_check_every
        self.policy = policy or {}
        self.approval_handler = approval_handler
        self.intelligence_fabric = intelligence_fabric
        self.generation_required_vsr = float(generation_required_vsr)
        if not 0.0 <= self.generation_required_vsr <= 1.0:
            raise ValueError("generation_required_vsr must be between 0 and 1")
        self.context_compiler = context_compiler
        self.context_token_budget = int(context_token_budget)
        if self.context_token_budget < 0:
            raise ValueError("context_token_budget must be non-negative")
        self.proof_graph_path = Path(proof_graph_path) if proof_graph_path else None
        if proof_graph is not None:
            self.proof_graph = proof_graph
        elif self.proof_graph_path is not None and self.proof_graph_path.exists():
            self.proof_graph = ProofGraph.load(self.proof_graph_path)
        else:
            self.proof_graph = ProofGraph()
        if self.workspace.exists():
            self.proof_graph.observe_dependency("workspace_tree", workspace_tree_hash(self.workspace))
        self.verification_optimizer = verification_optimizer
        self.verification_requirement = verification_requirement
        if (self.verification_optimizer is None) != (self.verification_requirement is None):
            raise ValueError("verification optimizer and requirement must be configured together")
        self._selected_generation_bid = None
        self._competence_outcome_recorded = False
        self._shadow_finalized = False
        self._run_started = perf_counter()
        self._provider_request_ids: list[str] = []
        self._metrics: dict[str, int | float] = {
            "provider_calls": 0,
            "provider_input_tokens": 0,
            "provider_output_tokens": 0,
            "provider_cached_input_tokens": 0,
            "provider_latency_ms": 0.0,
            "tool_calls": 0,
            "verifier_runs": 0,
            "verification_latency_ms": 0.0,
            "completion_claims": 0,
            "false_completion_claims": 0,
        }

    def _result(self, status: AgentStatus, trace_id: str, *, turns: int = 0, **kwargs: Any) -> AgentResult:
        if (
            self.intelligence_fabric is not None
            and self._selected_generation_bid is not None
            and not self._competence_outcome_recorded
            and status in {AgentStatus.VERIFIED, AgentStatus.MAX_TURNS}
        ):
            self.intelligence_fabric.record_outcome(
                self._selected_generation_bid,
                success=status is AgentStatus.VERIFIED,
            )
            self._competence_outcome_recorded = True
        if (
            not self._shadow_finalized
            and status in {AgentStatus.VERIFIED, AgentStatus.FAILED, AgentStatus.MAX_TURNS}
            and hasattr(self.decisions, "finalize_mission")
        ):
            summary = self.decisions.finalize_mission(
                verified_outcome=status is AgentStatus.VERIFIED,
                trace_id=trace_id,
            )
            self._shadow_finalized = True
            self.audit.append("shadow.finalized", **summary.to_dict())
        decision = self.decisions.telemetry()
        provider_tokens = int(self._metrics["provider_input_tokens"]) + int(self._metrics["provider_output_tokens"])
        decision_tokens = int(decision["input_tokens"]) + int(decision["output_tokens"])
        denominator = provider_tokens + decision_tokens
        metrics = dict(self._metrics)
        metrics["provider_request_count"] = len(self._provider_request_ids)
        metrics.update(
            {
                "decision_calls": int(decision["calls"]),
                "decision_input_tokens": int(decision["input_tokens"]),
                "decision_output_tokens": int(decision["output_tokens"]),
                "decision_latency_ms": float(decision["latency_ms"]),
                "control_plane_token_tax": (decision_tokens / denominator) if denominator else 0.0,
                "wall_time_ms": (perf_counter() - self._run_started) * 1000.0,
            }
        )
        if self.intelligence_fabric is not None:
            metrics.update(
                {f"fabric_{key}": value
                 for key, value in self.intelligence_fabric.telemetry().items()}
            )
        metrics.update({f"proof_{key}": value for key, value in self.proof_graph.telemetry().items()})
        if hasattr(self.decisions, "shadow_telemetry"):
            metrics.update(
                {f"shadow_{key}": value for key, value in self.decisions.shadow_telemetry().items()}
            )
        if self.proof_graph_path is not None:
            self.proof_graph.save(self.proof_graph_path)
        return AgentResult(
            status=status,
            trace_id=trace_id,
            turns=turns,
            audit_path=str(self.audit.path) if self.audit.path else None,
            events=list(self.audit.events),
            metrics=metrics,
            provider_request_ids=list(self._provider_request_ids),
            **kwargs,
        )

    @staticmethod
    def _argument_summary(call: ToolCall) -> dict[str, Any]:
        summary: dict[str, Any] = {"keys": sorted(call.arguments.keys())}
        if "path" in call.arguments:
            summary["path"] = str(call.arguments["path"])
        if "command" in call.arguments:
            command = str(call.arguments["command"])
            summary["command_sha256"] = hashlib.sha256(command.encode("utf-8")).hexdigest()
            summary["command_bytes"] = len(command.encode("utf-8"))
        if "content" in call.arguments:
            content = str(call.arguments["content"])
            summary["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            summary["content_bytes"] = len(content.encode("utf-8"))
        return summary


    @staticmethod
    def _redacted_command_for_decision(command: str) -> str:
        """Preserve command semantics for Jev while removing common secret literals."""
        text = command
        text = re.sub(
            r"(?i)(\b(?:authorization|api[-_]?key|token|password|secret)\b\s*(?:=|:)\s*)[^\s;]+",
            r"\1[REDACTED]",
            text,
        )
        text = re.sub(
            r"(?i)(--?(?:api[-_]?key|token|password|secret|authorization)(?:=|\s+))[^\s;]+",
            r"\1[REDACTED]",
            text,
        )
        text = re.sub(
            r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD))=([^\s;]+)",
            r"\1=[REDACTED]",
            text,
        )
        text = re.sub(r"\b(?:sk|ghp|github_pat|ts)_[A-Za-z0-9_-]{8,}\b", "[REDACTED]", text)
        text = re.sub(r"(?i)(https?://[^:/@\s]+:)[^@/\s]+@", r"\1[REDACTED]@", text)
        return text[:8000]

    def _gate_action(self, task: str, call: ToolCall) -> SafetyDecision:
        try:
            deterministic = self.tools.preflight(call.name, call.arguments)
        except ToolPolicyError as exc:
            return SafetyDecision("block", 1.0, 1.0, f"deterministic policy: {exc}")
        if deterministic == "confirm":
            return SafetyDecision("confirm", 0.0, 1.0, "deterministic consequential-action policy")
        if call.name in _READ_ONLY:
            return SafetyDecision("allow", 0.0, 0.0, "deterministic read-only tool")
        if (
            deterministic == "allow"
            and call.name in {"write_file", "replace_text"}
            and bool(self.policy.get("repo_local_write_auto_allow", False))
        ):
            return SafetyDecision(
                "allow",
                0.0,
                0.0,
                "explicit policy auto-allows deterministic repository-local file edits",
            )
        if call.name not in _MUTATING:
            return SafetyDecision("block", 1.0, 1.0, "tool is outside the governed tool surface")
        # File-write content stays hashed, but shell semantics must remain visible to
        # Jev's safety judgment. Common credential literals are redacted first.
        if call.name == "run_command":
            action_repr = json.dumps(
                {
                    "tool": call.name,
                    "command": self._redacted_command_for_decision(str(call.arguments.get("command", ""))),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        else:
            action_repr = json.dumps(
                {"tool": call.name, "arguments": self._argument_summary(call)},
                ensure_ascii=False,
                sort_keys=True,
            )
        return self.decisions.safe_to_run(task=task, command=action_repr, policy=self.policy)

    def _completion_verdict(self, *, task: str, evidence: dict[str, Any]) -> DoneVerdict:
        if (
            bool(self.policy.get("authoritative_verifier", False))
            and int(evidence.get("verification_exit_code", 1)) == 0
            and bool(evidence.get("evidence_fresh", False))
        ):
            return DoneVerdict(
                True,
                1.0,
                1.0,
                "fresh preregistered deterministic verifier passed under authoritative-verifier policy",
            )
        return self.decisions.done(task=task, evidence=evidence)

    def _create_session(self, model: Any, task: str, context: str):
        return self.provider_factory.create(
            model,
            task=task,
            context=context,
            tools=self.tools.specs(),
            instructions=SYSTEM_INSTRUCTIONS,
        )

    @staticmethod
    def _retained_context(base_context: str, retained: list[str]) -> str:
        if not retained:
            return base_context
        return base_context + "\n\n### RETAINED TOOL EVIDENCE (typed compaction)\n" + "\n".join(retained)

    def run(self, task: str) -> AgentResult:
        if not self.workspace.exists() or not self.workspace.is_dir():
            raise FileNotFoundError(self.workspace)
        trace_id = uuid.uuid4().hex
        self.audit.append("mission.started", trace_id=trace_id, task=task, workspace=str(self.workspace))

        try:
            candidates = collect_candidates(self.workspace, task)
            selected = self.decisions.scope(task=task, candidates=candidates, top_k=self.scope_top_k)
            self.audit.append(
                "decision.scope",
                candidates=len(candidates),
                selected=[{"path": x.path, "score": x.score, "confidence": x.confidence} for x in selected],
            )
            if self.context_compiler is not None and self.context_token_budget > 0:
                projection = compile_candidate_files(
                    selected,
                    token_budget=self.context_token_budget,
                    compiler=self.context_compiler,
                )
                base_context = projection.render()
                self.audit.append(
                    "context.compiled",
                    projection_id=projection.projection_id,
                    candidates=len(selected),
                    selected=[item.key for item in projection.selected],
                    excluded=projection.excluded,
                    token_budget=projection.token_budget,
                    tokens_used=projection.tokens_used,
                    candidate_tokens=projection.candidate_tokens,
                    useful_context_ratio=projection.useful_context_ratio,
                    compression_ratio=projection.compression_ratio,
                )
            else:
                base_context = format_selected_context(selected)
            eligible = self.registry.eligible(frontier_required=self.frontier_required, require_tools=True)
            if self.intelligence_fabric is not None:
                bid = self.intelligence_fabric.select(
                    capability="generation",
                    required_vsr=self.generation_required_vsr,
                )
                model_alias = str(bid.metadata.get("model_alias") or "").strip()
                if not model_alias:
                    raise RuntimeError(
                        f"generation bid {bid.strategy_id!r} has no model_alias metadata"
                    )
                try:
                    model = next(candidate for candidate in eligible if candidate.alias == model_alias)
                except StopIteration as exc:
                    raise RuntimeError(
                        f"generation bid {bid.strategy_id!r} selected ineligible model alias "
                        f"{model_alias!r}"
                    ) from exc
                self.intelligence_fabric.record_selection(bid)
                self._selected_generation_bid = bid
                self.audit.append(
                    "decision.intelligence_bid",
                    strategy_id=bid.strategy_id,
                    source=bid.source,
                    capability="generation",
                    predicted_vsr=bid.predicted_vsr,
                    estimated_cost_usd=bid.estimated_cost_usd,
                    estimated_latency_ms=bid.estimated_latency_ms,
                    frontier_input_tokens=bid.frontier_input_tokens,
                    frontier_output_tokens=bid.frontier_output_tokens,
                    model_alias=model_alias,
                )
            else:
                model = self.decisions.choose_model(
                    task,
                    eligible,
                    frontier_required=self.frontier_required,
                    state={"selected_files": [x.path for x in selected]},
                )
            if self.frontier_required and not model.is_frontier:
                raise RuntimeError("Frontier-model invariant violated")
            self.audit.append(
                "decision.model",
                alias=model.alias,
                provider=model.provider,
                model=model.model,
                tier=model.tier,
                transport=model.transport,
            )
            session = self._create_session(model, task, base_context)
        except Exception as exc:
            self.audit.append("mission.failed", stage="initialization", error=repr(exc))
            return self._result(AgentStatus.FAILED, trace_id, message=f"Initialization failed: {exc}")

        pending_results: dict[str, Any] | None = None
        retained_outputs: list[str] = []
        recent_actions: list[str] = []
        final_text = ""
        latest_verification: dict[str, Any] | None = None

        for turn_index in range(1, self.max_turns + 1):
            try:
                provider_started = perf_counter()
                turn = session.step(pending_results)
                provider_latency_ms = (perf_counter() - provider_started) * 1000.0
                usage = extract_token_usage(turn.raw)
                provider_request_id = extract_provider_request_id(turn.raw)
                if provider_request_id is not None:
                    self._provider_request_ids.append(provider_request_id)
                self._metrics["provider_calls"] += 1
                self._metrics["provider_input_tokens"] += usage.input_tokens
                self._metrics["provider_output_tokens"] += usage.output_tokens
                self._metrics["provider_cached_input_tokens"] += usage.cached_input_tokens
                self._metrics["provider_latency_ms"] += provider_latency_ms
                self.audit.append(
                    "provider.usage",
                    turn=turn_index,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cached_input_tokens=usage.cached_input_tokens,
                    latency_ms=provider_latency_ms,
                    provider_request_id=provider_request_id,
                )
            except Exception as exc:
                self.audit.append("mission.failed", stage="provider_step", turn=turn_index, error=repr(exc))
                return self._result(
                    AgentStatus.FAILED,
                    trace_id,
                    turns=turn_index,
                    model_alias=model.alias,
                    model=model.model,
                    final_text=final_text,
                    message=f"Provider step failed: {exc}",
                )
            pending_results = None
            if turn.text:
                final_text = turn.text
                self.audit.append("model.text", turn=turn_index, chars=len(turn.text))

            if turn.tool_calls:
                pending_results = {}
                this_turn_records: list[str] = []
                for call in turn.tool_calls:
                    self._metrics["tool_calls"] += 1
                    summary = self._argument_summary(call)
                    recent_actions.append(f"{call.name}:{json.dumps(summary, sort_keys=True)}")
                    decision = self._gate_action(task, call)
                    self.audit.append(
                        "decision.safe_to_run",
                        tool=call.name,
                        action=decision.action,
                        destructive_probability=decision.destructive_probability,
                        human_probability=decision.human_probability,
                        reason=decision.reason,
                    )
                    safety_action = "allow"
                    if decision.action == "confirm":
                        approved = bool(
                            self.approval_handler
                            and self.approval_handler(call.name, call.arguments, decision.reason)
                        )
                        if not approved:
                            self.audit.append("mission.needs_human", tool=call.name, argument_summary=summary)
                            return self._result(
                                AgentStatus.NEEDS_HUMAN,
                                trace_id,
                                turns=turn_index,
                                model_alias=model.alias,
                                model=model.model,
                                final_text=final_text,
                                message=f"Approval required for {call.name}: {decision.reason}",
                            )
                        self.audit.append("approval.granted", tool=call.name, argument_summary=summary)
                        safety_action = "approved"
                    elif decision.action == "block":
                        pending_results[call.id] = {
                            "error": "blocked_by_governed_safety_gate",
                            "reason": decision.reason,
                        }
                        self.audit.append("tool.blocked", tool=call.name, call_id=call.id)
                        continue
                    try:
                        result = self.tools.execute(call.name, call.arguments, safety_action=safety_action)
                    except (ToolPolicyError, ApprovalRequired, OSError, TypeError, ValueError) as exc:
                        result = {"error": type(exc).__name__, "message": str(exc)}
                    pending_results[call.id] = result
                    record = json.dumps(
                        {"tool": call.name, "call_id": call.id, "result": result},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    this_turn_records.append(record)
                    retained_outputs.append(record)
                    tool_ok = not isinstance(result, dict) or "error" not in result
                    self.audit.append(
                        "tool.result",
                        tool=call.name,
                        call_id=call.id,
                        ok=tool_ok,
                        exit_code=result.get("exit_code") if isinstance(result, dict) else None,
                    )
                    if tool_ok and call.name in {"write_file", "replace_text"}:
                        current_tree = workspace_tree_hash(self.workspace)
                        invalidated = self.proof_graph.observe_dependency("workspace_tree", current_tree)
                        if invalidated:
                            self.audit.append(
                                "proof.invalidated",
                                dependency="workspace_tree",
                                claims=sorted(invalidated),
                            )

                # Real compaction: score exact tool records, keep/truncate/drop, then restart the
                # provider session so discarded history is not kept in the frontier context.
                if self.retention_every > 0 and turn_index % self.retention_every == 0 and retained_outputs:
                    window = retained_outputs[-8:]
                    policies = self.decisions.retention(task=task, outputs=window)
                    compacted: list[str] = []
                    for item, retention in zip(window, policies, strict=True):
                        if retention == "keep":
                            compacted.append(item)
                        elif retention == "truncate":
                            compacted.append(item[:1200] + ("…" if len(item) > 1200 else ""))
                    retained_outputs = compacted
                    self.audit.append("decision.retention", decisions=policies, retained=len(compacted))
                    session = self._create_session(
                        model,
                        task,
                        self._retained_context(base_context, retained_outputs),
                    )
                    pending_results = None

                if self.loop_check_every > 0 and turn_index % self.loop_check_every == 0 and len(recent_actions) >= 4:
                    p_loop = self.decisions.loop_probability(task=task, recent_actions=recent_actions[-6:])
                    self.audit.append("decision.loop", probability=p_loop)
                    if p_loop >= 0.85:
                        return self._result(
                            AgentStatus.NEEDS_HUMAN,
                            trace_id,
                            turns=turn_index,
                            model_alias=model.alias,
                            model=model.model,
                            final_text=final_text,
                            message="Loop detector escalated repeated non-progress to a human.",
                        )
                continue

            # A natural-language finish is only RUNNING -> VERIFYING, never RUNNING -> VERIFIED.
            self._metrics["completion_claims"] += 1
            try:
                verification_started = perf_counter()
                if self.verification_optimizer is not None and self.verification_requirement is not None:
                    plan = self.verification_optimizer.plan(self.verification_requirement)
                    commands = [
                        self.verify_command if method.command == "$PRIMARY_VERIFY" else method.command
                        for method in plan.methods
                    ]
                    self.audit.append("verification.plan", **plan.to_dict())
                else:
                    commands = [self.verify_command]
                verification_results = [
                    self.tools.run_command(command, safety_action="allow") for command in commands
                ]
                self._metrics["verification_latency_ms"] += (perf_counter() - verification_started) * 1000.0
                self._metrics["verifier_runs"] += len(verification_results)
                combined_exit = 0 if all(int(result["exit_code"]) == 0 for result in verification_results) else 1
                combined_output = "\n\n".join(
                    f"### verifier {index + 1}: {commands[index]}\n{result['output']}"
                    for index, result in enumerate(verification_results)
                )
                latest_verification = {
                    "exit_code": combined_exit,
                    "output": combined_output,
                    "command_sha256": hashlib.sha256("\n".join(commands).encode("utf-8")).hexdigest(),
                }
            except (ToolPolicyError, ApprovalRequired) as exc:
                self.audit.append("mission.failed", stage="verification_policy", error=str(exc))
                return self._result(
                    AgentStatus.FAILED,
                    trace_id,
                    turns=turn_index,
                    model_alias=model.alias,
                    model=model.model,
                    final_text=final_text,
                    message=f"Verifier command rejected by deterministic policy: {exc}",
                )
            if int(latest_verification["exit_code"]) != 0:
                self._metrics["false_completion_claims"] += 1
            self.audit.append(
                "verification.executed",
                command_sha256=latest_verification.get("command_sha256"),
                exit_code=latest_verification["exit_code"],
                output_tail=latest_verification["output"][-4000:],
                fresh=True,
            )
            tree_hash = workspace_tree_hash(self.workspace)
            claim = EvidenceClaim.mint(
                subject=f"sha256:{tree_hash}",
                predicate="verification_passed",
                verifier="deterministic:repo-verifier",
                method=" + ".join(commands),
                verdict=int(latest_verification["exit_code"]) == 0,
                dependencies={"workspace_tree": tree_hash},
                metadata={"trace_id": trace_id, "turn": turn_index},
            )
            self.proof_graph.add_claim(claim)
            evidence_fresh = self.proof_graph.is_fresh(claim.claim_id)
            self.audit.append(
                "proof.claim",
                claim_id=claim.claim_id,
                subject=claim.subject,
                predicate=claim.predicate,
                verdict=claim.verdict,
                fresh=evidence_fresh,
            )
            evidence = {
                "verification_exit_code": latest_verification["exit_code"],
                "verification_output": latest_verification["output"],
                "evidence_fresh": evidence_fresh,
                "evidence_claim_id": claim.claim_id,
                "evidence_subject": claim.subject,
            }
            verdict = self._completion_verdict(task=task, evidence=evidence)
            self.audit.append(
                "decision.done",
                verified=verdict.verified,
                done_probability=verdict.done_probability,
                judgeable_probability=verdict.judgeable_probability,
                reason=verdict.reason,
            )
            if verdict.verified:
                acceptance = EvidenceClaim.mint(
                    subject=f"mission:{trace_id}",
                    predicate="mission_acceptance",
                    verifier="harness:completion-gate",
                    method="typed-done+subject-bound-evidence",
                    verdict=True,
                    dependencies={"workspace_tree": tree_hash},
                    parent_claim_ids=(claim.claim_id,),
                    metadata={
                        "done_probability": verdict.done_probability,
                        "judgeable_probability": verdict.judgeable_probability,
                    },
                )
                self.proof_graph.add_claim(acceptance)
                if not self.proof_graph.accepts([acceptance.claim_id]):
                    self.audit.append(
                        "mission.failed",
                        stage="proof_acceptance",
                        acceptance_claim_id=acceptance.claim_id,
                    )
                    return self._result(
                        AgentStatus.FAILED,
                        trace_id,
                        turns=turn_index,
                        model_alias=model.alias,
                        model=model.model,
                        final_text=final_text,
                        message="Mission acceptance proof graph failed closed.",
                    )
                self.audit.append(
                    "mission.verified",
                    trace_id=trace_id,
                    acceptance_claim_id=acceptance.claim_id,
                    evidence_claim_id=claim.claim_id,
                )
                return self._result(
                    AgentStatus.VERIFIED,
                    trace_id,
                    turns=turn_index,
                    model_alias=model.alias,
                    model=model.model,
                    verification_exit_code=latest_verification["exit_code"],
                    verification_output=latest_verification["output"],
                    final_text=final_text,
                    message=final_text,
                )

            # Any failed/unjudgeable completion gate returns exact fresh evidence to a new frontier
            # session. This also avoids synthetic function-call IDs that some provider APIs reject.
            diagnostic = (
                base_context
                + "\n\n### FRESH VERIFICATION EVIDENCE — NOT VERIFIED\n"
                + latest_verification["output"][-12000:]
                + f"\nexit_code={latest_verification['exit_code']}\n"
                + f"done_probability={verdict.done_probability:.3f}\n"
                + f"judgeable_probability={verdict.judgeable_probability:.3f}\n"
            )
            session = self._create_session(model, task, self._retained_context(diagnostic, retained_outputs))
            pending_results = None

        self.audit.append("mission.max_turns", max_turns=self.max_turns)
        return self._result(
            AgentStatus.MAX_TURNS,
            trace_id,
            turns=self.max_turns,
            model_alias=model.alias,
            model=model.model,
            verification_exit_code=latest_verification.get("exit_code") if latest_verification else None,
            verification_output=latest_verification.get("output", "") if latest_verification else "",
            final_text=final_text,
            message="Maximum turns exhausted without verified completion.",
        )
