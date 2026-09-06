from __future__ import annotations

from math import sqrt
import random
from statistics import median


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be > 0")
    if successes < 0 or successes > total:
        raise ValueError("successes must be between 0 and total")
    p = successes / total
    denominator = 1 + (z * z) / total
    center = (p + (z * z) / (2 * total)) / denominator
    radius = z * sqrt((p * (1 - p) / total) + (z * z) / (4 * total * total)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def newcombe_difference_interval(
    control_successes: int,
    control_total: int,
    treatment_successes: int,
    treatment_total: int,
    z: float = 1.959963984540054,
) -> tuple[float, float]:
    """Conservative Newcombe/Wilson interval for treatment minus control success rate."""
    control_low, control_high = wilson_interval(control_successes, control_total, z=z)
    treatment_low, treatment_high = wilson_interval(treatment_successes, treatment_total, z=z)
    return max(-1.0, treatment_low - control_high), min(1.0, treatment_high - control_low)


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot take percentile of empty values")
    index = round((len(sorted_values) - 1) * probability)
    return sorted_values[index]


def bootstrap_median_difference(control: list[float], treatment: list[float], seed: int, resamples: int = 10_000) -> dict:
    if not control or not treatment:
        raise ValueError("control and treatment must be non-empty")
    if resamples < 1:
        raise ValueError("resamples must be >= 1")
    rng = random.Random(seed)
    control_values = [float(value) for value in control]
    treatment_values = [float(value) for value in treatment]
    diffs = []
    for _ in range(resamples):
        c = [rng.choice(control_values) for _ in control_values]
        t = [rng.choice(treatment_values) for _ in treatment_values]
        diffs.append(median(t) - median(c))
    diffs.sort()
    observed = median(treatment_values) - median(control_values)
    return {
        "observed_difference": observed,
        "ci_low": _percentile(diffs, 0.025),
        "ci_high": _percentile(diffs, 0.975),
        "resamples": resamples,
        "seed": seed,
    }


def paired_bootstrap_median_reduction(
    control: list[float],
    treatment: list[float],
    seed: int,
    resamples: int = 10_000,
) -> dict:
    """Estimate median proportional reduction while preserving preregistered pair identity."""
    if not control or not treatment:
        raise ValueError("control and treatment must be non-empty")
    if len(control) != len(treatment):
        raise ValueError("control and treatment must have equal length for paired bootstrap")
    if resamples < 1:
        raise ValueError("resamples must be >= 1")

    control_values = [float(value) for value in control]
    treatment_values = [float(value) for value in treatment]
    if any(value <= 0.0 for value in control_values):
        raise ValueError("control values must be > 0 for proportional reduction")

    def reduction(c: list[float], t: list[float]) -> float:
        control_median = median(c)
        if control_median <= 0.0:
            raise ValueError("control median must be > 0 for proportional reduction")
        return (control_median - median(t)) / control_median

    rng = random.Random(seed)
    n = len(control_values)
    reductions: list[float] = []
    for _ in range(resamples):
        indices = [rng.randrange(n) for _ in range(n)]
        c = [control_values[index] for index in indices]
        t = [treatment_values[index] for index in indices]
        reductions.append(reduction(c, t))

    reductions.sort()
    observed = reduction(control_values, treatment_values)
    return {
        "method": "paired_percentile_bootstrap",
        "observed_reduction": observed,
        "ci_low": _percentile(reductions, 0.025),
        "ci_high": _percentile(reductions, 0.975),
        "resamples": resamples,
        "seed": seed,
    }


def _base_failures(results: dict) -> list[str]:
    reasons = []
    if int(results.get("new_correctness_failures", 0)) > 0:
        reasons.append("new_correctness_failures")
    if int(results.get("safety_regressions", 0)) > 0:
        reasons.append("safety_regressions")
    return reasons


def _attempts_ready(results: dict, conditions: tuple[str, ...], minimum: int) -> bool:
    attempts = results.get("mission_attempts_per_condition", {})
    return all(int(attempts.get(condition, 0)) >= minimum for condition in conditions)


def _interval(mapping: dict, key: str) -> tuple[float, float] | None:
    raw = mapping.get(key)
    if not isinstance(raw, dict) or "ci_low" not in raw or "ci_high" not in raw:
        return None
    low = float(raw["ci_low"])
    high = float(raw["ci_high"])
    if low > high:
        return None
    return low, high


def evaluate_gates(results: dict, protocol: dict) -> dict:
    """Evaluate preregistered promotion gates without modifying thresholds."""
    minimum = int(protocol["confirmatory"]["minimum_mission_attempts_per_condition"])
    threshold = protocol["thresholds"]
    analysis = protocol.get("analysis", {})
    require_ci = bool(analysis.get("promotion_requires_ci_lower_bound", False))
    base_failures = _base_failures(results)
    specs = {
        "G-TR": {
            "conditions": ("A", "B"),
            "checks": [
                ("tool_overhead_reduction", threshold["tool_overhead_reduction_min"]),
                ("tool_mission_wall_reduction", threshold["tool_mission_wall_reduction_min"]),
            ],
            "noninferior": "B",
        },
        "G-OB": {
            "conditions": ("A", "C"),
            "checks": [
                ("browser_peak_rss_reduction", threshold["browser_peak_rss_reduction_min"]),
                ("browser_cold_startup_reduction", threshold["browser_cold_startup_reduction_min"]),
                ("browser_compatibility", threshold["browser_compatibility_min"]),
            ],
            "noninferior": "C",
        },
        "G-COMB": {
            "conditions": ("A", "D"),
            "checks": [("combined_mission_wall_reduction", threshold["combined_mission_wall_reduction_min"])],
            "noninferior": "D",
        },
    }

    metric_intervals = results.get("metric_confidence_intervals", {})
    success_intervals = results.get("mission_success_difference_intervals", {})
    margin = float(threshold["mission_success_noninferiority_margin"])
    verdicts = {}

    for gate, spec in specs.items():
        if base_failures:
            verdicts[gate] = {"verdict": "FAIL", "reasons": list(base_failures)}
            continue
        if not _attempts_ready(results, spec["conditions"], minimum):
            verdicts[gate] = {"verdict": "INCONCLUSIVE", "reasons": ["insufficient_confirmatory_attempts"]}
            continue

        hard_failures: list[str] = []
        uncertainties: list[str] = []
        for metric, required in spec["checks"]:
            actual = float(results.get(metric, float("-inf")))
            if actual < float(required):
                hard_failures.append(f"{metric}_below_threshold")
                continue
            if require_ci:
                interval = _interval(metric_intervals, metric)
                if interval is None:
                    uncertainties.append(f"{metric}_ci_missing")
                    continue
                low, high = interval
                if not (low <= actual <= high):
                    uncertainties.append(f"{metric}_ci_invalid")
                elif low < float(required):
                    uncertainties.append(f"{metric}_ci_below_threshold")

        success_interval = _interval(success_intervals, spec["noninferior"])
        if require_ci:
            if success_interval is None:
                uncertainties.append("mission_success_noninferiority_ci_missing")
            else:
                low, high = success_interval
                if low < -margin:
                    if high < -margin:
                        hard_failures.append("mission_success_noninferiority_failed")
                    else:
                        uncertainties.append("mission_success_noninferiority_ci_not_established")
        else:
            noninferior = results.get("mission_success_noninferior", {})
            if noninferior.get(spec["noninferior"]) is not True:
                hard_failures.append("mission_success_noninferiority_failed")

        if hard_failures:
            verdicts[gate] = {"verdict": "FAIL", "reasons": hard_failures + uncertainties}
        elif uncertainties:
            verdicts[gate] = {"verdict": "INCONCLUSIVE", "reasons": uncertainties}
        else:
            verdicts[gate] = {"verdict": "PASS", "reasons": []}

    return verdicts
