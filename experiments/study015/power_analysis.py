"""Draft power/sensitivity utilities for STUDY-015.

These are planning calculations only. They do not freeze sample size.
"""
from __future__ import annotations

import math


def norm_ppf(p: float) -> float:
    if not 0 < p < 1:
        raise ValueError("p must be in (0,1)")
    a = [2.515517, 0.802853, 0.010328]
    b = [1.432788, 0.189269, 0.001308]
    if p < 0.5:
        t = math.sqrt(-2 * math.log(p))
        sign = -1
    else:
        t = math.sqrt(-2 * math.log(1 - p))
        sign = 1
    num = a[0] + a[1] * t + a[2] * t * t
    den = 1 + b[0] * t + b[1] * t + b[2] * t * t * t
    return sign * (t - num / den)


def paired_binary_planning_n(
    *,
    net_difference: float,
    discordant_rate: float,
    alpha: float,
    power: float,
) -> int:
    """Conservative normal-approximation planning N for a paired binary contrast.

    Uses Var(diff) <= discordant_rate / n. Final freeze should verify power
    using exact or simulation-based calculations under the chosen alternatives.
    """
    if not 0 < abs(net_difference) < 1:
        raise ValueError("net_difference must be non-zero and within (-1,1)")
    if not 0 < discordant_rate <= 1:
        raise ValueError("discordant_rate must be in (0,1]")
    z_alpha = norm_ppf(1 - alpha / 2)
    z_beta = norm_ppf(power)
    n = ((z_alpha + z_beta) ** 2 * discordant_rate) / (net_difference ** 2)
    return math.ceil(n)


def paired_continuous_planning_n(*, standardized_effect: float, alpha: float, power: float) -> int:
    if standardized_effect <= 0:
        raise ValueError("standardized_effect must be positive")
    z_alpha = norm_ppf(1 - alpha / 2)
    z_beta = norm_ppf(power)
    return math.ceil(((z_alpha + z_beta) / standardized_effect) ** 2)


def draft_plan() -> dict:
    primary_contrasts = 8
    alpha_family = 0.05
    conservative_alpha = alpha_family / primary_contrasts
    scenarios = {
        "binary_medium": paired_binary_planning_n(
            net_difference=0.15,
            discordant_rate=0.30,
            alpha=conservative_alpha,
            power=0.80,
        ),
        "binary_small": paired_binary_planning_n(
            net_difference=0.10,
            discordant_rate=0.30,
            alpha=conservative_alpha,
            power=0.80,
        ),
        "continuous_dz_0_35": paired_continuous_planning_n(
            standardized_effect=0.35,
            alpha=conservative_alpha,
            power=0.80,
        ),
    }
    return {
        "status": "DRAFT_NOT_FROZEN",
        "familywise_alpha": alpha_family,
        "planning_contrasts": primary_contrasts,
        "conservative_per_contrast_alpha": conservative_alpha,
        "target_power": 0.80,
        "multiplicity_candidate": "Holm-Bonferroni for frozen primary family; conservative Bonferroni used for planning",
        "scenarios": scenarios,
        "freeze_requirement": "Run exact/simulation sensitivity analysis after condition feasibility and observed discordance estimates are available; freeze N before confirmatory execution.",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(draft_plan(), indent=2, sort_keys=True))
