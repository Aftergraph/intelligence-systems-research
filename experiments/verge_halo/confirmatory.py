from __future__ import annotations

from pathlib import Path
import json
import random
from statistics import mean
from typing import Any

from experiments.verge.models import stable_hash
from experiments.verge_repertoire.repertoire import (
    Repertoire,
    evaluate_in_context,
    evolve_fixed_repertoire,
)

from .contexts import MissionContext, context_manifest_hash, load_contexts
from .halo import select_halo_robust


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


def _restore_repertoire(result, contexts_by_id) -> Repertoire:
    repertoire = Repertoire()
    for entry in result.repertoire:
        source = contexts_by_id[entry.source_context_id]
        repertoire.insert(source, entry.genome, entry.outcome)
    return repertoire


def _failure_row(
    *,
    selector: str,
    seed: int,
    context_id: str,
    repertoire_hash: str,
    utility: float,
) -> dict[str, Any]:
    return {
        "seed": seed,
        "selector": selector,
        "context_id": context_id,
        "repertoire_hash": repertoire_hash,
        "source_context_id": None,
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
        "selector_evaluations": 0,
        "halo_worst_selection_utility": None,
    }


def _outcome_row(
    *,
    selector: str,
    seed: int,
    context: MissionContext,
    entry,
    repertoire_hash: str,
    selector_evaluations: int,
    halo_worst_selection_utility: float | None = None,
) -> dict[str, Any]:
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
        "halo_worst_selection_utility": halo_worst_selection_utility,
    }


def _select_nominal(
    repertoire: Repertoire,
    *,
    seed: int,
    context: MissionContext,
    repertoire_hash: str,
    failure_utility: float,
) -> dict[str, Any]:
    try:
        entry = repertoire.select(context)
    except LookupError:
        return _failure_row(
            selector="NOMINAL",
            seed=seed,
            context_id=context.context_id,
            repertoire_hash=repertoire_hash,
            utility=failure_utility,
        )
    return _outcome_row(
        selector="NOMINAL",
        seed=seed,
        context=context,
        entry=entry,
        repertoire_hash=repertoire_hash,
        selector_evaluations=len(repertoire),
    )


def _select_halo(
    repertoire: Repertoire,
    *,
    seed: int,
    context: MissionContext,
    repertoire_hash: str,
    failure_utility: float,
    halo: dict[str, Any],
) -> dict[str, Any]:
    try:
        selection = select_halo_robust(
            repertoire,
            context,
            confidence_shocks=tuple(
                float(value)
                for value in halo["confidence_shocks"]
            ),
            latency_shocks=tuple(
                float(value)
                for value in halo["latency_shocks"]
            ),
            cost_shocks=tuple(
                float(value)
                for value in halo["cost_shocks"]
            ),
        )
    except LookupError:
        return _failure_row(
            selector="HALO",
            seed=seed,
            context_id=context.context_id,
            repertoire_hash=repertoire_hash,
            utility=failure_utility,
        )
    return _outcome_row(
        selector="HALO",
        seed=seed,
        context=context,
        entry=selection.entry,
        repertoire_hash=repertoire_hash,
        selector_evaluations=selection.halo_evaluations,
        halo_worst_selection_utility=selection.worst_utility,
    )


def _totals(rows: list[dict[str, Any]], selector: str) -> dict[str, Any]:
    selected = [row for row in rows if row["selector"] == selector]
    verified = sum(row["verified_success"] for row in selected)
    cost = sum(row["cost"] for row in selected)
    return {
        "contexts": len(selected),
        "verified_successes": verified,
        "false_completions": sum(
            row["false_completion"] for row in selected
        ),
        "unauthorized_actions": sum(
            row["unauthorized_actions"] for row in selected
        ),
        "evidence_integrity_failures": sum(
            row["evidence_integrity_failures"] for row in selected
        ),
        "selection_failures": sum(
            row["selection_failure"] for row in selected
        ),
        "recovery_successes": sum(
            row["recovery_success"] for row in selected
        ),
        "human_interventions": sum(
            row["human_interventions"] for row in selected
        ),
        "cost": cost,
        "cpvo": cost / verified if verified else None,
        "latency": sum(row["latency"] for row in selected),
        "selector_evaluations": sum(
            row["selector_evaluations"] for row in selected
        ),
        "mean_utility": (
            mean(row["utility"] for row in selected)
            if selected else None
        ),
    }


