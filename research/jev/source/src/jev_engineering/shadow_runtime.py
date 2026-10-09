from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable

from .learning import LearningCandidate, LearningRatchet, LearningState, PromotionPolicy


def _canonical(value: Any) -> Any:
    """Return a JSON-stable representation of decision-relevant output only."""
    if is_dataclass(value):
        name = type(value).__name__
        if name == "CandidateFile":
            return {
                "path": str(getattr(value, "path", "")),
                "score": round(float(getattr(value, "score", 0.0)), 9),
                "confidence": round(float(getattr(value, "confidence", 0.0)), 9),
            }
        if name == "ModelProfile":
            return {"alias": str(getattr(value, "alias", ""))}
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    # ModelProfile and similar objects are dataclasses today, but keep a safe
    # last-resort identity projection rather than serializing arbitrary state.
    alias = getattr(value, "alias", None)
    if isinstance(alias, str):
        return {"alias": alias}
    return repr(value)


@dataclass(frozen=True, slots=True)
class ShadowDecisionRecord:
    sequence: int
    station: str
    incumbent_output: Any
    candidate_output: Any | None
    equivalent: bool
    active_strategy: str
    candidate_error: str | None = None


@dataclass(frozen=True, slots=True)
class ShadowMissionSummary:
    trace_id: str
    incumbent_strategy: str
    candidate_strategy: str
    shadow_calls: int
    agreements: int
    candidate_errors: int
    path_equivalent: bool
    candidate_outcome_observable: bool
    incumbent_verified_outcome: bool
    candidate_verified_outcome: bool | None

    @property
    def agreement_rate(self) -> float:
        return self.agreements / self.shadow_calls if self.shadow_calls else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "trace_id": self.trace_id,
            "incumbent_strategy": self.incumbent_strategy,
            "candidate_strategy": self.candidate_strategy,
            "shadow_calls": self.shadow_calls,
            "agreements": self.agreements,
            "agreement_rate": self.agreement_rate,
            "candidate_errors": self.candidate_errors,
            "path_equivalent": self.path_equivalent,
            "candidate_outcome_observable": self.candidate_outcome_observable,
            "incumbent_verified_outcome": self.incumbent_verified_outcome,
            "candidate_verified_outcome": self.candidate_verified_outcome,
        }


