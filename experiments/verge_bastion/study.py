from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from experiments.verge.models import stable_hash
from experiments.verge_repertoire.repertoire import Repertoire, evaluate_in_context

from .contexts import context_manifest_hash, load_contexts
from .robust_search import (
    evolve_nominal_context,
    evolve_robust_context,
    make_training_halo,
)


FAIL_CLOSED_UTILITY = -10000.0


@dataclass(frozen=True)
class BuiltRepertoire:
    repertoire: Repertoire
    policy_context_evaluations: int
    candidate_evaluations: int
    robust_coverage: float
    hash: str


def _build_repertoire(
    contexts,
    *,
    seed: int,
    policy_context_budget_per_niche: int,
    population_size: int,
    robust: bool,
) -> BuiltRepertoire:
    training = tuple(context for context in contexts if context.split == "TRAIN")
    if not training:
        raise ValueError("no TRAIN contexts")

    repertoire = Repertoire()
    policy_context_evaluations = 0
    candidate_evaluations = 0
    robust_survivors = 0
    serial = []

    for index, context in enumerate(training):
        context_seed = seed * 1009 + index
        result = (
            evolve_robust_context(
                context,
                seed=context_seed,
                policy_context_budget=policy_context_budget_per_niche,
                population_size=population_size,
            )
            if robust
            else evolve_nominal_context(
                context,
                seed=context_seed,
                policy_context_budget=policy_context_budget_per_niche,
                population_size=population_size,
            )
        )
        policy_context_evaluations += result.policy_context_evaluations
        candidate_evaluations += result.candidate_evaluations
        nominal_outcome = evaluate_in_context(result.genome, context)
        if nominal_outcome.feasible:
            repertoire.insert(context, result.genome, nominal_outcome)

        halo = make_training_halo(context)
        if all(evaluate_in_context(result.genome, point).feasible for point in halo):
            robust_survivors += 1

        serial.append({
            "context_id": context.context_id,
            "genome": result.genome.payload(),
            "nominal_utility": result.nominal_utility,
            "worst_halo_utility": result.worst_halo_utility,
            "mean_halo_utility": result.mean_halo_utility,
            "robust_feasible": result.robust_feasible,
        })

    return BuiltRepertoire(
        repertoire=repertoire,
        policy_context_evaluations=policy_context_evaluations,
        candidate_evaluations=candidate_evaluations,
        robust_coverage=robust_survivors / len(training),
        hash=stable_hash(tuple(serial)),
    )


def _select_row(
    repertoire: Repertoire,
    *,
    seed: int,
    algorithm: str,
    context,
    repertoire_hash: str,
) -> dict:
    try:
        entry = repertoire.select(context)
    except LookupError:
        return {
            "seed": seed,
            "algorithm": algorithm,
            "context_id": context.context_id,
            "repertoire_hash": repertoire_hash,
            "source_context_id": None,
            "utility": FAIL_CLOSED_UTILITY,
            "verified_success": 0,
            "false_completion": 0,
            "unauthorized_actions": 0,
            "evidence_integrity_failures": 0,
            "recovery_success": 0,
            "cost": 0.0,
            "latency": 0.0,
            "human_interventions": 0,
            "selection_failure": 1,
        }

    outcome = evaluate_in_context(entry.genome, context)
    return {
        "seed": seed,
        "algorithm": algorithm,
        "context_id": context.context_id,
        "repertoire_hash": repertoire_hash,
        "source_context_id": entry.source_context_id,
        "utility": outcome.utility,
        "verified_success": outcome.verified_success,
        "false_completion": outcome.false_completion,
        "unauthorized_actions": outcome.unauthorized_actions,
        "evidence_integrity_failures": outcome.evidence_integrity_failures,
        "recovery_success": outcome.recovery_success,
        "cost": outcome.cost,
        "latency": outcome.latency,
        "human_interventions": outcome.human_interventions,
        "selection_failure": 0,
    }


