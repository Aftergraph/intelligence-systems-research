from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from .jev_client import SystemOneResponse
from .local_decisions import LocalDecisionBackend
from .types import CandidateFile, DoneVerdict, ModelProfile, SafetyDecision


class DecisionBackend(Protocol):
    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
    ) -> SystemOneResponse: ...


class DecisionEngine:
    """The typed decision plane around the coding loop.

    The five core stations mirror the Jev working note:
    scope -> model choice -> run safety -> done/judgeable -> retention.
    """

    def __init__(self, backend: DecisionBackend, *, decision_model: str | None = None) -> None:
        self.backend = backend
        self.decision_model = decision_model
        self._metrics = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0.0,
        }

    def _ask(self, state: Any, questions: dict[str, dict[str, Any]]) -> SystemOneResponse:
        started = perf_counter()
        response = self.backend.system_one(
            state=state, questions=questions, model=self.decision_model
        )
        self._metrics["calls"] += 1
        self._metrics["input_tokens"] += int(response.usage.input_tokens)
        self._metrics["output_tokens"] += int(response.usage.output_tokens)
        self._metrics["latency_ms"] += (perf_counter() - started) * 1000.0
        return response

    def telemetry(self) -> dict[str, int | float]:
        return dict(self._metrics)

    def scope(self, *, task: str, candidates: list[CandidateFile], top_k: int = 8) -> list[CandidateFile]:
        if not candidates:
            return []
        questions: dict[str, dict[str, Any]] = {}
        state: dict[str, Any] = {"task": task, "candidates": {}}
        for i, candidate in enumerate(candidates):
            key = f"f{i}"
            state["candidates"][key] = {"path": candidate.path, "excerpt": candidate.excerpt[:4000]}
            questions[key] = {
                "type": "score",
                "instructions": "Score how useful this file/chunk is for solving the task. 0=irrelevant, 4=essential.",
                "criteria": ["irrelevant", "weak", "useful", "strong", "essential"],
            }
        response = self._ask(state, questions)
        ranked: list[CandidateFile] = []
        for i, candidate in enumerate(candidates):
            answer = response.score(f"f{i}")
            ranked.append(CandidateFile(candidate.path, candidate.excerpt, answer.score, answer.confidence))
        ranked.sort(key=lambda x: (x.score, x.confidence), reverse=True)
        return ranked[: max(1, top_k)]

    def choose_model(
        self,
        task: str,
        models: list[ModelProfile],
        *,
        frontier_required: bool = True,
        state: dict[str, Any] | None = None,
    ) -> ModelProfile:
        eligible = [m for m in models if (m.is_frontier or not frontier_required)]
        if not eligible:
            raise ValueError("No eligible frontier model is configured")
        criteria = {
            m.alias: (
                f"provider={m.provider}; model={m.model}; tier={m.tier}; "
                f"context={m.context_window or 'unknown'}; tools={m.supports_tools}"
            )
            for m in eligible
        }
        response = self._ask(
            {"task": task, "state": state or {}, "frontier_required": frontier_required},
            {
                "model": {
                    "type": "choice",
                    "instructions": "Choose the best configured model for this coding step. Prefer capability fit, then reliability; cost is secondary.",
                    "criteria": criteria,
                }
            },
        )
        selected = response.choice("model").choice
        try:
            return next(m for m in eligible if m.alias == selected)
        except StopIteration as exc:
            raise ValueError(f"Decision backend selected unknown/ineligible model alias {selected!r}") from exc

    def safe_to_run(self, *, task: str, command: str, policy: dict[str, float] | None = None) -> SafetyDecision:
        policy = policy or {}
        destructive_threshold = float(policy.get("destructive_block_threshold", 0.80))
        human_threshold = float(policy.get("human_threshold", 0.70))
        response = self._ask(
            {"task": task, "command": command},
            {
                "destructive": {
                    "type": "noul",
                    "instructions": "Is this action destructive, irreversible, credential-sensitive, production-impacting, or outside the repository?",
                },
                "needs_human": {
                    "type": "noul",
                    "instructions": "Should a human explicitly approve this action before execution?",
                },
            },
        )
        destructive = response.noul("destructive")
        human = response.noul("needs_human")
        if destructive >= destructive_threshold:
            action = "block"
            reason = f"destructive probability {destructive:.3f} >= {destructive_threshold:.3f}"
        elif human >= human_threshold:
            action = "confirm"
            reason = f"human-approval probability {human:.3f} >= {human_threshold:.3f}"
        else:
            action = "allow"
            reason = "typed risk gates below configured thresholds"
        return SafetyDecision(action, destructive, human, reason)

    def done(self, *, task: str, evidence: dict[str, Any]) -> DoneVerdict:
        exit_code = evidence.get("verification_exit_code")
        if exit_code is None:
            return DoneVerdict(False, 0.0, 0.0, "no fresh verification exit code")
        response = self._ask(
            {"task": task, "evidence": evidence},
            {
                "done": {
                    "type": "noul",
                    "instructions": "Does the supplied fresh evidence demonstrate that the task's requested observable outcome is complete?",
                },
                "judgeable": {
                    "type": "noul",
                    "instructions": "Is the evidence clear and sufficient enough to judge completion at all?",
                },
            },
        )
        done_p = response.noul("done")
        judgeable_p = response.noul("judgeable")
        verified = int(exit_code) == 0 and bool(evidence.get("evidence_fresh", False)) and done_p >= 0.85 and judgeable_p >= 0.80
        reason = (
            "fresh verification + typed completion gate passed"
            if verified
            else f"exit={exit_code}, done={done_p:.3f}, judgeable={judgeable_p:.3f}"
        )
        return DoneVerdict(verified, done_p, judgeable_p, reason)

    def retention(self, *, task: str, outputs: list[str]) -> list[str]:
        if not outputs:
            return []
        questions = {
            f"r{i}": {
                "type": "score",
                "instructions": "Score how much this exact tool output is worth retaining for the next coding steps. 0=drop, 1=truncate, 2=keep verbatim.",
                "criteria": ["drop", "truncate", "keep"],
            }
            for i in range(len(outputs))
        }
        response = self._ask({"task": task, "outputs": outputs}, questions)
        decisions: list[str] = []
        for i in range(len(outputs)):
            score = response.score(f"r{i}").score
            if score < 0.67:
                decisions.append("drop")
            elif score < 1.5:
                decisions.append("truncate")
            else:
                decisions.append("keep")
        return decisions

    def loop_probability(self, *, task: str, recent_actions: list[str]) -> float:
        response = self._ask(
            {"task": task, "recent_actions": recent_actions},
            {
                "looping": {
                    "type": "noul",
                    "instructions": "Is the agent repeating itself without meaningful progress?",
                }
            },
        )
        return response.noul("looping")

# Backwards/UX name: this is intentionally *not* Jev. It is an explicit local
# heuristic fallback for demos and offline tests only.
HeuristicDecisionBackend = LocalDecisionBackend
