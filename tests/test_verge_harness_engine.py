import math

import pytest

from experiments.verge.benchmarks import ackley, rastrigin, rosenbrock, sphere
from experiments.verge.engine import evolve
from experiments.verge.harness import (
    benchmark_manifest_hash,
    evaluate_policy,
    load_cases,
)
from experiments.verge.models import PolicyGenome


def test_classical_benchmarks_have_known_optima():
    assert sphere((0.0, 0.0)) == 0.0
    assert rastrigin((0.0, 0.0)) == 0.0
    assert rosenbrock((1.0, 1.0)) == 0.0
    assert math.isclose(ackley((0.0, 0.0)), 0.0, abs_tol=1e-12)


def test_case_manifest_hash_is_stable():
    cases = load_cases()
    assert benchmark_manifest_hash(cases) == benchmark_manifest_hash(load_cases())


def test_policy_evaluation_is_evidence_gated_and_deterministic():
    cases = load_cases()
    genome = PolicyGenome(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=2,
        confidence_threshold=0.90,
        verification_depth=4,
        operator_weights=(("numeric", 0.5), ("rule", 0.5)),
    )
    first = evaluate_policy(genome, cases, seed=11)
    second = evaluate_policy(genome, cases, seed=11)
    assert first == second
    assert first.feasible is True
    assert first.objectives.unauthorized_actions == 0


def test_evolve_is_reproducible_and_respects_budget():
    cases = load_cases()
    a = evolve(cases, seed=123, population_size=10, generations=6)
    b = evolve(cases, seed=123, population_size=10, generations=6)
    assert a.best.genome.identity == b.best.genome.identity
    assert a.best.outcome == b.best.outcome
    assert a.evaluations == b.evaluations == 70


def test_evolve_improves_or_matches_initial_verified_quality():
    cases = load_cases()
    result = evolve(cases, seed=7, population_size=12, generations=8)
    assert result.best_quality >= result.initial_best_quality
    assert result.archive_size > 0


def test_manifest_mismatch_is_rejected():
    cases = load_cases()
    with pytest.raises(ValueError, match="benchmark manifest hash mismatch"):
        evolve(cases, seed=1, population_size=4, generations=1, expected_manifest_hash="deadbeef")

