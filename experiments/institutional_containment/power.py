"""Outcome-blind sample-size planning for STUDY-012.

The preregistered experiment is paired by workload/scenario/replicate. This
planner uses an intentionally conservative independent-proportions
approximation as an upper-bound planning tool so the eventual paired analysis
is not underpowered because of optimistic correlation assumptions.
"""
from __future__ import annotations

from math import ceil, sqrt
from statistics import NormalDist

PLANNING_METHOD = "conservative_independent_two_proportion_upper_bound_v1"


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
    replicates = ceil(n_per_condition / scenarios)
    return scenarios * replicates * conditions


def build_frozen_power_plan(
    *,
    domains: int,
    scenarios_per_domain: int,
    conditions: int = 7,
    baseline_rate: float = 0.50,
    minimum_detectable_difference: float = 0.10,
    alpha: float = 0.01,
    power: float = 0.80,
) -> dict[str, object]:
    """Build the outcome-blind confirmatory sampling plan.

    Each replicate contributes one paired observation for every
    domain-by-scenario cell in every condition. Domain count is therefore part
    of the sampling math; omitting it would understate observations per
    replicate and misstate the confirmatory run budget.
    """
    if domains <= 0 or scenarios_per_domain <= 0 or conditions <= 0:
        raise ValueError("domains, scenarios_per_domain, and conditions must be positive")

    n_required = conservative_two_proportion_n_per_condition(
        baseline_rate=baseline_rate,
        minimum_detectable_difference=minimum_detectable_difference,
        alpha=alpha,
        power=power,
    )
    pairs_per_replicate = domains * scenarios_per_domain
    replicates = ceil(n_required / pairs_per_replicate)
    observations_per_condition = pairs_per_replicate * replicates
    total_runs = observations_per_condition * conditions

    return {
        "study_id": "STUDY-012",
        "experiment_id": "ICT-EXP-0001",
        "status": "FROZEN_POWER_PLAN_V1",
        "planning_method": PLANNING_METHOD,
        "outcome_blind": True,
        "baseline_rate": baseline_rate,
        "minimum_detectable_difference": minimum_detectable_difference,
        "alpha": alpha,
        "power": power,
        "domains": domains,
        "scenarios_per_domain": scenarios_per_domain,
        "conditions": conditions,
        "n_per_condition_required": n_required,
        "pairs_per_replicate": pairs_per_replicate,
        "replicates": replicates,
        "observations_per_condition": observations_per_condition,
        "total_runs": total_runs,
    }
