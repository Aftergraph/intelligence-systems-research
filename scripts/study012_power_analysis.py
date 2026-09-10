"""Outcome-blind sample-size planning for STUDY-012 / ICT-EXP-001."""
from __future__ import annotations

import math
from statistics import NormalDist


def conservative_two_proportion_n(
    *,
    alpha_two_sided: float,
    power: float,
    baseline_rate: float,
    minimum_material_difference: float,
) -> int:
    """Return conservative per-condition n using an independent-proportions bound.

    STUDY-012's primary analysis is paired. Before outcomes exist, its discordance
    rate is unknown, so this independent-proportions approximation is deliberately
    used as a conservative planning bound rather than estimating paired power from
    observed data.
    """
    if not 0 < alpha_two_sided < 1:
        raise ValueError("alpha_two_sided must be between 0 and 1")
    if not 0 < power < 1:
        raise ValueError("power must be between 0 and 1")
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1")
    if not 0 < minimum_material_difference < 1:
        raise ValueError("minimum_material_difference must be between 0 and 1")
    treatment_rate = baseline_rate - minimum_material_difference
    if not 0 < treatment_rate < 1:
        raise ValueError("baseline_rate - minimum_material_difference must be between 0 and 1")

    p_bar = (baseline_rate + treatment_rate) / 2
    z_alpha = NormalDist().inv_cdf(1 - alpha_two_sided / 2)
    z_power = NormalDist().inv_cdf(power)
    numerator = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_power * math.sqrt(
            baseline_rate * (1 - baseline_rate)
            + treatment_rate * (1 - treatment_rate)
        )
    ) ** 2
    return math.ceil(numerator / (minimum_material_difference**2))
