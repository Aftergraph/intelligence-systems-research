from __future__ import annotations

from pathlib import Path
import json
import random
from statistics import mean
from typing import Any

from experiments.verge.models import PolicyGenome, stable_hash
from experiments.verge_crucible.search import _generate_nominal_candidates
from experiments.verge_repertoire.repertoire import Repertoire, evaluate_in_context
from experiments.verge_headroom.contexts import load_contexts


PARENT_RESULT_PATH = Path("data/verge_headroom_heldout_confirmatory_v1.json")


def _headroom_key(genome: PolicyGenome, context, outcome) -> tuple:
    confidence_margin = genome.confidence_threshold - context.min_confidence
    verification_margin = genome.verification_depth - context.min_verification
    retry_margin = genome.retry_ceiling - context.min_retries
    normalized_min_margin = min(
        confidence_margin / 0.10,
        verification_margin / 2.0,
        retry_margin / 2.0,
    )
    return (
        normalized_min_margin,
        outcome.utility,
        -outcome.cost,
        -outcome.latency,
        genome.identity,
    )


def _nominal_key(genome: PolicyGenome, outcome) -> tuple:
    return (
        outcome.utility,
        -outcome.cost,
        -outcome.latency,
        genome.identity,
    )


def _select_pair(rows, context):
    feasible = [
        (genome, outcome)
        for genome, outcome in rows
        if outcome.feasible
        and genome.confidence_threshold >= context.min_confidence
        and genome.verification_depth >= context.min_verification
        and genome.retry_ceiling >= context.min_retries
    ]
    if not feasible:
        raise LookupError("no feasible elite")

    nominal_genome, nominal_outcome = max(
        feasible,
        key=lambda pair: _nominal_key(pair[0], pair[1]),
    )
    headroom_genome, headroom_outcome = max(
        feasible,
        key=lambda pair: _headroom_key(pair[0], context, pair[1]),
    )
    return (
        (nominal_genome, nominal_outcome),
        (headroom_genome, headroom_outcome),
    )


def _build_pair(contexts, seed: int, candidate_budget_per_niche: int = 256, population_size: int = 8):
    training = tuple(c for c in contexts if c.split == "TRAIN")
    nominal_rep = Repertoire()
    headroom_rep = Repertoire()
    selections = []

    for index, context in enumerate(training):
        generated = _generate_nominal_candidates(
            context,
            seed=seed * 1009 + index,
            candidate_budget=candidate_budget_per_niche,
            population_size=population_size,
        )
        rows = [
            (genome, evaluate_in_context(genome, context))
            for genome, _utility, _feasible in generated
        ]
        nominal, headroom = _select_pair(rows, context)
        nominal_rep.insert(context, nominal[0], nominal[1])
        headroom_rep.insert(context, headroom[0], headroom[1])
        selections.append({
            "context_id": context.context_id,
            "nominal": nominal[0].identity,
            "headroom": headroom[0].identity,
        })

    return nominal_rep, headroom_rep, tuple(selections)


def _select_utility(rep: Repertoire, context) -> dict[str, Any]:
    try:
        entry = rep.select(context)
    except LookupError:
        return {
            "utility": -10000.0,
            "unauthorized_actions": 0,
            "evidence_integrity_failures": 0,
            "verified_success": 0,
            "selection_failure": 1,
        }
    outcome = evaluate_in_context(entry.genome, context)
    return {
        "utility": outcome.utility,
        "unauthorized_actions": outcome.unauthorized_actions,
        "evidence_integrity_failures": outcome.evidence_integrity_failures,
        "verified_success": outcome.verified_success,
        "selection_failure": 0,
    }


def _bootstrap(values, resamples=10000, seed=2021):
    rng = random.Random(seed)
    samples = []
    for _ in range(resamples):
        draw = [rng.choice(values) for _ in range(len(values))]
        samples.append(mean(draw))
    samples.sort()
    return samples[249], samples[9749]


def run_replication() -> dict[str, Any]:
    contexts = load_contexts()
    heldout = tuple(c for c in contexts if c.split == "HELD_OUT")
    seed_deltas = []
    selection_records = []
    candidate_safety = {
        "unauthorized_actions": 0,
        "evidence_integrity_failures": 0,
        "verified_successes": 0,
        "selection_failures": 0,
    }

    for seed in range(30):
        nominal_rep, headroom_rep, selections = _build_pair(contexts, seed)
        selection_records.append({
            "seed": seed,
            "selections": selections,
        })

        nominal_utils = []
        headroom_utils = []
        for context in heldout:
            nominal = _select_utility(nominal_rep, context)
            headroom = _select_utility(headroom_rep, context)
            nominal_utils.append(nominal["utility"])
            headroom_utils.append(headroom["utility"])
            candidate_safety["unauthorized_actions"] += headroom["unauthorized_actions"]
            candidate_safety["evidence_integrity_failures"] += headroom["evidence_integrity_failures"]
            candidate_safety["verified_successes"] += headroom["verified_success"]
            candidate_safety["selection_failures"] += headroom["selection_failure"]

        nw = min(nominal_utils)
        hw = min(headroom_utils)
        seed_deltas.append({
            "seed": seed,
            "delta_worst": hw - nw,
            "nominal_worst_utility": nw,
            "headroom_worst_utility": hw,
        })

    deltas = [row["delta_worst"] for row in seed_deltas]
    ci = _bootstrap(deltas)
    result = {
        "experiment_id": "JAR-EXP-0021",
        "evidence_class": "INTERNAL_IMPLEMENTATION_REPLICATION",
        "parent_experiment_id": "JAR-EXP-0020",
        "seed_deltas": seed_deltas,
        "summary": {
            "mean_delta_worst": mean(deltas),
            "bootstrap_ci95": ci,
            "wins": sum(d > 1e-12 for d in deltas),
            "ties": sum(abs(d) <= 1e-12 for d in deltas),
            "losses": sum(d < -1e-12 for d in deltas),
            "candidate_safety": candidate_safety,
            "positive_support": bool(
                candidate_safety["unauthorized_actions"] == 0
                and candidate_safety["evidence_integrity_failures"] == 0
                and mean(deltas) > 0
                and ci[0] > 0
            ),
        },
        "selection_records_hash": stable_hash(tuple(selection_records)),
    }
    return result


def compare_to_parent(parent_path: Path = PARENT_RESULT_PATH) -> dict[str, Any]:
    replica = run_replication()
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_deltas = [
        {
            "seed": row["seed"],
            "delta_worst": row["delta_worst"],
            "nominal_worst_utility": row["nominal_worst_utility"],
            "headroom_worst_utility": row["headroom_worst_utility"],
        }
        for row in parent["seed_worst_deltas"]
    ]
    return {
        "replica": replica,
        "seed_delta_vector_exact_match": replica["seed_deltas"] == parent_deltas,
        "mean_exact_match": replica["summary"]["mean_delta_worst"] == parent["summary"]["mean_delta_worst"],
        "ci_exact_match": tuple(replica["summary"]["bootstrap_ci95"]) == tuple(parent["summary"]["bootstrap_ci95"]),
        "support_verdict_match": replica["summary"]["positive_support"] == parent["summary"]["positive_support"],
    }
