from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from .baselines import run_fixed, run_ga, run_pareto, run_qd, run_random
from .engine import evolve
from .harness import benchmark_manifest_hash, load_cases


def _row(name: str, seed: int, best, evaluations: int) -> dict:
    obj = best.outcome.objectives
    cpvo = obj.cost / obj.verified_success if obj.verified_success else None
    return {
        "algorithm": name,
        "seed": seed,
        "candidate_id": best.genome.identity,
        "best_quality": best.quality,
        "evaluations": evaluations,
        "verified_success": obj.verified_success,
        "false_completion": obj.false_completion,
        "unauthorized_actions": obj.unauthorized_actions,
        "cost": obj.cost,
        "cpvo": cpvo,
        "latency": obj.latency,
        "human_interventions": obj.human_interventions,
        "recovery": obj.recovery,
        "feasible": best.outcome.feasible,
    }


def _summaries(rows: list[dict]) -> dict[str, dict]:
    algorithms = sorted({row["algorithm"] for row in rows})
    result = {}
    for name in algorithms:
        group = [row for row in rows if row["algorithm"] == name]
        cpvos = [row["cpvo"] for row in group if row["cpvo"] is not None]
        result[name] = {
            "runs": len(group),
            "mean_best_quality": mean(row["best_quality"] for row in group),
            "mean_verified_success": mean(row["verified_success"] for row in group),
            "mean_false_completion": mean(row["false_completion"] for row in group),
            "mean_unauthorized_actions": mean(row["unauthorized_actions"] for row in group),
            "mean_cpvo": mean(cpvos) if cpvos else None,
            "mean_latency": mean(row["latency"] for row in group),
            "mean_human_interventions": mean(row["human_interventions"] for row in group),
        }
    return result


def _paired_vs_verge(rows: list[dict]) -> dict[str, dict]:
    by_seed = {}
    for row in rows:
        by_seed.setdefault(row["seed"], {})[row["algorithm"]] = row
    algorithms = sorted({row["algorithm"] for row in rows if row["algorithm"] != "B11-verge"})
    out = {}
    for name in algorithms:
        diffs = []
        wins = ties = losses = 0
        for seed, group in sorted(by_seed.items()):
            if name not in group or "B11-verge" not in group:
                continue
            diff = group["B11-verge"]["best_quality"] - group[name]["best_quality"]
            diffs.append(diff)
            if diff > 1e-12:
                wins += 1
            elif diff < -1e-12:
                losses += 1
            else:
                ties += 1
        out[name] = {
            "paired_runs": len(diffs),
            "mean_quality_delta_verge_minus_baseline": mean(diffs) if diffs else None,
            "verge_wins": wins,
            "ties": ties,
            "verge_losses": losses,
        }
    return out


def run_pilot(
    seeds: tuple[int, ...] = tuple(range(30)),
    population_size: int = 20,
    generations: int = 10,
) -> dict:
    cases = load_cases()
    evaluations = population_size * (generations + 1)
    rows: list[dict] = []
    runners = (run_random, run_fixed, run_ga, run_pareto, run_qd)

    for seed in seeds:
        for runner in runners:
            result = runner(
                cases,
                seed=seed,
                population_size=population_size,
                generations=generations,
            )
            rows.append(_row(result.name, seed, result.best, result.evaluations))
        verge = evolve(
            cases,
            seed=seed,
            population_size=population_size,
            generations=generations,
        )
        rows.append(_row("B11-verge", seed, verge.best, verge.evaluations))

    return {
        "experiment_id": "JAR-EXP-0015",
        "phase": "S2-DETERMINISTIC-EXPLORATORY",
        "evidence_class": "EXPLORATORY_SYNTHETIC",
        "confirmatory": False,
        "claim_boundary": (
            "This synthetic pilot validates implementation mechanics and comparative behavior; "
            "it does not establish real-agent superiority or production readiness."
        ),
        "configuration": {
            "seeds": list(seeds),
            "population_size": population_size,
            "generations": generations,
            "evaluations_per_run": evaluations,
            "benchmark_manifest_hash": benchmark_manifest_hash(cases),
        },
        "summaries": _summaries(rows),
        "paired_vs_verge": _paired_vs_verge(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=30)
    parser.add_argument("--population-size", type=int, default=20)
    parser.add_argument("--generations", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_pilot(
        seeds=tuple(range(args.seed_count)),
        population_size=args.population_size,
        generations=args.generations,
    )
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
