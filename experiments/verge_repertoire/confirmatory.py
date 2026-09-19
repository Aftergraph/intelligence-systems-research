from __future__ import annotations

from pathlib import Path
import json
import random
from statistics import mean
from typing import Any

from experiments.verge.models import stable_hash

from .contexts import MissionContext, context_manifest_hash, load_contexts
from .repertoire import Repertoire, evaluate_in_context, evolve_fixed_repertoire
from .study import evolve_global_policy


_MANIFEST_PATH = Path(__file__).with_name("analysis_manifest.json")


def paired_bootstrap_ci(
    values: list[float],
    *,
    resamples: int,
    rng_seed: int,
    lower_rank: int,
    upper_rank: int,
) -> tuple[float, float]:
    if not values:
        raise ValueError("values must not be empty")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if not (1 <= lower_rank <= upper_rank <= resamples):
        raise ValueError("bootstrap ranks out of range")

    rng = random.Random(rng_seed)
    samples: list[float] = []
    for _ in range(resamples):
        draw = [rng.choice(values) for _ in range(len(values))]
        samples.append(mean(draw))
    samples.sort()
    return samples[lower_rank - 1], samples[upper_rank - 1]


def _restore_repertoire(result, contexts_by_id: dict[str, MissionContext]) -> Repertoire:
    repertoire = Repertoire()
    for entry in result.repertoire:
        source = contexts_by_id[entry.source_context_id]
        repertoire.insert(source, entry.genome, entry.outcome)
    return repertoire


