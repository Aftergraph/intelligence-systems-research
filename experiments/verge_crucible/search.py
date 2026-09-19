from __future__ import annotations

from dataclasses import dataclass
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
from experiments.verge_bastion.robust_search import make_training_halo


@dataclass(frozen=True)
class CrucibleSearchResult:
    genome: PolicyGenome
    policy_context_evaluations: int
    candidate_evaluations: int
    promoted_candidates: int
    robust_feasible: bool
    nominal_utility: float
    worst_halo_utility: float
    mean_halo_utility: float


def _child(
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


def _generate_nominal_candidates(
    context: MissionContext,
    *,
    seed: int,
    candidate_budget: int,
    population_size: int = 8,
) -> list[tuple[PolicyGenome, float, bool]]:
    if candidate_budget < population_size:
        raise ValueError("candidate budget smaller than population")
    rng = random.Random(seed)
    initial = [_conservative_policy()] + [
        _random_policy(rng) for _ in range(population_size - 1)
    ]
    evaluated: list[tuple[PolicyGenome, float, bool]] = []

    population: list[tuple[PolicyGenome, float, bool]] = []
    for genome in initial:
        outcome = evaluate_in_context(genome, context)
        row = (genome, outcome.utility, outcome.feasible)
        evaluated.append(row)
        population.append(row)

    consumed = population_size
    while consumed < candidate_budget:
        feasible = [row for row in population if row[2]]
        ranked = sorted(
            feasible or population,
            key=lambda row: row[1],
            reverse=True,
        )
        parents = [row[0] for row in ranked[: max(2, population_size // 3)]]
        parent = rng.choice(parents)
        if consumed % population_size == population_size - 1:
            child = _random_policy(rng)
        else:
            child = _child(rng, parent, parents)
        outcome = evaluate_in_context(child, context)
        row = (child, outcome.utility, outcome.feasible)
        evaluated.append(row)
        population.append(row)
        population = sorted(
            population,
            key=lambda item: (item[2], item[1]),
            reverse=True,
        )[:population_size]
        consumed += 1

    return evaluated


def evolve_nominal_context_matched(
    context: MissionContext,
    *,
    seed: int,
    policy_context_budget: int = 256,
    population_size: int = 8,
) -> CrucibleSearchResult:
    rows = _generate_nominal_candidates(
        context,
        seed=seed,
        candidate_budget=policy_context_budget,
        population_size=population_size,
    )
    feasible = [row for row in rows if row[2]]
    best = max(feasible or rows, key=lambda row: row[1])
    genome = best[0]
    outcome = evaluate_in_context(genome, context)
    return CrucibleSearchResult(
        genome=genome,
        policy_context_evaluations=policy_context_budget,
        candidate_evaluations=policy_context_budget,
        promoted_candidates=0,
        robust_feasible=outcome.feasible,
        nominal_utility=outcome.utility,
        worst_halo_utility=outcome.utility,
        mean_halo_utility=outcome.utility,
    )


def evolve_crucible_context(
    context: MissionContext,
    *,
    seed: int,
    policy_context_budget: int = 256,
    population_size: int = 8,
    nominal_candidate_budget: int = 144,
    promoted_candidates: int = 16,
) -> CrucibleSearchResult:
    halo = make_training_halo(context)
    remaining_halo_points = tuple(
        point
        for point in halo
        if not (
            point.min_confidence == context.min_confidence
            and point.latency_pressure == context.latency_pressure
            and point.cost_pressure == context.cost_pressure
        )
    )
    expected = (
        nominal_candidate_budget
        + promoted_candidates * len(remaining_halo_points)
    )
    if expected != policy_context_budget:
        raise ValueError(
            f"budget mismatch: expected {expected}, got {policy_context_budget}"
        )

    rows = _generate_nominal_candidates(
        context,
        seed=seed,
        candidate_budget=nominal_candidate_budget,
        population_size=population_size,
    )

    ranked = sorted(
        [row for row in rows if row[2]],
        key=lambda row: row[1],
        reverse=True,
    )
    promoted = ranked[:promoted_candidates]
    if len(promoted) < promoted_candidates:
        raise ValueError("insufficient feasible candidates for promotion")

    robust_rows = []
    for genome, nominal_utility, _ in promoted:
        outcomes = [
            evaluate_in_context(genome, point)
            for point in remaining_halo_points
        ]
        feasible = all(outcome.feasible for outcome in outcomes)
        utilities = [nominal_utility] + [outcome.utility for outcome in outcomes]
        robust_rows.append(
            (
                genome,
                feasible,
                min(utilities),
                mean(utilities),
                nominal_utility,
            )
        )

    feasible_robust = [row for row in robust_rows if row[1]]
    pool = feasible_robust or robust_rows
    best = max(
        pool,
        key=lambda row: (
            row[1],
            row[2],
            row[3],
            row[4],
        ),
    )
    return CrucibleSearchResult(
        genome=best[0],
        policy_context_evaluations=policy_context_budget,
        candidate_evaluations=nominal_candidate_budget,
        promoted_candidates=promoted_candidates,
        robust_feasible=best[1],
        nominal_utility=best[4],
        worst_halo_utility=best[2],
        mean_halo_utility=best[3],
    )
