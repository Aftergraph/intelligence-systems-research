from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import sqrt
import json
from pathlib import Path
from typing import Any, Iterable


class NoAdmissibleIntelligence(RuntimeError):
    """Raised when no strategy satisfies capability, quality, authority, and budget gates."""




@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """A typed request to the intelligence scheduler, separate from authority."""

    request_id: str
    capability: str
    required_vsr: float
    risk_class: str = "normal"
    authority_granted: bool = True
    state_features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be non-empty")
        if not self.capability.strip():
            raise ValueError("capability must be non-empty")
        if not 0.0 <= self.required_vsr <= 1.0:
            raise ValueError("required_vsr must be between 0 and 1")

@dataclass(frozen=True, slots=True)
class IntelligenceBid:
    """A provider/model-agnostic bid for one unit of intelligence work.

    The same contract represents deterministic rules, Jev/System-1, learned
    policies, frontier models, specialist models, teams, or human escalation.
    Prices and latency are estimates; observed telemetry must remain separate.
    """

    strategy_id: str
    source: str
    capabilities: tuple[str, ...]
    predicted_vsr: float
    estimated_cost_usd: float
    estimated_latency_ms: float
    uncertainty: float = 0.0
    risk: float = 0.0
    frontier_input_tokens: int = 0
    frontier_output_tokens: int = 0
    authorized: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        if not self.source.strip():
            raise ValueError("source must be non-empty")
        if not self.capabilities:
            raise ValueError("capabilities must be non-empty")
        for name, value in (
            ("predicted_vsr", self.predicted_vsr),
            ("uncertainty", self.uncertainty),
            ("risk", self.risk),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be non-negative")
        if self.estimated_latency_ms < 0:
            raise ValueError("estimated_latency_ms must be non-negative")
        if self.frontier_input_tokens < 0 or self.frontier_output_tokens < 0:
            raise ValueError("frontier token estimates must be non-negative")

    @property
    def uses_frontier(self) -> bool:
        return self.source.casefold() == "frontier"


@dataclass(slots=True)
class FrontierTokenBudget:
    """Mission-scoped frontier inference budget.

    Admission uses reserved token estimates. Consumption is explicit so merely
    considering a bid never spends budget. Non-frontier work never consumes it.
    """

    input_limit: int
    output_limit: int
    input_used: int = 0
    output_used: int = 0

    def __post_init__(self) -> None:
        if self.input_limit < 0 or self.output_limit < 0:
            raise ValueError("frontier token limits must be non-negative")
        if self.input_used < 0 or self.output_used < 0:
            raise ValueError("frontier token usage must be non-negative")
        if self.input_used > self.input_limit or self.output_used > self.output_limit:
            raise ValueError("frontier token usage cannot exceed configured limits")

    @property
    def remaining(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_limit - self.input_used,
            "output_tokens": self.output_limit - self.output_used,
        }

    def can_admit(self, bid: IntelligenceBid) -> bool:
        if not bid.uses_frontier:
            return True
        return (
            self.input_used + bid.frontier_input_tokens <= self.input_limit
            and self.output_used + bid.frontier_output_tokens <= self.output_limit
        )

    def consume(self, bid: IntelligenceBid) -> None:
        if not bid.uses_frontier:
            return
        if not self.can_admit(bid):
            raise NoAdmissibleIntelligence(
                f"frontier budget cannot admit {bid.strategy_id!r}: "
                f"needs {bid.frontier_input_tokens}/{bid.frontier_output_tokens} tokens, "
                f"remaining {self.remaining['input_tokens']}/{self.remaining['output_tokens']}"
            )
        self.input_used += bid.frontier_input_tokens
        self.output_used += bid.frontier_output_tokens


@dataclass(frozen=True, slots=True)
class CompetenceKey:
    strategy_id: str
    task_family: str = "general"
    repo: str = "*"
    language: str = "*"
    mission_phase: str = "*"
    toolset: str = "*"
    context_band: str = "*"
    risk_class: str = "*"
    reasoning_level: str = "*"
    environment: str = "*"


@dataclass(frozen=True, slots=True)
class CompetenceEstimate:
    mean: float
    uncertainty: float
    observations: int
    alpha: float
    beta: float


class CompetenceGraph:
    """Empirical strategy competence indexed by task/environment dimensions.

    Each exact key has a Beta posterior. The graph deliberately does not smear
    evidence across neighboring keys; hierarchical/generalized transfer can be
    added later only after it is itself benchmarked.
    """

    def __init__(self, *, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> None:
        if prior_alpha <= 0 or prior_beta <= 0:
            raise ValueError("Beta priors must be positive")
        self.prior_alpha = float(prior_alpha)
        self.prior_beta = float(prior_beta)
        self._counts: dict[CompetenceKey, tuple[float, float, int]] = {}

    def observe(self, key: CompetenceKey, *, success: bool, weight: float = 1.0) -> None:
        if weight <= 0:
            raise ValueError("observation weight must be positive")
        successes, failures, observations = self._counts.get(key, (0.0, 0.0, 0))
        if success:
            successes += float(weight)
        else:
            failures += float(weight)
        self._counts[key] = (successes, failures, observations + 1)

    def estimate(self, key: CompetenceKey) -> CompetenceEstimate:
        successes, failures, observations = self._counts.get(key, (0.0, 0.0, 0))
        alpha = self.prior_alpha + successes
        beta = self.prior_beta + failures
        total = alpha + beta
        mean = alpha / total
        variance = (alpha * beta) / ((total * total) * (total + 1.0))
        # Standard deviation is used as an explicit uncertainty penalty. It
        # shrinks only with evidence and remains bounded in [0, 1].
        uncertainty = min(1.0, max(0.0, sqrt(variance)))
        return CompetenceEstimate(mean, uncertainty, observations, alpha, beta)

    def to_dict(self) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for key, (successes, failures, observations) in sorted(
            self._counts.items(),
            key=lambda item: (item[0].strategy_id, item[0].task_family, repr(item[0])),
        ):
            rows.append(
                {
                    "key": {
                        "strategy_id": key.strategy_id,
                        "task_family": key.task_family,
                        "repo": key.repo,
                        "language": key.language,
                        "mission_phase": key.mission_phase,
                        "toolset": key.toolset,
                        "context_band": key.context_band,
                        "risk_class": key.risk_class,
                        "reasoning_level": key.reasoning_level,
                        "environment": key.environment,
                    },
                    "successes": successes,
                    "failures": failures,
                    "observations": observations,
                }
            )
        return {
            "version": 1,
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
            "observations": rows,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CompetenceGraph":
        if int(payload.get("version", 0)) != 1:
            raise ValueError("unsupported competence graph version")
        graph = cls(
            prior_alpha=float(payload.get("prior_alpha", 1.0)),
            prior_beta=float(payload.get("prior_beta", 1.0)),
        )
        rows = payload.get("observations") or []
        if not isinstance(rows, list):
            raise TypeError("competence observations must be a list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("key"), dict):
                raise TypeError("invalid competence observation row")
            raw_key = row["key"]
            key = CompetenceKey(
                strategy_id=str(raw_key.get("strategy_id") or ""),
                task_family=str(raw_key.get("task_family") or "general"),
                repo=str(raw_key.get("repo") or "*"),
                language=str(raw_key.get("language") or "*"),
                mission_phase=str(raw_key.get("mission_phase") or "*"),
                toolset=str(raw_key.get("toolset") or "*"),
                context_band=str(raw_key.get("context_band") or "*"),
                risk_class=str(raw_key.get("risk_class") or "*"),
                reasoning_level=str(raw_key.get("reasoning_level") or "*"),
                environment=str(raw_key.get("environment") or "*"),
            )
            successes = float(row.get("successes", 0.0))
            failures = float(row.get("failures", 0.0))
            observations = int(row.get("observations", 0))
            if successes < 0 or failures < 0 or observations < 0:
                raise ValueError("competence counts must be non-negative")
            graph._counts[key] = (successes, failures, observations)
        return graph

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "CompetenceGraph":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("competence graph root must be an object")
        return cls.from_dict(payload)

    def bid(
        self,
        key: CompetenceKey,
        *,
        source: str,
        capabilities: tuple[str, ...],
        estimated_cost_usd: float,
        estimated_latency_ms: float,
        frontier_input_tokens: int = 0,
        frontier_output_tokens: int = 0,
        risk: float = 0.0,
        authorized: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> IntelligenceBid:
        estimate = self.estimate(key)
        return IntelligenceBid(
            strategy_id=key.strategy_id,
            source=source,
            capabilities=capabilities,
            predicted_vsr=estimate.mean,
            estimated_cost_usd=estimated_cost_usd,
            estimated_latency_ms=estimated_latency_ms,
            uncertainty=estimate.uncertainty,
            risk=risk,
            frontier_input_tokens=frontier_input_tokens,
            frontier_output_tokens=frontier_output_tokens,
            authorized=authorized,
            metadata={
                **(metadata or {}),
                "competence_observations": estimate.observations,
                "competence_alpha": estimate.alpha,
                "competence_beta": estimate.beta,
            },
        )


@dataclass(frozen=True, slots=True)
class FabricWeights:
    cost: float = 1.0
    latency: float = 0.0001
    uncertainty: float = 0.25
    risk: float = 0.5
    frontier_tokens: float = 0.000001

    def __post_init__(self) -> None:
        if any(value < 0 for value in (
            self.cost,
            self.latency,
            self.uncertainty,
            self.risk,
            self.frontier_tokens,
        )):
            raise ValueError("fabric weights must be non-negative")


class IntelligenceFabric:
    """Minimum-sufficient intelligence scheduler with fail-closed gates."""

    def __init__(
        self,
        *,
        bids: Iterable[IntelligenceBid],
        frontier_budget: FrontierTokenBudget,
        weights: FabricWeights | None = None,
        competence_graph: CompetenceGraph | None = None,
        competence_graph_path: str | Path | None = None,
        promotion_registry: Any | None = None,
    ) -> None:
        self.bids = list(bids)
        self.frontier_budget = frontier_budget
        self.weights = weights or FabricWeights()
        self.competence_graph_path = Path(competence_graph_path) if competence_graph_path else None
        self.promotion_registry = promotion_registry
        if competence_graph is not None:
            self.competence_graph = competence_graph
        elif self.competence_graph_path is not None and self.competence_graph_path.exists():
            self.competence_graph = CompetenceGraph.load(self.competence_graph_path)
        else:
            self.competence_graph = None
        self._selections = 0
        self._frontier_selections = 0
        self._frontier_input_reserved = 0
        self._frontier_output_reserved = 0
        self._outcomes_recorded = 0

    @staticmethod
    def _competence_key_for_bid(bid: IntelligenceBid) -> CompetenceKey | None:
        raw = bid.metadata.get("competence_key")
        if not isinstance(raw, dict):
            return None
        return CompetenceKey(
            strategy_id=bid.strategy_id,
            task_family=str(raw.get("task_family") or "general"),
            repo=str(raw.get("repo") or "*"),
            language=str(raw.get("language") or "*"),
            mission_phase=str(raw.get("mission_phase") or "*"),
            toolset=str(raw.get("toolset") or "*"),
            context_band=str(raw.get("context_band") or "*"),
            risk_class=str(raw.get("risk_class") or "*"),
            reasoning_level=str(raw.get("reasoning_level") or "*"),
            environment=str(raw.get("environment") or "*"),
        )

    def _materialize_bid(self, bid: IntelligenceBid) -> IntelligenceBid:
        if self.competence_graph is None:
            return bid
        key = self._competence_key_for_bid(bid)
        if key is None:
            return bid
        estimate = self.competence_graph.estimate(key)
        if estimate.observations <= 0:
            return bid
        return replace(
            bid,
            predicted_vsr=estimate.mean,
            uncertainty=estimate.uncertainty,
            metadata={
                **bid.metadata,
                "competence_observations": estimate.observations,
                "competence_alpha": estimate.alpha,
                "competence_beta": estimate.beta,
            },
        )

    def _objective(self, bid: IntelligenceBid) -> float:
        w = self.weights
        frontier_tokens = bid.frontier_input_tokens + bid.frontier_output_tokens
        return (
            w.cost * bid.estimated_cost_usd
            + w.latency * bid.estimated_latency_ms
            + w.uncertainty * bid.uncertainty
            + w.risk * bid.risk
            + w.frontier_tokens * frontier_tokens
        )

    def select_request(self, request: DecisionRequest) -> IntelligenceBid:
        if not request.authority_granted:
            raise NoAdmissibleIntelligence(
                f"decision request {request.request_id!r} has no authority to proceed"
            )
        capability = request.capability
        required_vsr = request.required_vsr
        materialized = [self._materialize_bid(bid) for bid in self.bids]
        capable = [bid for bid in materialized if capability in bid.capabilities]
        authorized = [bid for bid in capable if bid.authorized]
        quality = [bid for bid in authorized if bid.predicted_vsr >= required_vsr]
        admissible = [bid for bid in quality if self.frontier_budget.can_admit(bid)]

        if admissible:
            decision_family = str(request.state_features.get("decision_family") or "").strip()
            if self.promotion_registry is not None and decision_family:
                preferred = self.promotion_registry.preferred(decision_family)
                if preferred:
                    promoted = [bid for bid in admissible if bid.strategy_id == preferred]
                    if promoted:
                        return min(promoted, key=lambda bid: (self._objective(bid), -bid.predicted_vsr))
            return min(
                admissible,
                key=lambda bid: (
                    self._objective(bid),
                    -bid.predicted_vsr,
                    bid.strategy_id,
                ),
            )

        if quality and any(bid.uses_frontier for bid in quality):
            blocked = [bid.strategy_id for bid in quality if not self.frontier_budget.can_admit(bid)]
            if blocked:
                raise NoAdmissibleIntelligence(
                    "no admissible strategy: frontier budget blocks " + ", ".join(sorted(blocked))
                )
        if capable and not authorized:
            raise NoAdmissibleIntelligence("no admissible strategy: authority gate rejected all candidates")
        if authorized and not quality:
            raise NoAdmissibleIntelligence(
                f"no admissible strategy reaches required_vsr={required_vsr:.3f}"
            )
        raise NoAdmissibleIntelligence(f"no strategy provides capability {capability!r}")

    def select(self, *, capability: str, required_vsr: float) -> IntelligenceBid:
        return self.select_request(
            DecisionRequest(
                request_id=f"{capability}:inline",
                capability=capability,
                required_vsr=required_vsr,
            )
        )

    def record_selection(self, bid: IntelligenceBid, *, reserve_frontier: bool = True) -> None:
        self._selections += 1
        if not bid.uses_frontier:
            return
        if reserve_frontier:
            self.frontier_budget.consume(bid)
        self._frontier_selections += 1
        self._frontier_input_reserved += bid.frontier_input_tokens
        self._frontier_output_reserved += bid.frontier_output_tokens

    def record_outcome(self, bid: IntelligenceBid, *, success: bool) -> None:
        if self.competence_graph is None:
            return
        key = self._competence_key_for_bid(bid)
        if key is None:
            return
        self.competence_graph.observe(key, success=success)
        self._outcomes_recorded += 1
        if self.competence_graph_path is not None:
            self.competence_graph.save(self.competence_graph_path)

    def telemetry(self) -> dict[str, int | float]:
        return {
            "selections": self._selections,
            "frontier_selections": self._frontier_selections,
            "frontier_input_tokens_reserved": self._frontier_input_reserved,
            "frontier_output_tokens_reserved": self._frontier_output_reserved,
            "frontier_input_tokens_used": self.frontier_budget.input_used,
            "frontier_output_tokens_used": self.frontier_budget.output_used,
            "frontier_input_tokens_remaining": self.frontier_budget.remaining["input_tokens"],
            "frontier_output_tokens_remaining": self.frontier_budget.remaining["output_tokens"],
            "competence_outcomes_recorded": self._outcomes_recorded,
        }
