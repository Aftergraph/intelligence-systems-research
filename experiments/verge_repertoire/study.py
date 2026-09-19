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

from .contexts import MissionContext, context_manifest_hash, load_contexts
from .repertoire import (
    ContextEvaluation,
    Repertoire,
    RepertoireEvolutionResult,
    _conservative_policy,
    _random_policy,
    evaluate_in_context,
    evolve_repertoire,
)


@dataclass(frozen=True)
class GlobalEvolutionResult:
    genome: PolicyGenome
    mean_train_utility: float
    training_context_ids: tuple[str, ...]
    policy_context_evaluations: int


def _global_score(
    genome: PolicyGenome,
    contexts: tuple[MissionContext, ...],
) -> tuple[float, tuple[ContextEvaluation, ...]]:
    outcomes = tuple(evaluate_in_context(genome, context) for context in contexts)
    if not all(outcome.feasible for outcome in outcomes):
        violations = sum(not outcome.feasible for outcome in outcomes)
        return -10000.0 - 1000.0 * violations, outcomes
    return mean(outcome.utility for outcome in outcomes), outcomes


def evolve_global_policy(
    contexts: tuple[MissionContext, ...],
    seed: int,
    population_size: int = 12,
    generations: int = 6,
) -> GlobalEvolutionResult:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    training = tuple(context for context in contexts if context.split == "TRAIN")
    if not training:
        raise ValueError("no TRAIN contexts")

    rng = random.Random(seed)
    population = [_conservative_policy()] + [
        _random_policy(rng) for _ in range(population_size - 1)
    ]
    scored = [(genome, *_global_score(genome, training)) for genome in population]
    evaluations = population_size * len(training)

    feasible = [
        item for item in scored
        if all(outcome.feasible for outcome in item[2])
    ]
    best = max(feasible or scored, key=lambda item: item[1])

    for _generation in range(generations):
        feasible = [
            item for item in scored
            if all(outcome.feasible for outcome in item[2])
        ]
        parents = sorted(
            feasible or scored,
            key=lambda item: item[1],
            reverse=True,
        )[: max(2, population_size // 3)]

        children: list[PolicyGenome] = []
        for slot in range(population_size):
            parent = rng.choice(parents)[0]
            op_seed = rng.randrange(2**31)
            op = rng.randrange(4)
            if slot == population_size - 1:
                child = _random_policy(rng)
            elif op == 0:
                child, _ = mutate_numeric(parent, op_seed)
            elif op == 1:
                child, _ = mutate_rule(parent, op_seed)
            elif op == 2:
                child, _ = crossover(parent, rng.choice(parents)[0], op_seed)
            else:
                a = rng.choice(parents)[0]
                b = rng.choice(parents)[0]
                child, _ = differential_mutation(parent, a, b, op_seed)
            children.append(child)

        scored = [(genome, *_global_score(genome, training)) for genome in children]
        evaluations += population_size * len(training)
        for item in scored:
            if all(outcome.feasible for outcome in item[2]) and item[1] > best[1]:
                best = item

    return GlobalEvolutionResult(
        genome=best[0],
        mean_train_utility=best[1],
        training_context_ids=tuple(context.context_id for context in training),
        policy_context_evaluations=evaluations,
    )


def build_random_repertoire(
    contexts: tuple[MissionContext, ...],
    seed: int,
    evaluations_per_context: int,
) -> RepertoireEvolutionResult:
    if evaluations_per_context < 1:
        raise ValueError("evaluations_per_context must be positive")
    training = tuple(context for context in contexts if context.split == "TRAIN")
    if not training:
        raise ValueError("no TRAIN contexts")

    rng = random.Random(seed)
    repertoire = Repertoire()
    evaluations = 0

    for context in training:
        candidates = [_conservative_policy()] + [
            _random_policy(rng) for _ in range(evaluations_per_context - 1)
        ]
        evaluations += len(candidates)
        for genome in candidates:
            outcome = evaluate_in_context(genome, context)
            repertoire.insert(context, genome, outcome)

    return RepertoireEvolutionResult(
        repertoire=repertoire.entries(),
        training_context_ids=tuple(context.context_id for context in training),
        evaluations=evaluations,
    )


def _restore_repertoire(
    result: RepertoireEvolutionResult,
    contexts_by_id: dict[str, MissionContext],
) -> Repertoire:
    repertoire = Repertoire()
    for entry in result.repertoire:
        source = contexts_by_id[entry.source_context_id]
        repertoire.insert(source, entry.genome, entry.outcome)
    return repertoire


def run_development_pilot(
    seeds: tuple[int, ...] = tuple(range(30)),
    population_size: int = 12,
    generations: int = 6,
) -> dict:
    contexts = load_contexts()
    by_id = {context.context_id: context for context in contexts}
    development = tuple(
        context for context in contexts if context.split == "DEVELOPMENT"
    )
    if not development:
        raise ValueError("no DEVELOPMENT contexts")

    rows: list[dict] = []
    paired: list[dict] = []
    search_runs: list[dict] = []

    for seed in seeds:
        global_result = evolve_global_policy(
            contexts,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        repertoire_result = evolve_repertoire(
            contexts,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        random_result = build_random_repertoire(
            contexts,
            seed=seed,
            evaluations_per_context=population_size * (generations + 1),
        )
        repertoire = _restore_repertoire(repertoire_result, by_id)
        random_repertoire = _restore_repertoire(random_result, by_id)

        search_runs.extend([
            {
                "seed": seed,
                "algorithm": "R1-global-evolved",
                "policy_context_evaluations": global_result.policy_context_evaluations,
            },
            {
                "seed": seed,
                "algorithm": "R3-random-repertoire",
                "policy_context_evaluations": random_result.evaluations,
            },
            {
                "seed": seed,
                "algorithm": "R6-verge-repertoire",
                "policy_context_evaluations": repertoire_result.evaluations,
            },
        ])

        for context in development:
            global_outcome = evaluate_in_context(global_result.genome, context)
            selected = repertoire.select(context)
            repertoire_outcome = evaluate_in_context(selected.genome, context)
            random_selected = random_repertoire.select(context)
            random_outcome = evaluate_in_context(random_selected.genome, context)

            rows.extend([
                {
                    "seed": seed,
                    "algorithm": "R1-global-evolved",
                    "context_id": context.context_id,
                    "utility": global_outcome.utility,
                    "feasible": global_outcome.feasible,
                    "verified_success": global_outcome.verified_success,
                    "unauthorized_actions": global_outcome.unauthorized_actions,
                },
                {
                    "seed": seed,
                    "algorithm": "R3-random-repertoire",
                    "context_id": context.context_id,
                    "source_context_id": random_selected.source_context_id,
                    "utility": random_outcome.utility,
                    "feasible": random_outcome.feasible,
                    "verified_success": random_outcome.verified_success,
                    "unauthorized_actions": random_outcome.unauthorized_actions,
                },
                {
                    "seed": seed,
                    "algorithm": "R6-verge-repertoire",
                    "context_id": context.context_id,
                    "source_context_id": selected.source_context_id,
                    "utility": repertoire_outcome.utility,
                    "feasible": repertoire_outcome.feasible,
                    "verified_success": repertoire_outcome.verified_success,
                    "unauthorized_actions": repertoire_outcome.unauthorized_actions,
                },
            ])
            paired.append({
                "seed": seed,
                "context_id": context.context_id,
                "global_utility": global_outcome.utility,
                "repertoire_utility": repertoire_outcome.utility,
                "utility_delta_repertoire_minus_global": (
                    repertoire_outcome.utility - global_outcome.utility
                ),
                "global_feasible": global_outcome.feasible,
                "repertoire_feasible": repertoire_outcome.feasible,
                "random_repertoire_utility": random_outcome.utility,
                "utility_delta_repertoire_minus_random": (
                    repertoire_outcome.utility - random_outcome.utility
                ),
                "random_repertoire_feasible": random_outcome.feasible,
            })

    deltas = [row["utility_delta_repertoire_minus_global"] for row in paired]
    random_deltas = [
        row["utility_delta_repertoire_minus_random"] for row in paired
    ]
    return {
        "experiment_id": "JAR-EXP-0016",
        "phase": "DEVELOPMENT",
        "evidence_class": "EXPLORATORY_DEVELOPMENT",
        "confirmatory": False,
        "held_out_evaluated": False,
        "context_manifest_hash": context_manifest_hash(contexts),
        "development_context_ids": tuple(
            context.context_id for context in development
        ),
        "configuration": {
            "seeds": seeds,
            "population_size": population_size,
            "generations": generations,
        },
        "summary": {
            "paired_context_evaluations": len(paired),
            "mean_utility_delta_repertoire_minus_global": mean(deltas) if deltas else None,
            "repertoire_wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "repertoire_losses": sum(delta < -1e-12 for delta in deltas),
            "repertoire_safety_failures": sum(
                not row["repertoire_feasible"] for row in paired
            ),
            "global_safety_failures": sum(
                not row["global_feasible"] for row in paired
            ),
            "mean_utility_delta_repertoire_minus_random": (
                mean(random_deltas) if random_deltas else None
            ),
            "repertoire_vs_random_wins": sum(
                delta > 1e-12 for delta in random_deltas
            ),
            "repertoire_vs_random_ties": sum(
                abs(delta) <= 1e-12 for delta in random_deltas
            ),
            "repertoire_vs_random_losses": sum(
                delta < -1e-12 for delta in random_deltas
            ),
            "random_repertoire_safety_failures": sum(
                not row["random_repertoire_feasible"] for row in paired
            ),
        },
        "search_runs": search_runs,
        "paired_context_rows": paired,
        "rows": rows,
    }
