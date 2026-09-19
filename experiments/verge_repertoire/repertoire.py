from __future__ import annotations

from dataclasses import dataclass
import math
import random

from experiments.verge.adaptation import ProbabilityMatcher
from experiments.verge.models import PolicyGenome
from experiments.verge.operators import (
    crossover,
    differential_mutation,
    mutate_numeric,
    mutate_rule,
)

from .contexts import MissionContext


@dataclass(frozen=True)
class ContextEvaluation:
    feasible: bool
    verified_success: int
    false_completion: int
    unauthorized_actions: int
    evidence_integrity_failures: int
    cost: float
    latency: float
    human_interventions: int
    recovery_success: int
    utility: float


@dataclass(frozen=True)
class RepertoireEntry:
    source_context_id: str
    source_descriptor: tuple[float, float, float, float]
    genome: PolicyGenome
    outcome: ContextEvaluation


@dataclass(frozen=True)
class RepertoireEvolutionResult:
    repertoire: tuple[RepertoireEntry, ...]
    training_context_ids: tuple[str, ...]
    evaluations: int
    adaptive: bool = False
    operator_probabilities: tuple[
        tuple[str, tuple[tuple[str, float], ...]], ...
    ] = ()


def evaluate_in_context(genome: PolicyGenome, context: MissionContext) -> ContextEvaluation:
    executes = "execute" in genome.routing_policy
    verifies = "verify" in genome.routing_policy

    below_authority_floor = (
        genome.verification_depth < context.min_verification
        or genome.confidence_threshold < context.min_confidence
    )
    unauthorized = int(executes and context.risk_class > 0 and below_authority_floor)
    evidence_failure = int(executes and not verifies)

    recovery_ok = (
        genome.retry_ceiling >= context.min_retries
        and verifies
    )
    verifier_pass = (
        executes
        and verifies
        and not below_authority_floor
        and genome.retry_ceiling >= context.min_retries
    )
    feasible = unauthorized == 0 and evidence_failure == 0 and verifier_pass

    cost = context.base_cost * (
        1.0
        + 0.16 * genome.verification_depth
        + 0.10 * genome.retry_ceiling
        + 0.07 * genome.parallelism
    ) * (0.5 + context.cost_pressure)

    latency = context.base_latency * (
        1.0
        + 0.13 * genome.verification_depth
        + 0.08 * genome.retry_ceiling
    ) / math.sqrt(genome.parallelism) * (0.5 + context.latency_pressure)

    intervention_floor = min(1.0, context.min_confidence + 0.04)
    interventions = int(genome.confidence_threshold < intervention_floor)

    verified_success = int(feasible)
    false_completion = int(executes and not verifier_pass)
    recovery_success = int(recovery_ok and feasible)

    if not feasible:
        utility = -10000.0 - 1000.0 * unauthorized - 500.0 * evidence_failure
    else:
        utility = (
            100.0 * verified_success
            + 5.0 * recovery_success
            - 0.60 * cost
            - 0.25 * latency
            - 10.0 * interventions
        )

    return ContextEvaluation(
        feasible=feasible,
        verified_success=verified_success,
        false_completion=false_completion,
        unauthorized_actions=unauthorized,
        evidence_integrity_failures=evidence_failure,
        cost=cost,
        latency=latency,
        human_interventions=interventions,
        recovery_success=recovery_success,
        utility=utility,
    )


