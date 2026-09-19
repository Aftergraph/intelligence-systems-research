from experiments.verge.models import PolicyGenome
from experiments.verge_repertoire.contexts import (
    MissionContext,
    context_manifest_hash,
    load_contexts,
)
from experiments.verge_repertoire.repertoire import (
    Repertoire,
    evaluate_in_context,
    evolve_repertoire,
)


def policy(**overrides):
    data = dict(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=2,
        confidence_threshold=0.85,
        verification_depth=3,
        operator_weights=(("numeric", 0.25), ("rule", 0.25), ("crossover", 0.25), ("differential", 0.25)),
    )
    data.update(overrides)
    return PolicyGenome(**data)


def test_context_splits_are_disjoint_and_hash_stable():
    contexts = load_contexts()
    train = {c.context_id for c in contexts if c.split == "TRAIN"}
    development = {c.context_id for c in contexts if c.split == "DEVELOPMENT"}
    held_out = {c.context_id for c in contexts if c.split == "HELD_OUT"}
    assert train and development and held_out
    assert train.isdisjoint(development)
    assert train.isdisjoint(held_out)
    assert development.isdisjoint(held_out)
    assert context_manifest_hash(contexts) == context_manifest_hash(load_contexts())


def test_distinct_contexts_favor_distinct_feasible_policies():
    contexts = {c.context_id: c for c in load_contexts()}
    risk = contexts["TRAIN-RISK-1"]
    latency = contexts["TRAIN-LATENCY-1"]

    conservative = policy(
        parallelism=2,
        retry_ceiling=3,
        confidence_threshold=0.95,
        verification_depth=4,
    )
    fast = policy(
        parallelism=4,
        retry_ceiling=1,
        confidence_threshold=0.80,
        verification_depth=2,
    )

    risk_conservative = evaluate_in_context(conservative, risk)
    risk_fast = evaluate_in_context(fast, risk)
    latency_conservative = evaluate_in_context(conservative, latency)
    latency_fast = evaluate_in_context(fast, latency)

    assert risk_conservative.feasible is True
    assert risk_fast.feasible is False
    assert latency_fast.feasible is True
    assert latency_fast.utility > latency_conservative.utility


def test_repertoire_never_inserts_infeasible_policy():
    context = next(c for c in load_contexts() if c.context_id == "TRAIN-RISK-1")
    unsafe = policy(confidence_threshold=0.50, verification_depth=1)
    result = evaluate_in_context(unsafe, context)
    rep = Repertoire()
    assert rep.insert(context, unsafe, result) is False
    assert len(rep) == 0


def test_repertoire_selects_nearest_context_elite():
    contexts = {c.context_id: c for c in load_contexts()}
    rep = Repertoire()

    risk_policy = policy(confidence_threshold=0.95, verification_depth=4, retry_ceiling=3)
    latency_policy = policy(parallelism=4, confidence_threshold=0.80, verification_depth=2, retry_ceiling=1)

    for cid, candidate in (("TRAIN-RISK-1", risk_policy), ("TRAIN-LATENCY-1", latency_policy)):
        context = contexts[cid]
        result = evaluate_in_context(candidate, context)
        assert result.feasible
        assert rep.insert(context, candidate, result)

    selected = rep.select(contexts["DEV-LATENCY-1"])
    assert selected.genome.parallelism == 4
    assert selected.source_context_id == "TRAIN-LATENCY-1"


def test_evolution_is_deterministic_and_never_reads_heldout_for_training():
    contexts = load_contexts()
    a = evolve_repertoire(contexts, seed=17, population_size=8, generations=4)
    b = evolve_repertoire(contexts, seed=17, population_size=8, generations=4)

    assert a == b
    assert a.training_context_ids
    assert all(cid.startswith("TRAIN-") for cid in a.training_context_ids)
    assert not any(cid.startswith("HELD-") for cid in a.training_context_ids)
    assert a.evaluations == 8 * (4 + 1) * len(a.training_context_ids)
    assert len(a.repertoire) > 0


def test_selector_filters_source_elite_that_is_infeasible_in_target_context():
    contexts = {c.context_id: c for c in load_contexts()}
    rep = Repertoire()

    fast = policy(
        parallelism=4,
        retry_ceiling=1,
        confidence_threshold=0.80,
        verification_depth=2,
    )
    safe = policy(
        parallelism=2,
        retry_ceiling=3,
        confidence_threshold=0.95,
        verification_depth=4,
    )
    latency = contexts["TRAIN-LATENCY-1"]
    risk = contexts["TRAIN-RISK-1"]
    assert rep.insert(latency, fast, evaluate_in_context(fast, latency))
    assert rep.insert(risk, safe, evaluate_in_context(safe, risk))

    target = MissionContext(
        context_id="TEST-STRICT-LATENCY",
        split="DEVELOPMENT",
        risk_class=0,
        failure_pressure=0.21,
        latency_pressure=0.99,
        cost_pressure=0.36,
        min_verification=4,
        min_confidence=0.90,
        min_retries=2,
        base_cost=1.1,
        base_latency=1.7,
    )

    selected = rep.select(target)
    assert selected.genome == safe
    assert evaluate_in_context(selected.genome, target).feasible is True


def test_selector_fails_closed_when_no_target_feasible_elite_exists():
    contexts = {c.context_id: c for c in load_contexts()}
    rep = Repertoire()
    fast = policy(
        parallelism=4,
        retry_ceiling=1,
        confidence_threshold=0.80,
        verification_depth=2,
    )
    latency = contexts["TRAIN-LATENCY-1"]
    assert rep.insert(latency, fast, evaluate_in_context(fast, latency))

    target = MissionContext(
        context_id="TEST-STRICT",
        split="DEVELOPMENT",
        risk_class=2,
        failure_pressure=1.0,
        latency_pressure=0.5,
        cost_pressure=0.5,
        min_verification=4,
        min_confidence=0.95,
        min_retries=3,
        base_cost=1.0,
        base_latency=1.0,
    )

    import pytest
    with pytest.raises(LookupError, match="no target-feasible elite"):
        rep.select(target)
