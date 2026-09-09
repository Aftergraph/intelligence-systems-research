"""Outcome-blind sample-size planning for STUDY-012.

The preregistered experiment is paired by scenario/replicate. This planner uses
an intentionally conservative independent-proportions approximation as an
upper-bound planning tool so the eventual paired analysis is not underpowered
because of optimistic correlation assumptions.
"""
from __future__ import annotations

from math import ceil, sqrt
from statistics import NormalDist


def conservative_two_proportion_n_per_condition(
    *,
    baseline_rate: float = 0.50,
    minimum_detectable_difference: float = 0.10,
    alpha: float = 0.01,
    power: float = 0.80,
) -> int:
    """Return conservative n per condition for a two-sided rate difference.

    This function is used only for planning. It does not inspect outcomes and
    must be called before confirmatory data are generated.
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be in (0, 1)")
    if not 0 < minimum_detectable_difference < 1:
        raise ValueError("minimum_detectable_difference must be in (0, 1)")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not 0 < power < 1:
        raise ValueError("power must be in (0, 1)")

    p1 = baseline_rate
    p2 = min(1.0 - 1e-9, max(1e-9, p1 - minimum_detectable_difference))
    pbar = (p1 + p2) / 2.0
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_beta = NormalDist().inv_cdf(power)

    numerator = (
        z_alpha * sqrt(2.0 * pbar * (1.0 - pbar))
        + z_beta * sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
    ) ** 2
    n = numerator / (p1 - p2) ** 2
    return ceil(n)


def planned_total_runs(
    *,
    scenarios: int,
    conditions: int = 7,
    n_per_condition: int,
) -> int:
    if scenarios <= 0 or conditions <= 0 or n_per_condition <= 0:
        raise ValueError("all planning dimensions must be positive")
    # n_per_condition is interpreted as required observations per condition.
    # Replicates are rounded up so every scenario receives equal weight.
    replicates = ceil(n_per_condition / scenarios)
    return scenarios * replicates * conditions
