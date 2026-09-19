from __future__ import annotations

from dataclasses import dataclass
import random

from .adaptation import ProbabilityMatcher
from .archive import BehaviorDescriptor, QDArchive
from .evaluation import EvaluationOutcome
from .harness import benchmark_manifest_hash, evaluate_policy
from .models import PolicyGenome
from .operators import crossover, differential_mutation, mutate_numeric, mutate_rule
from .pareto import ScoredCandidate, nondominated_fronts


@dataclass(frozen=True)
class Candidate:
    genome: PolicyGenome
    outcome: EvaluationOutcome
    quality: float


@dataclass(frozen=True)
class EvolutionResult:
    best: Candidate
    initial_best_quality: float
    best_quality: float
    archive_size: int
    evaluations: int
    operator_probabilities: dict[str, float]


def _quality(outcome: EvaluationOutcome) -> float:
    obj = outcome.objectives
    if not outcome.feasible:
        return -10000.0 - 1000.0 * obj.unauthorized_actions
    return (
        100.0 * obj.verified_success
        + 5.0 * obj.recovery
        - 25.0 * obj.false_completion
        - 0.6 * obj.cost
        - 0.25 * obj.latency
        - 10.0 * obj.human_interventions
    )


def _random_genome(rng: random.Random) -> PolicyGenome:
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
        confidence_threshold=round(rng.uniform(0.50, 0.95), 3),
        verification_depth=rng.randint(1, 4),
        operator_weights=(("numeric", 0.25), ("rule", 0.25), ("crossover", 0.25), ("differential", 0.25)),
    )


def _evaluate(genome: PolicyGenome, cases: tuple[dict, ...], seed: int) -> Candidate:
    outcome = evaluate_policy(genome, cases, seed)
    return Candidate(genome, outcome, _quality(outcome))


def _descriptor(candidate: Candidate) -> BehaviorDescriptor:
    return BehaviorDescriptor(
        parallelism=candidate.genome.parallelism,
        intervention_band=int(candidate.outcome.objectives.human_interventions > 0),
        verification_depth=candidate.genome.verification_depth,
    )


def _select_parents(population: list[Candidate]) -> list[Candidate]:
    feasible = [candidate for candidate in population if candidate.outcome.feasible]
    if not feasible:
        return sorted(population, key=lambda c: c.quality, reverse=True)[: max(1, len(population) // 3)]
    scored = [ScoredCandidate(c.genome.identity, c.outcome.objectives) for c in feasible]
    fronts = nondominated_fronts(scored)
    rank = {}
    for idx, front in enumerate(fronts):
        for item in front:
            rank[item.candidate_id] = idx
    ordered = sorted(
        feasible,
        key=lambda c: (rank[c.genome.identity], -c.quality),
    )
    return ordered[: max(2, len(population) // 3)]


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


def evolve(
    cases: tuple[dict, ...],
    seed: int,
    population_size: int = 20,
    generations: int = 10,
    expected_manifest_hash: str | None = None,
) -> EvolutionResult:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    actual_hash = benchmark_manifest_hash(cases)
    if expected_manifest_hash is not None and expected_manifest_hash != actual_hash:
        raise ValueError("benchmark manifest hash mismatch")

    rng = random.Random(seed)
    matcher = ProbabilityMatcher(("numeric", "rule", "crossover", "differential"), minimum=0.05)
    archive = QDArchive()
    population = [
        _evaluate(_conservative_genome(), cases, seed * 1000)
    ] + [
        _evaluate(_random_genome(rng), cases, seed * 1000 + index)
        for index in range(1, population_size)
    ]
    evaluations = population_size
    for candidate in population:
        archive.insert(candidate.genome.identity, _descriptor(candidate), candidate.outcome)

    feasible_initial = [candidate for candidate in population if candidate.outcome.feasible]
    initial_best = max(feasible_initial or population, key=lambda candidate: candidate.quality)
    global_best = initial_best

    for generation in range(generations):
        parents = _select_parents(population)
        children: list[Candidate] = []
        for slot in range(population_size):
            parent = rng.choice(parents)
            operator = _weighted_choice(rng, matcher.probabilities())
            op_seed = rng.randrange(0, 2**31)
            if slot == population_size - 1:
                genome = _random_genome(rng)
                operator = "immigrant"
            elif operator == "numeric":
                genome, _ = mutate_numeric(parent.genome, op_seed)
            elif operator == "rule":
                genome, _ = mutate_rule(parent.genome, op_seed)
            elif operator == "crossover":
                other = rng.choice(parents)
                genome, _ = crossover(parent.genome, other.genome, op_seed)
            else:
                base = parent.genome
                a = rng.choice(parents).genome
                b = rng.choice(parents).genome
                genome, _ = differential_mutation(base, a, b, op_seed)
            child = _evaluate(
                genome,
                cases,
                seed * 100000 + generation * population_size + slot,
            )
            if operator != "immigrant":
                matcher.update(operator, child.quality - parent.quality, child.outcome.feasible)
            archive.insert(child.genome.identity, _descriptor(child), child.outcome)
            children.append(child)
            if child.outcome.feasible and child.quality > global_best.quality:
                global_best = child
        population = children
        evaluations += population_size

    return EvolutionResult(
        best=global_best,
        initial_best_quality=initial_best.quality,
        best_quality=global_best.quality,
        archive_size=len(archive),
        evaluations=evaluations,
        operator_probabilities=matcher.probabilities(),
    )
