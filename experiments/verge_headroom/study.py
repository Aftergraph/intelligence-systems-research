from __future__ import annotations

from statistics import mean

from experiments.verge.models import stable_hash
from experiments.verge_crucible.search import _generate_nominal_candidates
from experiments.verge_repertoire.repertoire import Repertoire, evaluate_in_context

from .contexts import context_manifest_hash, load_contexts
from .ranking import select_headroom_best, select_nominal_best


FAIL_CLOSED_UTILITY = -10000.0


def _build_pair(
    contexts,
    *,
    seed: int,
    candidate_budget_per_niche: int,
    population_size: int,
):
    training = tuple(c for c in contexts if c.split == "TRAIN")
    nominal_rep = Repertoire()
    headroom_rep = Repertoire()
    serial = []

    for index, context in enumerate(training):
        context_seed = seed * 1009 + index
        generated = _generate_nominal_candidates(
            context,
            seed=context_seed,
            candidate_budget=candidate_budget_per_niche,
            population_size=population_size,
        )
        rows = [
            (genome, evaluate_in_context(genome, context))
            for genome, _utility, _feasible in generated
        ]
        nominal = select_nominal_best(rows, context)
        headroom = select_headroom_best(rows, context)

        nominal_rep.insert(context, nominal.genome, nominal.outcome)
        headroom_rep.insert(context, headroom.genome, headroom.outcome)

        serial.append({
            "context_id": context.context_id,
            "candidate_ids": [genome.identity for genome, _outcome in rows],
            "nominal": nominal.genome.identity,
            "headroom": headroom.genome.identity,
        })

    return {
        "nominal": nominal_rep,
        "headroom": headroom_rep,
        "candidate_set_hash": stable_hash(tuple(serial)),
        "policy_context_evaluations": len(training) * candidate_budget_per_niche,
        "candidate_evaluations": len(training) * candidate_budget_per_niche,
    }


def _row(rep: Repertoire, *, seed: int, algorithm: str, context):
    try:
        entry = rep.select(context)
    except LookupError:
        return {
            "seed": seed,
            "algorithm": algorithm,
            "context_id": context.context_id,
            "utility": FAIL_CLOSED_UTILITY,
            "verified_success": 0,
            "false_completion": 0,
            "unauthorized_actions": 0,
            "evidence_integrity_failures": 0,
            "selection_failure": 1,
            "cost": 0.0,
            "latency": 0.0,
            "human_interventions": 0,
        }

    outcome = evaluate_in_context(entry.genome, context)
    return {
        "seed": seed,
        "algorithm": algorithm,
        "context_id": context.context_id,
        "source_context_id": entry.source_context_id,
        "utility": outcome.utility,
        "verified_success": outcome.verified_success,
        "false_completion": outcome.false_completion,
        "unauthorized_actions": outcome.unauthorized_actions,
        "evidence_integrity_failures": outcome.evidence_integrity_failures,
        "selection_failure": 0,
        "cost": outcome.cost,
        "latency": outcome.latency,
        "human_interventions": outcome.human_interventions,
    }


def run_development_pilot(
    *,
    seeds: tuple[int, ...] = tuple(range(30)),
    candidate_budget_per_niche: int = 256,
    population_size: int = 8,
):
    contexts = load_contexts()
    development = tuple(c for c in contexts if c.split == "DEVELOPMENT")
    if not development:
        raise ValueError("no DEVELOPMENT contexts")

    search_runs = []
    context_rows = []
    seed_worst_deltas = []

    for seed in seeds:
        pair = _build_pair(
            contexts,
            seed=seed,
            candidate_budget_per_niche=candidate_budget_per_niche,
            population_size=population_size,
        )

        search_runs.extend([
            {
                "seed": seed,
                "algorithm": "NOMINAL-RANK",
                "policy_context_evaluations": pair["policy_context_evaluations"],
                "candidate_evaluations": pair["candidate_evaluations"],
                "candidate_set_hash": pair["candidate_set_hash"],
            },
            {
                "seed": seed,
                "algorithm": "HEADROOM-RANK",
                "policy_context_evaluations": pair["policy_context_evaluations"],
                "candidate_evaluations": pair["candidate_evaluations"],
                "candidate_set_hash": pair["candidate_set_hash"],
            },
        ])

        nominal_rows = []
        headroom_rows = []
        for context in development:
            nr = _row(
                pair["nominal"],
                seed=seed,
                algorithm="NOMINAL-RANK",
                context=context,
            )
            hr = _row(
                pair["headroom"],
                seed=seed,
                algorithm="HEADROOM-RANK",
                context=context,
            )
            nominal_rows.append(nr)
            headroom_rows.append(hr)
            context_rows.extend((nr, hr))

        nominal_worst = min(r["utility"] for r in nominal_rows)
        headroom_worst = min(r["utility"] for r in headroom_rows)
        seed_worst_deltas.append({
            "seed": seed,
            "nominal_worst_utility": nominal_worst,
            "headroom_worst_utility": headroom_worst,
            "delta_worst": headroom_worst - nominal_worst,
            "nominal_mean_utility": mean(r["utility"] for r in nominal_rows),
            "headroom_mean_utility": mean(r["utility"] for r in headroom_rows),
        })

    deltas = [row["delta_worst"] for row in seed_worst_deltas]
    headroom_rows = [r for r in context_rows if r["algorithm"] == "HEADROOM-RANK"]
    nominal_rows = [r for r in context_rows if r["algorithm"] == "NOMINAL-RANK"]

    return {
        "experiment_id": "JAR-EXP-0020",
        "phase": "DEVELOPMENT",
        "evidence_class": "EXPLORATORY_DEVELOPMENT",
        "confirmatory": False,
        "held_out_evaluated": False,
        "context_manifest_hash": context_manifest_hash(contexts),
        "development_context_ids": tuple(c.context_id for c in development),
        "configuration": {
            "seeds": seeds,
            "candidate_budget_per_niche": candidate_budget_per_niche,
            "population_size": population_size,
        },
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "seeds": len(seeds),
            "mean_delta_worst": mean(deltas) if deltas else None,
            "headroom_wins": sum(d > 1e-12 for d in deltas),
            "ties": sum(abs(d) <= 1e-12 for d in deltas),
            "headroom_losses": sum(d < -1e-12 for d in deltas),
            "headroom_uar": sum(r["unauthorized_actions"] for r in headroom_rows),
            "nominal_uar": sum(r["unauthorized_actions"] for r in nominal_rows),
            "headroom_evidence_failures": sum(r["evidence_integrity_failures"] for r in headroom_rows),
            "nominal_evidence_failures": sum(r["evidence_integrity_failures"] for r in nominal_rows),
            "headroom_selection_failures": sum(r["selection_failure"] for r in headroom_rows),
            "nominal_selection_failures": sum(r["selection_failure"] for r in nominal_rows),
        },
    }