class ShadowDecisionEngine:
    """Run a candidate decision plane without granting it execution authority.

    Every public decision returns the incumbent result. Candidate failures and
    divergences are observations only. A verified mission outcome is attributed
    to the candidate only when every shadowed decision is path-equivalent; if the
    candidate would have changed the path, its counterfactual outcome remains
    unknown rather than being imputed.
    """

    def __init__(
        self,
        *,
        incumbent: Any,
        candidate: Any,
        incumbent_strategy: str,
        candidate_strategy: str,
        log_path: str | Path | None = None,
        promotion_registry: "PromotionRegistry | None" = None,
    ) -> None:
        if not incumbent_strategy.strip() or not candidate_strategy.strip():
            raise ValueError("strategy ids must be non-empty")
        self.incumbent = incumbent
        self.candidate = candidate
        self.incumbent_strategy = incumbent_strategy
        self.candidate_strategy = candidate_strategy
        self.log_path = Path(log_path) if log_path else None
        self.promotion_registry = promotion_registry
        self.records: list[ShadowDecisionRecord] = []
        self._finalized = False
        self._summary: ShadowMissionSummary | None = None

    def _observe(self, station: str, incumbent_call: Callable[[], Any], candidate_call: Callable[[], Any]) -> Any:
        incumbent_result = incumbent_call()
        incumbent_output = _canonical(incumbent_result)
        candidate_output = None
        candidate_result = None
        error = None
        equivalent = False
        preferred = self.promotion_registry.preferred(station) if self.promotion_registry is not None else None
        candidate_active = preferred == self.candidate_strategy
        try:
            candidate_result = candidate_call()
            candidate_output = _canonical(candidate_result)
            equivalent = candidate_output == incumbent_output
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            if candidate_active:
                # A promoted route is production behavior. Never silently fall
                # back to the old route because that would hide a regression.
                raise RuntimeError(
                    f"promoted decision strategy {self.candidate_strategy!r} failed at {station!r}: {error}"
                ) from exc
        active_strategy = self.candidate_strategy if candidate_active else self.incumbent_strategy
        self.records.append(
            ShadowDecisionRecord(
                sequence=len(self.records) + 1,
                station=station,
                incumbent_output=incumbent_output,
                candidate_output=candidate_output,
                equivalent=equivalent,
                active_strategy=active_strategy,
                candidate_error=error,
            )
        )
        if candidate_active:
            return candidate_result
        return incumbent_result

    def scope(self, *, task: str, candidates: list[Any], top_k: int = 8) -> list[Any]:
        return self._observe(
            "scope",
            lambda: self.incumbent.scope(task=task, candidates=candidates, top_k=top_k),
            lambda: self.candidate.scope(task=task, candidates=candidates, top_k=top_k),
        )

    def choose_model(self, task: str, models: list[Any], *, frontier_required: bool = True, state: dict[str, Any] | None = None) -> Any:
        return self._observe(
            "choose_model",
            lambda: self.incumbent.choose_model(task, models, frontier_required=frontier_required, state=state),
            lambda: self.candidate.choose_model(task, models, frontier_required=frontier_required, state=state),
        )

    def safe_to_run(self, *, task: str, command: str, policy: dict[str, float] | None = None) -> Any:
        return self._observe(
            "safe_to_run",
            lambda: self.incumbent.safe_to_run(task=task, command=command, policy=policy),
            lambda: self.candidate.safe_to_run(task=task, command=command, policy=policy),
        )

    def done(self, *, task: str, evidence: dict[str, Any]) -> Any:
        return self._observe(
            "done",
            lambda: self.incumbent.done(task=task, evidence=evidence),
            lambda: self.candidate.done(task=task, evidence=evidence),
        )

    def retention(self, *, task: str, outputs: list[str]) -> list[str]:
        return self._observe(
            "retention",
            lambda: self.incumbent.retention(task=task, outputs=outputs),
            lambda: self.candidate.retention(task=task, outputs=outputs),
        )

    def loop_probability(self, *, task: str, recent_actions: list[str]) -> float:
        return self._observe(
            "loop_probability",
            lambda: self.incumbent.loop_probability(task=task, recent_actions=recent_actions),
            lambda: self.candidate.loop_probability(task=task, recent_actions=recent_actions),
        )

    def telemetry(self) -> dict[str, int | float]:
        # Preserve incumbent accounting as the production control-plane cost.
        return dict(self.incumbent.telemetry())

    def shadow_telemetry(self) -> dict[str, int | float]:
        raw = self.candidate.telemetry()
        return {
            "calls": len(self.records),
            "agreements": sum(1 for row in self.records if row.equivalent),
            "errors": sum(1 for row in self.records if row.candidate_error is not None),
            "input_tokens": int(raw.get("input_tokens", 0)),
            "output_tokens": int(raw.get("output_tokens", 0)),
            "latency_ms": float(raw.get("latency_ms", 0.0)),
        }

    def finalize_mission(self, *, verified_outcome: bool, trace_id: str) -> ShadowMissionSummary:
        if self._finalized:
            if self._summary is None:
                raise RuntimeError("shadow mission finalized without summary")
            return self._summary
        errors = sum(1 for row in self.records if row.candidate_error is not None)
        agreements = sum(1 for row in self.records if row.equivalent)
        path_equivalent = bool(self.records) and errors == 0 and agreements == len(self.records)
        candidate_path_observable = bool(self.records) and errors == 0 and all(
            row.active_strategy == self.candidate_strategy or row.equivalent for row in self.records
        )
        candidate_outcome = bool(verified_outcome) if candidate_path_observable else None
        summary = ShadowMissionSummary(
            trace_id=trace_id,
            incumbent_strategy=self.incumbent_strategy,
            candidate_strategy=self.candidate_strategy,
            shadow_calls=len(self.records),
            agreements=agreements,
            candidate_errors=errors,
            path_equivalent=path_equivalent,
            candidate_outcome_observable=candidate_path_observable,
            incumbent_verified_outcome=bool(verified_outcome),
            candidate_verified_outcome=candidate_outcome,
        )
        self._finalized = True
        self._summary = summary
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                **summary.to_dict(),
                "observed_at": time.time(),
                "records": [asdict(row) for row in self.records],
            }
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return summary


