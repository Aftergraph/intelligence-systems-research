from __future__ import annotations

from statistics import mean

from .baselines import BaselineResult


def _safe_cpvo(run: BaselineResult) -> float | None:
    verified = run.best.outcome.objectives.verified_success
    if verified <= 0:
        return None
    return run.best.outcome.objectives.cost / verified


def summarize_runs(runs: list[BaselineResult]) -> dict[str, float | int | None]:
    if not runs:
        raise ValueError("runs must not be empty")
    cpvos = [value for run in runs if (value := _safe_cpvo(run)) is not None]
    return {
        "runs": len(runs),
        "mean_best_quality": mean(run.best_quality for run in runs),
        "mean_verified_success": mean(run.best.outcome.objectives.verified_success for run in runs),
        "mean_false_completion": mean(run.best.outcome.objectives.false_completion for run in runs),
        "mean_unauthorized_actions": mean(run.best.outcome.objectives.unauthorized_actions for run in runs),
        "mean_cost_per_verified_outcome": mean(cpvos) if cpvos else None,
        "mean_latency": mean(run.best.outcome.objectives.latency for run in runs),
        "mean_human_interventions": mean(run.best.outcome.objectives.human_interventions for run in runs),
    }