def _candidate_result(
    repertoire: Repertoire,
    context: MissionContext,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    try:
        selected = repertoire.select(context)
    except LookupError:
        utility = float(
            manifest["failure_handling"]["no_target_feasible_elite"][
                "primary_utility"
            ]
        )
        return {
            "utility": utility,
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
            "source_context_id": None,
        }

    outcome = evaluate_in_context(selected.genome, context)
    return {
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
        "source_context_id": selected.source_context_id,
    }


def _comparator_result(genome, context: MissionContext) -> dict[str, Any]:
    outcome = evaluate_in_context(genome, context)
    return {
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
        "source_context_id": None,
    }


def _metric_totals(rows: list[dict[str, Any]], algorithm: str) -> dict[str, Any]:
    selected = [row for row in rows if row["algorithm"] == algorithm]
    verified = sum(row["verified_success"] for row in selected)
    total_cost = sum(row["cost"] for row in selected)
    return {
        "contexts": len(selected),
        "verified_successes": verified,
        "false_completions": sum(row["false_completion"] for row in selected),
        "unauthorized_actions": sum(row["unauthorized_actions"] for row in selected),
        "evidence_integrity_failures": sum(
            row["evidence_integrity_failures"] for row in selected
        ),
        "selection_failures": sum(row["selection_failure"] for row in selected),
        "recovery_successes": sum(row["recovery_success"] for row in selected),
        "cost": total_cost,
        "latency": sum(row["latency"] for row in selected),
        "human_interventions": sum(
            row["human_interventions"] for row in selected
        ),
        "cpvo": total_cost / verified if verified else None,
    }


def run_confirmatory(
    contexts: tuple[MissionContext, ...],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    actual_context_hash = context_manifest_hash(contexts)
    if actual_context_hash != manifest["context_manifest_hash"]:
        raise ValueError("context manifest hash mismatch")
    if manifest["candidate"] != "R5-C-verge-repertoire-core":
        raise ValueError("unexpected primary candidate")
    if manifest["comparator"] != "R1-global-evolved":
        raise ValueError("unexpected primary comparator")

    heldout = tuple(
        context for context in contexts if context.split == "HELD_OUT"
    )
    if not heldout:
        raise ValueError("no HELD_OUT contexts")
    by_id = {context.context_id: context for context in contexts}

    seeds = tuple(int(seed) for seed in manifest["seeds"])
    population_size = int(manifest["population_size"])
    generations = int(manifest["generations"])

    context_rows: list[dict[str, Any]] = []
    seed_deltas: list[dict[str, Any]] = []
    search_runs: list[dict[str, Any]] = []

    for seed in seeds:
        candidate_search = evolve_fixed_repertoire(
            contexts,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        comparator_search = evolve_global_policy(
            contexts,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        if candidate_search.evaluations != comparator_search.policy_context_evaluations:
            raise ValueError("primary search budgets do not match")

        repertoire = _restore_repertoire(candidate_search, by_id)
        search_runs.extend([
            {
                "seed": seed,
                "algorithm": manifest["candidate"],
                "policy_context_evaluations": candidate_search.evaluations,
            },
            {
                "seed": seed,
                "algorithm": manifest["comparator"],
                "policy_context_evaluations": comparator_search.policy_context_evaluations,
            },
        ])

        candidate_utilities: list[float] = []
        comparator_utilities: list[float] = []

        for context in heldout:
            candidate = _candidate_result(repertoire, context, manifest)
            comparator = _comparator_result(comparator_search.genome, context)

            candidate_utilities.append(float(candidate["utility"]))
            comparator_utilities.append(float(comparator["utility"]))

            context_rows.append({
                "seed": seed,
                "context_id": context.context_id,
                "algorithm": manifest["candidate"],
                **candidate,
            })
            context_rows.append({
                "seed": seed,
                "context_id": context.context_id,
                "algorithm": manifest["comparator"],
                **comparator,
            })

        candidate_mean = mean(candidate_utilities)
        comparator_mean = mean(comparator_utilities)
        seed_deltas.append({
            "seed": seed,
            "candidate_mean_utility": candidate_mean,
            "comparator_mean_utility": comparator_mean,
            "delta": candidate_mean - comparator_mean,
        })

    deltas = [row["delta"] for row in seed_deltas]
    bootstrap = manifest["bootstrap"]
    ci = paired_bootstrap_ci(
        deltas,
        resamples=int(bootstrap["resamples"]),
        rng_seed=int(bootstrap["rng_seed"]),
        lower_rank=int(bootstrap["lower_rank"]),
        upper_rank=int(bootstrap["upper_rank"]),
    )

    candidate_totals = _metric_totals(context_rows, manifest["candidate"])
    comparator_totals = _metric_totals(context_rows, manifest["comparator"])

    context_safety_failures = {}
    for context in heldout:
        rows = [
            row for row in context_rows
            if row["algorithm"] == manifest["candidate"]
            and row["context_id"] == context.context_id
        ]
        context_safety_failures[context.context_id] = sum(
            row["unauthorized_actions"] + row["evidence_integrity_failures"]
            for row in rows
        )

    safety_gate = manifest["safety_gate"]
    safety_pass = (
        candidate_totals["unauthorized_actions"]
        <= int(safety_gate["max_observed_unauthorized_actions"])
        and candidate_totals["evidence_integrity_failures"]
        <= int(safety_gate["max_observed_evidence_integrity_failures"])
        and all(value == 0 for value in context_safety_failures.values())
    )
    mean_delta = mean(deltas)

    return {
        "experiment_id": manifest["experiment_id"],
        "phase": manifest["phase"],
        "evidence_class": "INTERNAL_SYNTHETIC_HELD_OUT",
        "confirmatory": True,
        "manifest_hash": stable_hash(manifest),
        "context_manifest_hash": actual_context_hash,
        "heldout_context_ids": tuple(
            context.context_id for context in heldout
        ),
        "candidate": manifest["candidate"],
        "comparator": manifest["comparator"],
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_deltas": seed_deltas,
        "summary": {
            "n_seeds": len(seeds),
            "mean_delta": mean_delta,
            "bootstrap_ci95": ci,
            "wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "losses": sum(delta < -1e-12 for delta in deltas),
            "candidate_totals": candidate_totals,
            "comparator_totals": comparator_totals,
            "candidate_context_safety_failures": context_safety_failures,
            "safety_gate_pass": safety_pass,
            "positive_support": bool(
                safety_pass and mean_delta > 0.0 and ci[0] > 0.0
            ),
        },
    }


def load_analysis_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or _MANIFEST_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def run_frozen_confirmatory() -> dict[str, Any]:
    return run_confirmatory(load_contexts(), load_analysis_manifest())
