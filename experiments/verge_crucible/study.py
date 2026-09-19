from __future__ import annotations

from statistics import mean

from experiments.verge.models import stable_hash
from experiments.verge_repertoire.repertoire import Repertoire, evaluate_in_context
from experiments.verge_bastion.robust_search import make_training_halo

from .contexts import context_manifest_hash, load_contexts
from .search import evolve_crucible_context, evolve_nominal_context_matched


FAIL_CLOSED_UTILITY = -10000.0


def _build(contexts, *, seed: int, crucible: bool):
    training = tuple(c for c in contexts if c.split == "TRAIN")
    repertoire = Repertoire()
    serial = []
    total_budget = 0
    total_candidates = 0
    robust_survivors = 0

    for index, context in enumerate(training):
        context_seed = seed * 1009 + index
        result = (
            evolve_crucible_context(context, seed=context_seed)
            if crucible
            else evolve_nominal_context_matched(context, seed=context_seed)
        )
        total_budget += result.policy_context_evaluations
        total_candidates += result.candidate_evaluations
        nominal = evaluate_in_context(result.genome, context)
        if nominal.feasible:
            repertoire.insert(context, result.genome, nominal)
        halo = make_training_halo(context)
        if all(evaluate_in_context(result.genome, p).feasible for p in halo):
            robust_survivors += 1
        serial.append({
            "context_id": context.context_id,
            "genome": result.genome.payload(),
            "robust_feasible": result.robust_feasible,
            "worst_halo_utility": result.worst_halo_utility,
        })

    return {
        "repertoire": repertoire,
        "policy_context_evaluations": total_budget,
        "candidate_evaluations": total_candidates,
        "robust_coverage": robust_survivors / len(training),
        "hash": stable_hash(tuple(serial)),
    }


def _row(rep: Repertoire, *, seed: int, algorithm: str, context, rep_hash: str):
    try:
        entry = rep.select(context)
    except LookupError:
        return {
            "seed": seed,
            "algorithm": algorithm,
            "context_id": context.context_id,
            "repertoire_hash": rep_hash,
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
        "repertoire_hash": rep_hash,
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


def run_development_pilot(*, seeds: tuple[int, ...] = tuple(range(30))):
    contexts = load_contexts()
    development = tuple(c for c in contexts if c.split == "DEVELOPMENT")
    search_runs = []
    context_rows = []
    seed_worst_deltas = []
    crucible_coverages = []
    nominal_coverages = []

    for seed in seeds:
        nominal = _build(contexts, seed=seed, crucible=False)
        crucible = _build(contexts, seed=seed, crucible=True)
        if nominal["policy_context_evaluations"] != crucible["policy_context_evaluations"]:
            raise ValueError("search budgets do not match")

        nominal_coverages.append(nominal["robust_coverage"])
        crucible_coverages.append(crucible["robust_coverage"])
        search_runs.extend([
            {
                "seed": seed,
                "algorithm": "NOMINAL-REPERTOIRE",
                "policy_context_evaluations": nominal["policy_context_evaluations"],
                "candidate_evaluations": nominal["candidate_evaluations"],
                "robust_coverage": nominal["robust_coverage"],
            },
            {
                "seed": seed,
                "algorithm": "CRUCIBLE-REPERTOIRE",
                "policy_context_evaluations": crucible["policy_context_evaluations"],
                "candidate_evaluations": crucible["candidate_evaluations"],
                "robust_coverage": crucible["robust_coverage"],
            },
        ])

        nrows = []
        crows = []
        for context in development:
            nr = _row(nominal["repertoire"], seed=seed, algorithm="NOMINAL-REPERTOIRE", context=context, rep_hash=nominal["hash"])
            cr = _row(crucible["repertoire"], seed=seed, algorithm="CRUCIBLE-REPERTOIRE", context=context, rep_hash=crucible["hash"])
            nrows.append(nr)
            crows.append(cr)
            context_rows.extend((nr, cr))

        nw = min(r["utility"] for r in nrows)
        cw = min(r["utility"] for r in crows)
        seed_worst_deltas.append({
            "seed": seed,
            "nominal_worst_utility": nw,
            "crucible_worst_utility": cw,
            "delta_worst": cw - nw,
            "nominal_mean_utility": mean(r["utility"] for r in nrows),
            "crucible_mean_utility": mean(r["utility"] for r in crows),
        })

    deltas = [r["delta_worst"] for r in seed_worst_deltas]
    return {
        "experiment_id": "JAR-EXP-0019",
        "phase": "DEVELOPMENT",
        "evidence_class": "EXPLORATORY_DEVELOPMENT",
        "confirmatory": False,
        "held_out_evaluated": False,
        "context_manifest_hash": context_manifest_hash(contexts),
        "development_context_ids": tuple(c.context_id for c in development),
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "seeds": len(seeds),
            "mean_delta_worst": mean(deltas) if deltas else None,
            "crucible_wins": sum(d > 1e-12 for d in deltas),
            "ties": sum(abs(d) <= 1e-12 for d in deltas),
            "crucible_losses": sum(d < -1e-12 for d in deltas),
            "crucible_train_robust_coverage": mean(crucible_coverages),
            "nominal_train_robust_coverage": mean(nominal_coverages),
        },
    }