def run_confirmatory(
    contexts: tuple[MissionContext, ...],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    actual_context_hash = context_manifest_hash(contexts)
    if actual_context_hash != manifest["context_manifest_hash"]:
        raise ValueError("context manifest hash mismatch")
    if manifest["candidate_selector"] != "HALO":
        raise ValueError("unexpected candidate selector")
    if manifest["comparator_selector"] != "NOMINAL":
        raise ValueError("unexpected comparator selector")
    if manifest["shared_search"] != "R5-C-fixed-operator-repertoire":
        raise ValueError("unexpected shared search")

    heldout = tuple(
        context for context in contexts
        if context.split == "HELD_OUT"
    )
    if not heldout:
        raise ValueError("no HELD_OUT contexts")
    by_id = {context.context_id: context for context in contexts}

    seeds = tuple(int(seed) for seed in manifest["seeds"])
    population_size = int(manifest["population_size"])
    generations = int(manifest["generations"])
    failure_utility = float(
        manifest["failure_handling"]["no_eligible_elite"][
            "primary_utility"
        ]
    )

    search_runs: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    seed_worst_deltas: list[dict[str, Any]] = []

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
            "algorithm": manifest["shared_search"],
            "policy_context_evaluations": search.evaluations,
            "repertoire_hash": repertoire_hash,
        })

        nominal_rows: list[dict[str, Any]] = []
        halo_rows: list[dict[str, Any]] = []

        for context in heldout:
            nominal = _select_nominal(
                repertoire,
                seed=seed,
                context=context,
                repertoire_hash=repertoire_hash,
                failure_utility=failure_utility,
            )
            halo = _select_halo(
                repertoire,
                seed=seed,
                context=context,
                repertoire_hash=repertoire_hash,
                failure_utility=failure_utility,
                halo=manifest["halo"],
            )
            nominal_rows.append(nominal)
            halo_rows.append(halo)
            context_rows.extend((nominal, halo))

        nominal_worst = min(row["utility"] for row in nominal_rows)
        halo_worst = min(row["utility"] for row in halo_rows)
        seed_worst_deltas.append({
            "seed": seed,
            "nominal_worst_actual_utility": nominal_worst,
            "halo_worst_actual_utility": halo_worst,
            "delta_worst": halo_worst - nominal_worst,
            "nominal_mean_actual_utility": mean(
                row["utility"] for row in nominal_rows
            ),
            "halo_mean_actual_utility": mean(
                row["utility"] for row in halo_rows
            ),
        })

    deltas = [row["delta_worst"] for row in seed_worst_deltas]
    bootstrap = manifest["bootstrap"]
    ci = paired_bootstrap_ci(
        deltas,
        resamples=int(bootstrap["resamples"]),
        rng_seed=int(bootstrap["rng_seed"]),
        lower_rank=int(bootstrap["lower_rank"]),
        upper_rank=int(bootstrap["upper_rank"]),
    )

    halo_totals = _totals(context_rows, "HALO")
    nominal_totals = _totals(context_rows, "NOMINAL")

    safety_by_context = {}
    for context in heldout:
        rows = [
            row for row in context_rows
            if row["selector"] == "HALO"
            and row["context_id"] == context.context_id
        ]
        safety_by_context[context.context_id] = sum(
            row["unauthorized_actions"]
            + row["evidence_integrity_failures"]
            for row in rows
        )

    safety_gate = manifest["safety_gate"]
    safety_pass = (
        halo_totals["unauthorized_actions"]
        <= int(safety_gate["max_observed_unauthorized_actions"])
        and halo_totals["evidence_integrity_failures"]
        <= int(
            safety_gate[
                "max_observed_evidence_integrity_failures"
            ]
        )
        and all(value == 0 for value in safety_by_context.values())
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
        "shared_search": manifest["shared_search"],
        "candidate_selector": manifest["candidate_selector"],
        "comparator_selector": manifest["comparator_selector"],
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "n_seeds": len(seeds),
            "mean_delta_worst": mean_delta,
            "bootstrap_ci95": ci,
            "halo_wins": sum(delta > 1e-12 for delta in deltas),
            "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
            "halo_losses": sum(delta < -1e-12 for delta in deltas),
            "halo_totals": halo_totals,
            "nominal_totals": nominal_totals,
            "candidate_context_safety_failures": safety_by_context,
            "safety_gate_pass": safety_pass,
            "positive_support": bool(
                safety_pass
                and mean_delta > 0.0
                and ci[0] > 0.0
            ),
        },
    }


def load_analysis_manifest(
    path: Path | None = None,
) -> dict[str, Any]:
    target = path or _MANIFEST_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def run_frozen_confirmatory() -> dict[str, Any]:
    return run_confirmatory(
        load_contexts(),
        load_analysis_manifest(),
    )
