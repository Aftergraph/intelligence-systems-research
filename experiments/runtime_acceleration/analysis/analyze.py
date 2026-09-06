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


def evaluate_gates(results: dict, protocol: dict) -> dict:
    """Evaluate preregistered promotion gates without modifying thresholds."""
    minimum = int(protocol["confirmatory"]["minimum_mission_attempts_per_condition"])
    threshold = protocol["thresholds"]
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
    verdicts = {}
    noninferior = results.get("mission_success_noninferior", {})
    for gate, spec in specs.items():
        reasons = list(base_failures)
        if reasons:
            verdicts[gate] = {"verdict": "FAIL", "reasons": reasons}
            continue
        if not _attempts_ready(results, spec["conditions"], minimum):
            verdicts[gate] = {"verdict": "INCONCLUSIVE", "reasons": ["insufficient_confirmatory_attempts"]}
            continue
        for metric, required in spec["checks"]:
            actual = float(results.get(metric, float("-inf")))
            if actual < float(required):
                reasons.append(f"{metric}_below_threshold")
        if noninferior.get(spec["noninferior"]) is not True:
            reasons.append("mission_success_noninferiority_failed")
        verdicts[gate] = {"verdict": "FAIL" if reasons else "PASS", "reasons": reasons}
    return verdicts
