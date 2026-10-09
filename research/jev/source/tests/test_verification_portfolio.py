from __future__ import annotations

import pytest

from jev_engineering.verification_portfolio import (
    NoAdmissibleVerification,
    VerificationMethod,
    VerificationPortfolioOptimizer,
    VerificationRequirement,
)


def test_optimizer_selects_cheapest_portfolio_that_meets_assurance_and_detection() -> None:
    methods = [
        VerificationMethod("lint", 0, 0.35, 0.001, 200, "ruff check ."),
        VerificationMethod("unit", 1, 0.75, 0.01, 1200, "pytest -q tests/unit"),
        VerificationMethod("integration", 2, 0.80, 0.03, 3500, "pytest -q tests/integration"),
        VerificationMethod("independent", 4, 0.90, 0.10, 5000, "sentinel verify"),
    ]
    req = VerificationRequirement(
        required_assurance=2,
        required_detection=0.90,
        defect_probability=0.20,
        impact_usd=100.0,
    )
    plan = VerificationPortfolioOptimizer(methods).plan(req)
    assert [m.method_id for m in plan.methods] == ["unit", "integration"]
    assert plan.assurance_level >= 2
    assert plan.combined_detection >= 0.90
    assert plan.total_cost_usd == pytest.approx(0.04)
    assert plan.value_of_verification > 0


def test_high_assurance_requires_independent_method_even_if_low_level_detection_is_high() -> None:
    methods = [
        VerificationMethod("unit-a", 1, 0.95, 0.01, 500, "pytest a"),
        VerificationMethod("unit-b", 1, 0.95, 0.01, 500, "pytest b"),
        VerificationMethod("independent", 4, 0.80, 0.20, 2000, "sentinel verify"),
    ]
    req = VerificationRequirement(required_assurance=4, required_detection=0.75)
    plan = VerificationPortfolioOptimizer(methods).plan(req)
    assert "independent" in {m.method_id for m in plan.methods}


def test_optimizer_fails_closed_when_budget_cannot_cover_required_assurance() -> None:
    methods = [VerificationMethod("independent", 4, 0.90, 1.0, 1000, "verify")]
    req = VerificationRequirement(required_assurance=4, required_detection=0.8, max_cost_usd=0.5)
    with pytest.raises(NoAdmissibleVerification):
        VerificationPortfolioOptimizer(methods).plan(req)