class PromotionRegistry:
    """Evidence-gated preferred strategy registry.

    A preferred route never grants authority and never bypasses capability,
    quality, or budget gates. It only biases selection after a candidate has
    passed the complete LearningRatchet and PromotionPolicy.
    """

    def __init__(self, *, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._routes: dict[str, dict[str, Any]] = {}
        self._quarantine: dict[str, dict[str, Any]] = {}

    def preferred(self, decision_family: str) -> str | None:
        row = self._routes.get(decision_family)
        return str(row["strategy_id"]) if row else None

    def register(self, candidate: LearningCandidate) -> None:
        if candidate.state is not LearningState.PROMOTED:
            raise RuntimeError("only promoted candidates may enter the route registry")
        self._routes[candidate.decision_family] = {
            "strategy_id": candidate.candidate_strategy,
            "candidate_id": candidate.candidate_id,
            "promoted_at": time.time(),
        }
        self.save()

    def promote(self, candidate: LearningCandidate, *, policy: PromotionPolicy) -> LearningCandidate:
        decision = policy.evaluate(candidate)
        if not decision.promote:
            raise RuntimeError("promotion policy rejected candidate: " + "; ".join(decision.reasons))
        ratchet = LearningRatchet(candidate)
        promoted = ratchet.transition(LearningState.PROMOTED)
        self.register(promoted)
        return promoted

    def quarantine(self, decision_family: str, *, reason: str) -> None:
        row = self._routes.pop(decision_family, None)
        if row is None:
            return
        self._quarantine[decision_family] = {
            **row,
            "quarantined_at": time.time(),
            "reason": str(reason),
        }
        self.save()

    def quarantine_record(self, decision_family: str) -> dict[str, Any] | None:
        row = self._quarantine.get(decision_family)
        return dict(row) if row else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "routes": dict(sorted(self._routes.items())),
            "quarantine": dict(sorted(self._quarantine.items())),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, path: str | Path | None = None) -> "PromotionRegistry":
        if int(payload.get("version", 0)) != 1:
            raise ValueError("unsupported promotion registry version")
        registry = cls(path=path)
        routes = payload.get("routes") or {}
        if not isinstance(routes, dict):
            raise TypeError("promotion registry routes must be an object")
        for family, raw in routes.items():
            if not isinstance(raw, dict) or not str(raw.get("strategy_id") or "").strip():
                raise TypeError("invalid promoted route")
            registry._routes[str(family)] = {
                "strategy_id": str(raw["strategy_id"]),
                "candidate_id": str(raw.get("candidate_id") or "unknown"),
                "promoted_at": float(raw.get("promoted_at", 0.0)),
            }
        quarantine = payload.get("quarantine") or {}
        if not isinstance(quarantine, dict):
            raise TypeError("promotion registry quarantine must be an object")
        for family, raw in quarantine.items():
            if not isinstance(raw, dict):
                raise TypeError("invalid quarantined route")
            registry._quarantine[str(family)] = dict(raw)
        return registry

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    @classmethod
    def load(cls, path: str | Path) -> "PromotionRegistry":
        target = Path(path)
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("promotion registry root must be an object")
        return cls.from_dict(payload, path=target)
