from experiments.verge.models import PolicyGenome
from experiments.verge_headroom.contexts import load_contexts
from experiments.verge_headroom.ranking import (
    headroom_components,
    normalized_min_headroom,
    select_headroom_best,
    select_nominal_best,
)
from experiments.verge_repertoire.repertoire import evaluate_in_context


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


def test_headroom_components_match_frozen_definition():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-HDR-BAL-A")
    genome = policy(
        confidence_threshold=0.93,
        verification_depth=4,
        retry_ceiling=3,
    )
    confidence, verification, retry = headroom_components(genome, context)
    assert round(confidence, 6) == round(0.93 - context.min_confidence, 6)
    assert verification == 4 - context.min_verification
    assert retry == 3 - context.min_retries


def test_normalized_min_headroom_uses_0_10_2_2_scaling():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-HDR-BAL-A")
    genome = policy(
        confidence_threshold=context.min_confidence + 0.05,
        verification_depth=context.min_verification + 2,
        retry_ceiling=context.min_retries + 2,
    )
    assert normalized_min_headroom(genome, context) == 0.5


def test_headroom_ranking_can_choose_safer_margin_over_higher_nominal_utility():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-HDR-BAL-A")
    nominal = policy(
        confidence_threshold=context.min_confidence + 0.01,
        verification_depth=context.min_verification,
        retry_ceiling=context.min_retries,
        parallelism=4,
    )
    headroom = policy(
        confidence_threshold=context.min_confidence + 0.08,
        verification_depth=context.min_verification + 1,
        retry_ceiling=context.min_retries + 1,
        parallelism=2,
    )
    nout = evaluate_in_context(nominal, context)
    hout = evaluate_in_context(headroom, context)
    assert nout.feasible and hout.feasible
    assert nout.utility > hout.utility

    rows = [
        (nominal, nout),
        (headroom, hout),
    ]
    assert select_nominal_best(rows, context).genome == nominal
    assert select_headroom_best(rows, context).genome == headroom


def test_headroom_selector_rejects_infeasible_candidates():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-HDR-RISK-A")
    unsafe = policy(
        confidence_threshold=0.50,
        verification_depth=1,
        retry_ceiling=0,
    )
    safe = policy(
        confidence_threshold=0.97,
        verification_depth=4,
        retry_ceiling=3,
    )
    rows = [
        (unsafe, evaluate_in_context(unsafe, context)),
        (safe, evaluate_in_context(safe, context)),
    ]
    assert select_headroom_best(rows, context).genome == safe
