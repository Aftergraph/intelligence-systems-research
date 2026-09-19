from experiments.verge.models import PolicyGenome
from experiments.verge_repertoire.contexts import MissionContext
from experiments.verge_repertoire.repertoire import Repertoire, evaluate_in_context
from experiments.verge_halo.halo import (
    DEFAULT_CONFIDENCE_SHOCKS,
    DEFAULT_COST_SHOCKS,
    DEFAULT_LATENCY_SHOCKS,
    make_halo,
    select_halo_robust,
)


def policy(**overrides):
    data = dict(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=2,
        confidence_threshold=0.90,
        verification_depth=3,
        operator_weights=(
            ("numeric", 0.25),
            ("rule", 0.25),
            ("crossover", 0.25),
            ("differential", 0.25),
        ),
    )
    data.update(overrides)
    return PolicyGenome(**data)


def context(
    context_id,
    *,
    split="DEVELOPMENT",
    risk_class=1,
    failure_pressure=0.5,
    latency_pressure=0.5,
    cost_pressure=0.5,
    min_verification=3,
    min_confidence=0.85,
    min_retries=2,
):
    return MissionContext(
        context_id=context_id,
        split=split,
        risk_class=risk_class,
        failure_pressure=failure_pressure,
        latency_pressure=latency_pressure,
        cost_pressure=cost_pressure,
        min_verification=min_verification,
        min_confidence=min_confidence,
        min_retries=min_retries,
        base_cost=1.2,
        base_latency=1.3,
    )


def test_make_halo_is_deterministic_cartesian_and_does_not_mutate_target():
    target = context("TARGET")
    before = target
    halo = make_halo(target)

    assert target == before
    assert len(halo) == (
        len(DEFAULT_CONFIDENCE_SHOCKS)
        * len(DEFAULT_LATENCY_SHOCKS)
        * len(DEFAULT_COST_SHOCKS)
    )
    assert len({point.context_id for point in halo}) == len(halo)
    assert all(point.split == target.split for point in halo)
    assert max(point.min_confidence for point in halo) == 0.89
    assert max(point.latency_pressure for point in halo) == 0.60
    assert max(point.cost_pressure for point in halo) == 0.60


def test_make_halo_clips_bounded_context_fields():
    target = context(
        "CLIP",
        min_confidence=0.99,
        latency_pressure=0.98,
        cost_pressure=0.97,
    )
    halo = make_halo(target)
    assert max(point.min_confidence for point in halo) == 1.0
    assert max(point.latency_pressure for point in halo) == 1.0
    assert max(point.cost_pressure for point in halo) == 1.0


def test_halo_selector_rejects_nominally_feasible_low_margin_elite():
    target = context("TARGET", min_confidence=0.85)
    near_source = context(
        "TRAIN-NEAR",
        split="TRAIN",
        min_confidence=0.80,
    )
    far_source = context(
        "TRAIN-FAR",
        split="TRAIN",
        failure_pressure=0.80,
        latency_pressure=0.30,
        cost_pressure=0.30,
        min_confidence=0.90,
    )

    low_margin = policy(
        confidence_threshold=0.86,
        verification_depth=3,
        retry_ceiling=2,
        parallelism=4,
    )
    robust = policy(
        confidence_threshold=0.96,
        verification_depth=4,
        retry_ceiling=3,
        parallelism=2,
    )

    repertoire = Repertoire()
    assert repertoire.insert(
        near_source,
        low_margin,
        evaluate_in_context(low_margin, near_source),
    )
    assert repertoire.insert(
        far_source,
        robust,
        evaluate_in_context(robust, far_source),
    )

    nominal = repertoire.select(target)
    assert nominal.genome == low_margin
    assert evaluate_in_context(nominal.genome, target).feasible is True

    selected = select_halo_robust(repertoire, target)
    assert selected.entry.genome == robust
    assert selected.worst_utility > -10000
    assert selected.halo_evaluations == 2 * len(make_halo(target))


def test_halo_selector_fails_closed_when_no_elite_survives_halo():
    target = context("TARGET", risk_class=2, min_confidence=0.91, min_verification=4)
    source = context(
        "TRAIN-SOURCE",
        split="TRAIN",
        risk_class=2,
        min_confidence=0.90,
        min_verification=4,
    )
    marginal = policy(
        confidence_threshold=0.92,
        verification_depth=4,
        retry_ceiling=2,
    )

    repertoire = Repertoire()
    assert repertoire.insert(
        source,
        marginal,
        evaluate_in_context(marginal, source),
    )

    import pytest

    with pytest.raises(LookupError, match="no halo-feasible elite"):
        select_halo_robust(repertoire, target)
