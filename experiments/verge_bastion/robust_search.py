from __future__ import annotations

from dataclasses import dataclass, replace
import random
from statistics import mean

from experiments.verge.models import PolicyGenome
from experiments.verge.operators import (
    crossover,
    differential_mutation,
    mutate_numeric,
    mutate_rule,
)
from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_repertoire.repertoire import (
    _conservative_policy,
    _random_policy,
    evaluate_in_context,
)


DEFAULT_TRAIN_CONFIDENCE_SHOCKS = (0.00, 0.02)
DEFAULT_TRAIN_LATENCY_SHOCKS = (0.00, 0.08)
DEFAULT_TRAIN_COST_SHOCKS = (0.00, 0.08)


@dataclass(frozen=True)
class SearchResult:
    genome: PolicyGenome
    policy_context_evaluations: int
    candidate_evaluations: int
    robust_feasible: bool
    nominal_utility: float
    worst_halo_utility: float
    mean_halo_utility: float


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def make_training_halo(
    context: MissionContext,
    *,
    confidence_shocks: tuple[float, ...] = DEFAULT_TRAIN_CONFIDENCE_SHOCKS,
    latency_shocks: tuple[float, ...] = DEFAULT_TRAIN_LATENCY_SHOCKS,
    cost_shocks: tuple[float, ...] = DEFAULT_TRAIN_COST_SHOCKS,
) -> tuple[MissionContext, ...]:
    points: list[MissionContext] = []
    for confidence in confidence_shocks:
        for latency in latency_shocks:
            for cost in cost_shocks:
                points.append(
                    replace(
                        context,
                        context_id=(
                            f"{context.context_id}#train-halo-"
                            f"c{confidence:.2f}-"
                            f"l{latency:.2f}-"
                            f"k{cost:.2f}"
                        ),
                        min_confidence=_clip01(
                            context.min_confidence + confidence
                        ),
                        latency_pressure=_clip01(
                            context.latency_pressure + latency
                        ),
                        cost_pressure=_clip01(
                            context.cost_pressure + cost
                        ),
                    )
                )
    return tuple(points)


def _operator_child(
    rng: random.Random,
    parent: PolicyGenome,
    parent_pool: list[PolicyGenome],
) -> PolicyGenome:
    op = rng.randrange(4)
    seed = rng.randrange(2**31)
    if op == 0:
        child, _ = mutate_numeric(parent, seed)
        return child
    if op == 1:
        child, _ = mutate_rule(parent, seed)
        return child
    if op == 2:
        child, _ = crossover(parent, rng.choice(parent_pool), seed)
        return child
    a = rng.choice(parent_pool)
    b = rng.choice(parent_pool)
    child, _ = differential_mutation(parent, a, b, seed)
    return child


def _nominal_score(
    genome: PolicyGenome,
    context: MissionContext,
) -> tuple[tuple[float, float], dict]:
    outcome = evaluate_in_context(genome, context)
    if not outcome.feasible:
        return ((-1.0, outcome.utility), {
            "feasible": False,
            "nominal_utility": outcome.utility,
            "worst_halo_utility": outcome.utility,
            "mean_halo_utility": outcome.utility,
        })
    return ((1.0, outcome.utility), {
        "feasible": True,
        "nominal_utility": outcome.utility,
        "worst_halo_utility": outcome.utility,
        "mean_halo_utility": outcome.utility,
    })


def _robust_score(
    genome: PolicyGenome,
    context: MissionContext,
    halo: tuple[MissionContext, ...],
) -> tuple[tuple[float, float, float], dict]:
    nominal = evaluate_in_context(genome, context)
    outcomes = tuple(evaluate_in_context(genome, point) for point in halo)
    feasible = nominal.feasible and all(outcome.feasible for outcome in outcomes)
    utilities = [outcome.utility for outcome in outcomes]
    worst = min(utilities)
    average = mean(utilities)
    if not feasible:
        return ((-1.0, worst, average), {
            "feasible": False,
            "nominal_utility": nominal.utility,
            "worst_halo_utility": worst,
            "mean_halo_utility": average,
        })
    return ((1.0, worst, average), {
        "feasible": True,
        "nominal_utility": nominal.utility,
        "worst_halo_utility": worst,
        "mean_halo_utility": average,
    })


def _steady_state_search(
    context: MissionContext,
    *,
    seed: int,
    candidate_budget: int,
    population_size: int,
    robust: bool,
) -> tuple[PolicyGenome, dict]:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    if candidate_budget < population_size:
        raise ValueError("candidate budget smaller than population")

    rng = random.Random(seed)
    halo = make_training_halo(context) if robust else ()

    def evaluate(genome: PolicyGenome):
        if robust:
            return _robust_score(genome, context, halo)
        return _nominal_score(genome, context)

    genomes = [_conservative_policy()] + [
        _random_policy(rng) for _ in range(population_size - 1)
    ]
    population = []
    for genome in genomes:
        score, meta = evaluate(genome)
        population.append((score, genome, meta))

    consumed = population_size
    while consumed < candidate_budget:
        population.sort(key=lambda item: item[0], reverse=True)
        parent_count = max(2, population_size // 3)
        parents = [item[1] for item in population[:parent_count]]
        parent = rng.choice(parents)

        if consumed % population_size == population_size - 1:
            child = _random_policy(rng)
        else:
            child = _operator_child(rng, parent, parents)

        score, meta = evaluate(child)
        population.append((score, child, meta))
        population.sort(key=lambda item: item[0], reverse=True)
        population = population[:population_size]
        consumed += 1

    population.sort(key=lambda item: item[0], reverse=True)
    _score, genome, meta = population[0]
    return genome, meta


def evolve_nominal_context(
    context: MissionContext,
    *,
    seed: int,
    policy_context_budget: int,
    population_size: int = 8,
) -> SearchResult:
    if policy_context_budget < population_size:
        raise ValueError("budget too small")
    genome, meta = _steady_state_search(
        context,
        seed=seed,
        candidate_budget=policy_context_budget,
        population_size=population_size,
        robust=False,
    )
    return SearchResult(
        genome=genome,
        policy_context_evaluations=policy_context_budget,
        candidate_evaluations=policy_context_budget,
        robust_feasible=bool(meta["feasible"]),
        nominal_utility=float(meta["nominal_utility"]),
        worst_halo_utility=float(meta["worst_halo_utility"]),
        mean_halo_utility=float(meta["mean_halo_utility"]),
    )


def evolve_robust_context(
    context: MissionContext,
    *,
    seed: int,
    policy_context_budget: int,
    population_size: int = 8,
) -> SearchResult:
    halo_size = len(make_training_halo(context))
    if policy_context_budget % halo_size != 0:
        raise ValueError("robust budget must be divisible by halo size")
    candidate_budget = policy_context_budget // halo_size
    if candidate_budget < population_size:
        raise ValueError("budget too small for robust population")

    genome, meta = _steady_state_search(
        context,
        seed=seed,
        candidate_budget=candidate_budget,
        population_size=population_size,
        robust=True,
    )
    return SearchResult(
        genome=genome,
        policy_context_evaluations=policy_context_budget,
        candidate_evaluations=candidate_budget,
        robust_feasible=bool(meta["feasible"]),
        nominal_utility=float(meta["nominal_utility"]),
        worst_halo_utility=float(meta["worst_halo_utility"]),
        mean_halo_utility=float(meta["mean_halo_utility"]),
    )