def run_development_pilot(
    *,
    seeds: tuple[int, ...] = tuple(range(30)),
    policy_context_budget_per_niche: int = 256,
    population_size: int = 8,
) -> dict:
    contexts = load_contexts()
    development = tuple(context for context in contexts if context.split == "DEVELOPMENT")
    if not development:
        raise ValueError("no DEVELOPMENT contexts")

    search_runs = []
    context_rows = []
    seed_worst_deltas = []
    robust_coverages = []
    nominal_coverages = []

    for seed in seeds:
        nominal = _build_repertoire(
            contexts,
            seed=seed,
            policy_context_budget_per_niche=policy_context_budget_per_niche,
            population_size=population_size,
            robust=False,
        )
        bastion = _build_repertoire(
            contexts,
            seed=seed,
            policy_context_budget_per_niche=policy_context_budget_per_niche,
            population_size=population_size,
            robust=True,
        )

        if nominal.policy_context_evaluations != bastion.policy_context_evaluations:
            raise ValueError("search budgets do not match")

        robust_coverages.append(bastion.robust_coverage)
        nominal_coverages.append(nominal.robust_coverage)

        search_runs.extend([
            {
                "seed": seed,
                "algorithm": "NOMINAL-REPERTOIRE",
                "policy_context_evaluations": nominal.policy_context_evaluations,
                "candidate_evaluations": nominal.candidate_evaluations,
                "train_robust_coverage": nominal.robust_coverage,
                "repertoire_hash": nominal.hash,
            },
            {
                "seed": seed,
                "algorithm": "BASTION-ROBUST-REPERTOIRE",
                "policy_context_evaluations": bastion.policy_context_evaluations,
                "candidate_evaluations": bastion.candidate_evaluations,
                "train_robust_coverage": bastion.robust_coverage,
                "repertoire_hash": bastion.hash,
            },
        ])

        nominal_rows = []
        bastion_rows = []
        for context in development:
            nrow = _select_row(
                nominal.repertoire,
                seed=seed,
                algorithm="NOMINAL-REPERTOIRE",
                context=context,
                repertoire_hash=nominal.hash,
            )
            brow = _select_row(
                bastion.repertoire,
                seed=seed,
                algorithm="BASTION-ROBUST-REPERTOIRE",
                context=context,
                repertoire_hash=bastion.hash,
            )
            nominal_rows.append(nrow)
            bastion_rows.append(brow)
            context_rows.extend((nrow, brow))

        nominal_worst = min(row["utility"] for row in nominal_rows)
        bastion_worst = min(row["utility"] for row in bastion_rows)
        seed_worst_deltas.append({
            "seed": seed,
            "nominal_worst_utility": nominal_worst,
            "bastion_worst_utility": bastion_worst,
            "delta_worst": bastion_worst - nominal_worst,
            "nominal_mean_utility": mean(row["utility"] for row in nominal_rows),
            "bastion_mean_utility": mean(row["utility"] for row in bastion_rows),
        })

    deltas = [row["delta_worst"] for row in seed_worst_deltas]
    bastion_rows_all = [r for r in context_rows if r["algorithm"] == "BASTION-ROBUST-REPERTOIRE"]
    nominal_rows_all = [r for r in context_rows if r["algorithm"] == "NOMINAL-REPERTOIRE"]

    return {
        "experiment_id": "JAR-EXP-0018",
        "phase": "DEVELOPMENT",
        "evidence_class": "EXPLORATORY_DEVELOPMENT",
        "confirmatory": False,
        "held_out_evaluated": False,
        "context_manifest_hash": context_manifest_hash(contexts),
        "development_context_ids": tuple(context.context_id for context in development),
        "configuration": {
            "seeds": seeds,
            "policy_context_budget_per_niche": policy_context_budget_per_niche,
            "population_size": population_size,
        },
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "seeds": len(seeds),
            "mean_delta_worst": mean(deltas) if deltas else None,
            "bastion_wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "bastion_losses": sum(delta < -1e-12 for delta in deltas),
            "bastion_train_robust_coverage": mean(robust_coverages) if robust_coverages else None,
            "nominal_train_robust_coverage": mean(nominal_coverages) if nominal_coverages else None,
            "bastion_selection_failures": sum(r["selection_failure"] for r in bastion_rows_all),
            "nominal_selection_failures": sum(r["selection_failure"] for r in nominal_rows_all),
            "bastion_uar": sum(r["unauthorized_actions"] for r in bastion_rows_all),
            "nominal_uar": sum(r["unauthorized_actions"] for r in nominal_rows_all),
        },
    }
