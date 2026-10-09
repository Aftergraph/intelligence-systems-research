from __future__ import annotations

import pytest

from jev_engineering.verification_portfolio import (
    VerificationMethod,
    VerificationPortfolioOptimizer,
    VerificationRequirement,
    VerifierCorrelationMatrix,
)


def _method(name: str, p: float) -> VerificationMethod:
    return VerificationMethod(
        method_id=name,
        assurance_level=2,
        detection_probability=p,
        estimated_cost_usd=0.01,
        estimated_latency_ms=10,
        command=f"verify-{name}",
    )


def test_positive_verifier_correlation_reduces_combined_detection_estimate() -> None:
    a = _method("a", 0.75)
    b = _method("b", 0.70)
    independent = VerificationPortfolioOptimizer([a, b]).combined_detection((a, b))
    assert independent == pytest.approx(0.925)

    matrix = VerifierCorrelationMatrix()
    matrix.set("a", "b", 0.8)
    adjusted = VerificationPortfolioOptimizer([a, b], correlations=matrix).combined_detection((a, b))
    assert 0.75 < adjusted < independent


def test_empirical_correlation_calibration_detects_identical_verifier_outcomes() -> None:
    matrix = VerifierCorrelationMatrix()
    for outcome in [True, False, True, True, False, False]:
        matrix.observe("a", "b", a_detected=outcome, b_detected=outcome)
    assert matrix.get("a", "b") == pytest.approx(1.0)


def test_optimizer_fails_closed_when_correlation_breaks_detection_requirement() -> None:
    a = _method("a", 0.75)
    b = _method("b", 0.70)
    matrix = VerifierCorrelationMatrix()
    matrix.set("a", "b", 1.0)
    optimizer = VerificationPortfolioOptimizer([a, b], correlations=matrix)
    requirement = VerificationRequirement(required_assurance=2, required_detection=0.90)
    with pytest.raises(RuntimeError, match="no verification portfolio"):
        optimizer.plan(requirement)


def test_config_loads_verifier_correlations(tmp_path) -> None:
    from jev_engineering.config import AppConfig

    path = tmp_path / "cfg.yaml"
    path.write_text('''
verification_fabric:
  enabled: true
  requirement:
    required_assurance: 2
    required_detection: 0.80
  correlations:
    - [unit, integration, 0.8]
  methods:
    - id: unit
      assurance_level: 2
      detection_probability: 0.75
      estimated_cost_usd: 0.01
      estimated_latency_ms: 10
      command: pytest unit
    - id: integration
      assurance_level: 2
      detection_probability: 0.70
      estimated_cost_usd: 0.01
      estimated_latency_ms: 10
      command: pytest integration
models: {}
''', encoding="utf-8")
    cfg = AppConfig.load(path)
    optimizer, requirement = cfg.verification_portfolio()
    assert optimizer is not None and requirement is not None
    assert optimizer.correlations is not None
    assert optimizer.correlations.get("unit", "integration") == pytest.approx(0.8)
