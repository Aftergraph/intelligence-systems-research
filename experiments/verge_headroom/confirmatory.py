from __future__ import annotations

from pathlib import Path
import json
import random
from statistics import mean
from typing import Any

from experiments.verge.models import stable_hash

from .contexts import MissionContext, context_manifest_hash, load_contexts
from .study import _build_pair, _row


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


def _totals(rows: list[dict[str, Any]], algorithm: str) -> dict[str, Any]:
    selected = [row for row in rows if row["algorithm"] == algorithm]
    verified = sum(row["verified_success"] for row in selected)
    cost = sum(row["cost"] for row in selected)
    return {
        "contexts": len(selected),
        "verified_successes": verified,
        "false_completions": sum(row["false_completion"] for row in selected),
        "unauthorized_actions": sum(row["unauthorized_actions"] for row in selected),
        "evidence_integrity_failures": sum(row["evidence_integrity_failures"] for row in selected),
        "selection_failures": sum(row["selection_failure"] for row in selected),
        "human_interventions": sum(row["human_interventions"] for row in selected),
        "cost": cost,
        "cpvo": cost / verified if verified else None,
        "latency": sum(row["latency"] for row in selected),
        "mean_utility": mean(row["utility"] for row in selected) if selected else None,
    }


def run_confirmatory(
    contexts: tuple[MissionContext, ...],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    actual_hash = context_manifest_hash(contexts)
    if actual_hash != manifest["context_manifest_hash"]:
        raise ValueError("context manifest hash mismatch")
    if manifest["candidate"] != "HEADROOM-RANK":
        raise ValueError("unexpected candidate")
    if manifest["comparator"] != "NOMINAL-RANK":
        raise ValueError("unexpected comparator")

    heldout = tuple(c for c in contexts if c.split == "HELD_OUT")
    if not heldout:
        raise ValueError("no HELD_OUT contexts")

    search_runs: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    seed_worst_deltas: list[dict[str, Any]] = []

    for seed in tuple(int(s) for s in manifest["seeds"]):
        pair = _build_pair(
            contexts,
            seed=seed,
            candidate_budget_per_niche=int(manifest["candidate_budget_per_niche"]),
            population_size=int(manifest["population_size"]),
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
        for context in heldout:
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
    bootstrap = manifest["bootstrap"]
    ci = paired_bootstrap_ci(
        deltas,
        resamples=int(bootstrap["resamples"]),
        rng_seed=int(bootstrap["rng_seed"]),
        lower_rank=int(bootstrap["lower_rank"]),
        upper_rank=int(bootstrap["upper_rank"]),
    )

    candidate_totals = _totals(context_rows, "HEADROOM-RANK")
    comparator_totals = _totals(context_rows, "NOMINAL-RANK")

    safety_by_context = {}
    for context in heldout:
        rows = [
            r for r in context_rows
            if r["algorithm"] == "HEADROOM-RANK"
            and r["context_id"] == context.context_id
        ]
        safety_by_context[context.context_id] = sum(
            r["unauthorized_actions"] + r["evidence_integrity_failures"]
            for r in rows
        )

    safety_gate = manifest["safety_gate"]
    safety_pass = (
        candidate_totals["unauthorized_actions"]
        <= int(safety_gate["max_observed_unauthorized_actions"])
        and candidate_totals["evidence_integrity_failures"]
        <= int(safety_gate["max_observed_evidence_integrity_failures"])
        and all(v == 0 for v in safety_by_context.values())
    )
    mean_delta = mean(deltas)

    return {
        "experiment_id": manifest["experiment_id"],
        "phase": manifest["phase"],
        "evidence_class": "INTERNAL_SYNTHETIC_HELD_OUT",
        "confirmatory": True,
        "manifest_hash": stable_hash(manifest),
        "context_manifest_hash": actual_hash,
        "heldout_context_ids": tuple(c.context_id for c in heldout),
        "candidate": manifest["candidate"],
        "comparator": manifest["comparator"],
        "search_runs": search_runs,
        "context_rows": context_rows,
        "seed_worst_deltas": seed_worst_deltas,
        "summary": {
            "n_seeds": len(seed_worst_deltas),
            "mean_delta_worst": mean_delta,
            "bootstrap_ci95": ci,
            "headroom_wins": sum(d > 1e-12 for d in deltas),
            "ties": sum(abs(d) <= 1e-12 for d in deltas),
            "headroom_losses": sum(d < -1e-12 for d in deltas),
            "candidate_totals": candidate_totals,
            "comparator_totals": comparator_totals,
            "candidate_context_safety_failures": safety_by_context,
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
