from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import prod, sqrt
from typing import Iterable


class NoAdmissibleVerification(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VerificationMethod:
    method_id: str
    assurance_level: int
    detection_probability: float
    estimated_cost_usd: float
    estimated_latency_ms: float
    command: str
    independent: bool = False

    def __post_init__(self) -> None:
        if not self.method_id.strip() or not self.command.strip():
            raise ValueError("verification method id and command must be non-empty")
        if not 0 <= self.assurance_level <= 7:
            raise ValueError("assurance_level must be between 0 and 7")
        if not 0.0 <= self.detection_probability <= 1.0:
            raise ValueError("detection_probability must be between 0 and 1")
        if self.estimated_cost_usd < 0 or self.estimated_latency_ms < 0:
            raise ValueError("verification cost/latency must be non-negative")


class VerifierCorrelationMatrix:
    """Pairwise empirical correlation of verifier defect-detection events.

    Correlations are planning signals, not proof. Positive correlation reduces
    the portfolio's assumed incremental detection value. Negative values are
    retained but the current optimizer does not reward them until independently
    validated on larger datasets.
    """

    def __init__(self) -> None:
        self._manual: dict[tuple[str, str], float] = {}
        self._observations: dict[tuple[str, str], list[tuple[bool, bool]]] = defaultdict(list)

    @staticmethod
    def _key(a: str, b: str) -> tuple[str, str]:
        if not a.strip() or not b.strip() or a == b:
            raise ValueError("correlation requires two distinct non-empty verifier ids")
        return tuple(sorted((a, b)))

    def set(self, a: str, b: str, correlation: float) -> None:
        if not -1.0 <= correlation <= 1.0:
            raise ValueError("correlation must be between -1 and 1")
        self._manual[self._key(a, b)] = float(correlation)

    def observe(self, a: str, b: str, *, a_detected: bool, b_detected: bool) -> None:
        self._observations[self._key(a, b)].append((bool(a_detected), bool(b_detected)))

    def get(self, a: str, b: str) -> float:
        key = self._key(a, b)
        if key in self._manual:
            return self._manual[key]
        rows = self._observations.get(key, [])
        if len(rows) < 2:
            return 0.0
        n11 = sum(1 for x, y in rows if x and y)
        n10 = sum(1 for x, y in rows if x and not y)
        n01 = sum(1 for x, y in rows if not x and y)
        n00 = sum(1 for x, y in rows if not x and not y)
        denom = sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        if denom == 0:
            # Identical constant outcomes contain no variance and therefore no
            # estimable phi correlation. Be conservative rather than inventing independence.
            return 1.0 if all(x == y for x, y in rows) else 0.0
        return max(-1.0, min(1.0, (n11 * n00 - n10 * n01) / denom))

    def average_positive(self, method_ids: tuple[str, ...]) -> float:
        pairs = list(combinations(method_ids, 2))
        if not pairs:
            return 0.0
        positive = [max(0.0, self.get(a, b)) for a, b in pairs]
        return sum(positive) / len(positive)


@dataclass(frozen=True, slots=True)
class VerificationRequirement:
    required_assurance: int
    required_detection: float
    defect_probability: float = 0.1
    impact_usd: float = 1.0
    max_cost_usd: float | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.required_assurance <= 7:
            raise ValueError("required_assurance must be between 0 and 7")
        for name, value in (
            ("required_detection", self.required_detection),
            ("defect_probability", self.defect_probability),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.impact_usd < 0:
            raise ValueError("impact_usd must be non-negative")
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be non-negative")


@dataclass(frozen=True, slots=True)
class VerificationPlan:
    methods: tuple[VerificationMethod, ...]
    assurance_level: int
    combined_detection: float
    total_cost_usd: float
    total_latency_ms: float
    value_of_verification: float

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "methods": [method.method_id for method in self.methods],
            "assurance_level": self.assurance_level,
            "combined_detection": self.combined_detection,
            "total_cost_usd": self.total_cost_usd,
            "total_latency_ms": self.total_latency_ms,
            "value_of_verification": self.value_of_verification,
        }


class VerificationPortfolioOptimizer:
    """Risk-price verification while enforcing a hard assurance floor.

    By default detection events are treated as independent, preserving v1.3 behavior.
    When a VerifierCorrelationMatrix is supplied, positive measured correlation
    conservatively discounts the incremental detection gain above the strongest
    single verifier. This heuristic is explicit and should be replaced by a
    better joint model when enough calibrated data exists.
    """

    def __init__(
        self,
        methods: Iterable[VerificationMethod],
        *,
        latency_weight: float = 0.0,
        correlations: VerifierCorrelationMatrix | None = None,
    ) -> None:
        self.methods = tuple(methods)
        if not self.methods:
            raise ValueError("at least one verification method is required")
        if latency_weight < 0:
            raise ValueError("latency_weight must be non-negative")
        self.latency_weight = float(latency_weight)
        self.correlations = correlations

    def combined_detection(self, methods: tuple[VerificationMethod, ...]) -> float:
        independent = 1.0 - prod(1.0 - method.detection_probability for method in methods)
        if self.correlations is None or len(methods) < 2:
            return independent
        strongest = max(method.detection_probability for method in methods)
        rho = self.correlations.average_positive(tuple(method.method_id for method in methods))
        return strongest + (independent - strongest) * (1.0 - rho)

    def plan(self, requirement: VerificationRequirement) -> VerificationPlan:
        admissible: list[VerificationPlan] = []
        if len(self.methods) > 12:
            raise ValueError("verification portfolio optimizer supports at most 12 methods")
        for size in range(1, len(self.methods) + 1):
            for subset in combinations(self.methods, size):
                assurance = max(method.assurance_level for method in subset)
                if assurance < requirement.required_assurance:
                    continue
                detection = self.combined_detection(subset)
                if detection + 1e-12 < requirement.required_detection:
                    continue
                cost = sum(method.estimated_cost_usd for method in subset)
                if requirement.max_cost_usd is not None and cost > requirement.max_cost_usd + 1e-12:
                    continue
                latency = sum(method.estimated_latency_ms for method in subset)
                value = requirement.defect_probability * detection * requirement.impact_usd - cost
                admissible.append(
                    VerificationPlan(
                        methods=tuple(sorted(subset, key=lambda method: (method.assurance_level, method.method_id))),
                        assurance_level=assurance,
                        combined_detection=detection,
                        total_cost_usd=cost,
                        total_latency_ms=latency,
                        value_of_verification=value,
                    )
                )
        if not admissible:
            raise NoAdmissibleVerification(
                "no verification portfolio satisfies assurance/detection/cost constraints"
            )
        return min(
            admissible,
            key=lambda plan: (
                plan.total_cost_usd + self.latency_weight * plan.total_latency_ms,
                -plan.value_of_verification,
                len(plan.methods),
                tuple(method.method_id for method in plan.methods),
            ),
        )
