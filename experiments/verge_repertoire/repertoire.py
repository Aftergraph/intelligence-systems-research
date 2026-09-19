from __future__ import annotations

from dataclasses import dataclass
import math
import random

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


def _evolve_context(
    context: MissionContext,
    seed: int,
    population_size: int,
    generations: int,
) -> tuple[RepertoireEntry, int]:
    rng = random.Random(seed)
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

        children: list[PolicyGenome] = []
        for slot in range(population_size):
            parent = rng.choice(parent_pool)[0]
            op = rng.randrange(4)
            op_seed = rng.randrange(2**31)
            if slot == population_size - 1:
                child = _random_policy(rng)
            elif op == 0:
                child, _ = mutate_numeric(parent, op_seed)
            elif op == 1:
                child, _ = mutate_rule(parent, op_seed)
            elif op == 2:
                other = rng.choice(parent_pool)[0]
                child, _ = crossover(parent, other, op_seed)
            else:
                a = rng.choice(parent_pool)[0]
                b = rng.choice(parent_pool)[0]
                child, _ = differential_mutation(parent, a, b, op_seed)
            children.append(child)

        outcomes = [(genome, score(genome)) for genome in children]
        evaluations += population_size
        for genome, outcome in outcomes:
            if outcome.feasible and outcome.utility > best_outcome.utility:
                best_genome, best_outcome = genome, outcome

    entry = RepertoireEntry(
        source_context_id=context.context_id,
        source_descriptor=context.descriptor(),
        genome=best_genome,
        outcome=best_outcome,
    )
    return entry, evaluations


def evolve_repertoire(
    contexts: tuple[MissionContext, ...],
    seed: int,
    population_size: int = 12,
    generations: int = 6,
) -> RepertoireEvolutionResult:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    training = tuple(context for context in contexts if context.split == "TRAIN")
    if not training:
        raise ValueError("no TRAIN contexts")

    repertoire = Repertoire()
    evaluations = 0
    for index, context in enumerate(training):
        entry, used = _evolve_context(
            context,
            seed=seed * 1009 + index,
            population_size=population_size,
            generations=generations,
        )
        evaluations += used
        repertoire.insert(context, entry.genome, entry.outcome)

    return RepertoireEvolutionResult(
        repertoire=repertoire.entries(),
        training_context_ids=tuple(context.context_id for context in training),
        evaluations=evaluations,
    )
