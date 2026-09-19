from __future__ import annotations

from statistics import mean

from experiments.verge.models import stable_hash
from experiments.verge_repertoire.repertoire import (
    Repertoire,
    evaluate_in_context,
    evolve_fixed_repertoire,
)

from .contexts import context_manifest_hash, load_contexts
from .halo import select_halo_robust


FAIL_CLOSED_UTILITY = -10000.0


def _restore_repertoire(result, contexts_by_id) -> Repertoire:
    repertoire = Repertoire()
    for entry in result.repertoire:
        source = contexts_by_id[entry.source_context_id]
        repertoire.insert(source, entry.genome, entry.outcome)
    return repertoire


def _fail_closed(selector: str, seed: int, context_id: str, repertoire_hash: str) -> dict:
    return {
        "seed": seed,
        "selector": selector,
        "context_id": context_id,
        "repertoire_hash": repertoire_hash,
        "source_context_id": None,
        "utility": FAIL_CLOSED_UTILITY,
        "feasible": True,
        "verified_success": 0,
        "false_completion": 0,
        "unauthorized_actions": 0,
        "evidence_integrity_failures": 0,
        "recovery_success": 0,
        "cost": 0.0,
        "latency": 0.0,
        "human_interventions": 0,
        "selection_failure": 1,
        "selector_evaluations": 0,
    }


def _row_from_entry(
    *,
    selector: str,
    seed: int,
    context,
    entry,
    repertoire_hash: str,
    selector_evaluations: int,
) -> dict:
    outcome = evaluate_in_context(entry.genome, context)
    return {
        "seed": seed,
        "selector": selector,
        "context_id": context.context_id,
        "repertoire_hash": repertoire_hash,
        "source_context_id": entry.source_context_id,
        "utility": outcome.utility,
        "feasible": outcome.feasible,
        "verified_success": outcome.verified_success,
        "false_completion": outcome.false_completion,
        "unauthorized_actions": outcome.unauthorized_actions,
        "evidence_integrity_failures": outcome.evidence_integrity_failures,
        "recovery_success": outcome.recovery_success,
        "cost": outcome.cost,
        "latency": outcome.latency,
        "human_interventions": outcome.human_interventions,
        "selection_failure": 0,
        "selector_evaluations": selector_evaluations,
    }


def _select_nominal(repertoire: Repertoire, seed: int, context, repertoire_hash: str) -> dict:
    try:
        entry = repertoire.select(context)
    except LookupError:
        return _fail_closed("NOMINAL", seed, context.context_id, repertoire_hash)
    return _row_from_entry(
        selector="NOMINAL",
        seed=seed,
        context=context,
        entry=entry,
        repertoire_hash=repertoire_hash,
        selector_evaluations=len(repertoire),
    )


def _select_halo(repertoire: Repertoire, seed: int, context, repertoire_hash: str) -> dict:
    try:
        selection = select_halo_robust(repertoire, context)
    except LookupError:
        return _fail_closed("HALO", seed, context.context_id, repertoire_hash)
    return _row_from_entry(
        selector="HALO",
        seed=seed,
        context=context,
        entry=selection.entry,
        repertoire_hash=repertoire_hash,
        selector_evaluations=selection.halo_evaluations,
    )


def run_development_pilot(
    *,
    seeds: tuple[int, ...] = tuple(range(30)),
    population_size: int = 12,
    generations: int = 6,
) -> dict:
    contexts = load_contexts()
    by_id = {context.context_id: context for context in contexts}
    development = tuple(
        context for context in contexts
        if context.split == "DEVELOPMENT"
    )
    if not development:
        raise ValueError("no DEVELOPMENT contexts")

    search_runs: list[dict] = []
    context_rows: list[dict] = []
    seed_worst_deltas: list[dict] = []

    for seed in seeds:
        search = evolve_fixed_repertoire(
            contexts,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        repertoire = _restore_repertoire(search, by_id)
        repertoire_hash = stable_hash(search.repertoire)

        search_runs.append({
            "seed": seed,
            "algorithm": "SHARED-R5-C-FIXED-REPERTOIRE",
            "policy_context_evaluations": search.evaluations,
            "repertoire_hash": repertoire_hash,
        })

        nominal_rows: list[dict] = []
        halo_rows: list[dict] = []
        for context in development:
            nominal = _select_nominal(
                repertoire,
                seed,
                context,
                repertoire_hash,
            )
            halo = _select_halo(
                repertoire,
                seed,
                context,
                repertoire_hash,
            )
            nominal_rows.append(nominal)
            halo_rows.append(halo)
            context_rows.extend((nominal, halo))

        nominal_worst = min(row["utility"] for row in nominal_rows)
        halo_worst = min(row["utility"] for row in halo_rows)
        seed_worst_deltas.append({
            "seed": seed,
            "nominal_worst_utility": nominal_worst,
            "halo_worst_utility": halo_worst,
            "delta_worst": halo_worst - nominal_worst,
            "nominal_mean_utility": mean(
                row["utility"] for row in nominal_rows
            ),
            "halo_mean_utility": mean(
                row["utility"] for row in halo_rows
            ),
        })

    deltas = [row["delta_worst"] for row in seed_worst_deltas]
    halo_rows = [
        row for row in context_rows if row["selector"] == "HALO"
    ]
    nominal_rows = [
        row for row in context_rows if row["selector"] == "NOMINAL"
    ]

    return {
        "experiment_id": "JAR-EXP-0017",
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
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "seeds": len(seeds),
            "mean_delta_worst": mean(deltas) if deltas else None,
            "halo_wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "halo_losses": sum(delta < -1e-12 for delta in deltas),
            "halo_safety_failures": sum(
                row["unauthorized_actions"]
                + row["evidence_integrity_failures"]
                for row in halo_rows
            ),
            "nominal_safety_failures": sum(
                row["unauthorized_actions"]
                + row["evidence_integrity_failures"]
                for row in nominal_rows
            ),
            "halo_selection_failures": sum(
                row["selection_failure"] for row in halo_rows
            ),
            "nominal_selection_failures": sum(
                row["selection_failure"] for row in nominal_rows
            ),
            "halo_selector_evaluations": sum(
                row["selector_evaluations"] for row in halo_rows
            ),
            "nominal_selector_evaluations": sum(
                row["selector_evaluations"] for row in nominal_rows
            ),
        },
    }