class Repertoire:
    def __init__(self) -> None:
        self._entries: dict[str, RepertoireEntry] = {}

    def insert(
        self,
        context: MissionContext,
        genome: PolicyGenome,
        outcome: ContextEvaluation,
    ) -> bool:
        if not outcome.feasible:
            return False
        proposed = RepertoireEntry(
            source_context_id=context.context_id,
            source_descriptor=context.descriptor(),
            genome=genome,
            outcome=outcome,
        )
        current = self._entries.get(context.context_id)
        if current is None or proposed.outcome.utility > current.outcome.utility:
            self._entries[context.context_id] = proposed
            return True
        return False

    def select(self, context: MissionContext) -> RepertoireEntry:
        if not self._entries:
            raise LookupError("repertoire is empty")
        target = context.descriptor()

        def distance(entry: RepertoireEntry) -> tuple[float, float, str]:
            squared = sum(
                (left - right) ** 2
                for left, right in zip(entry.source_descriptor, target)
            )
            return (squared, -entry.outcome.utility, entry.source_context_id)

        return min(self._entries.values(), key=distance)

    def entries(self) -> tuple[RepertoireEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def __len__(self) -> int:
        return len(self._entries)


def _conservative_policy() -> PolicyGenome:
    return PolicyGenome(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=3,
        confidence_threshold=0.95,
        verification_depth=4,
        operator_weights=(
            ("numeric", 0.25),
            ("rule", 0.25),
            ("crossover", 0.25),
            ("differential", 0.25),
        ),
    )


def _random_policy(rng: random.Random) -> PolicyGenome:
    routes = (
        ("discover", "execute", "verify"),
        ("execute", "verify"),
        ("discover", "execute"),
        ("execute",),
    )
    return PolicyGenome(
        routing_policy=rng.choice(routes),
        parallelism=rng.randint(1, 4),
        retry_ceiling=rng.randint(0, 3),
        confidence_threshold=round(rng.uniform(0.65, 0.97), 3),
        verification_depth=rng.randint(1, 4),
        operator_weights=(
            ("numeric", 0.25),
            ("rule", 0.25),
            ("crossover", 0.25),
            ("differential", 0.25),
        ),
    )


def _weighted_choice(rng: random.Random, probabilities: dict[str, float]) -> str:
    threshold = rng.random()
    cumulative = 0.0
    last = next(iter(probabilities))
    for name, probability in probabilities.items():
        last = name
        cumulative += probability
        if threshold <= cumulative:
            return name
    return last


def _apply_operator(
    operator: str,
    parent: PolicyGenome,
    parent_pool: list[tuple[PolicyGenome, ContextEvaluation]],
    rng: random.Random,
    op_seed: int,
) -> PolicyGenome:
    if operator == "numeric":
        child, _ = mutate_numeric(parent, op_seed)
        return child
    if operator == "rule":
        child, _ = mutate_rule(parent, op_seed)
        return child
    if operator == "crossover":
        child, _ = crossover(parent, rng.choice(parent_pool)[0], op_seed)
        return child
    if operator == "differential":
        a = rng.choice(parent_pool)[0]
        b = rng.choice(parent_pool)[0]
        child, _ = differential_mutation(parent, a, b, op_seed)
        return child
    raise KeyError(operator)


def _evolve_context(
    context: MissionContext,
    seed: int,
    population_size: int,
    generations: int,
    adaptive: bool,
) -> tuple[RepertoireEntry, int, tuple[tuple[str, float], ...]]:
    rng = random.Random(seed)
    operators = ("numeric", "rule", "crossover", "differential")
    matcher = ProbabilityMatcher(operators, minimum=0.05)

    population = [_conservative_policy()] + [
        _random_policy(rng) for _ in range(population_size - 1)
    ]
    evaluations = population_size

    def score(genome: PolicyGenome) -> ContextEvaluation:
        return evaluate_in_context(genome, context)

    outcomes = [(genome, score(genome)) for genome in population]
    feasible = [(g, o) for g, o in outcomes if o.feasible]
    best_genome, best_outcome = max(
        feasible or outcomes,
        key=lambda pair: pair[1].utility,
    )

    for _generation in range(generations):
        feasible = [(g, o) for g, o in outcomes if o.feasible]
        parent_pool = sorted(
            feasible or outcomes,
            key=lambda pair: pair[1].utility,
            reverse=True,
        )[: max(2, population_size // 3)]

        pending: list[
            tuple[PolicyGenome, str | None, ContextEvaluation | None]
        ] = []
        for slot in range(population_size):
            parent_genome, parent_outcome = rng.choice(parent_pool)
            if slot == population_size - 1:
                pending.append((_random_policy(rng), None, None))
                continue

            if adaptive:
                operator = _weighted_choice(rng, matcher.probabilities())
            else:
                operator = operators[rng.randrange(len(operators))]
            child = _apply_operator(
                operator,
                parent_genome,
                parent_pool,
                rng,
                rng.randrange(2**31),
            )
            pending.append((child, operator, parent_outcome))

        outcomes = []
        for child, operator, parent_outcome in pending:
            outcome = score(child)
            outcomes.append((child, outcome))
            if adaptive and operator is not None and parent_outcome is not None:
                matcher.update(
                    operator,
                    outcome.utility - parent_outcome.utility,
                    outcome.feasible,
                )
            if outcome.feasible and outcome.utility > best_outcome.utility:
                best_genome, best_outcome = child, outcome
        evaluations += population_size

    entry = RepertoireEntry(
        source_context_id=context.context_id,
        source_descriptor=context.descriptor(),
        genome=best_genome,
        outcome=best_outcome,
    )
    probabilities = tuple(sorted(matcher.probabilities().items()))
    return entry, evaluations, probabilities


def _evolve_repertoire(
    contexts: tuple[MissionContext, ...],
    seed: int,
    population_size: int,
    generations: int,
    adaptive: bool,
) -> RepertoireEvolutionResult:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    training = tuple(context for context in contexts if context.split == "TRAIN")
    if not training:
        raise ValueError("no TRAIN contexts")

    repertoire = Repertoire()
    evaluations = 0
    probabilities: list[tuple[str, tuple[tuple[str, float], ...]]] = []

    for index, context in enumerate(training):
        entry, used, context_probabilities = _evolve_context(
            context,
            seed=seed * 1009 + index,
            population_size=population_size,
            generations=generations,
            adaptive=adaptive,
        )
        evaluations += used
        repertoire.insert(context, entry.genome, entry.outcome)
        probabilities.append((context.context_id, context_probabilities))

    return RepertoireEvolutionResult(
        repertoire=repertoire.entries(),
        training_context_ids=tuple(context.context_id for context in training),
        evaluations=evaluations,
        adaptive=adaptive,
        operator_probabilities=tuple(probabilities),
    )


def evolve_fixed_repertoire(
    contexts: tuple[MissionContext, ...],
    seed: int,
    population_size: int = 12,
    generations: int = 6,
) -> RepertoireEvolutionResult:
    return _evolve_repertoire(
        contexts,
        seed=seed,
        population_size=population_size,
        generations=generations,
        adaptive=False,
    )


def evolve_repertoire(
    contexts: tuple[MissionContext, ...],
    seed: int,
    population_size: int = 12,
    generations: int = 6,
) -> RepertoireEvolutionResult:
    return _evolve_repertoire(
        contexts,
        seed=seed,
        population_size=population_size,
        generations=generations,
        adaptive=True,
    )
