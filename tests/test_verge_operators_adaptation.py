import math

from experiments.verge.adaptation import ProbabilityMatcher
from experiments.verge.islands import IslandMember, IslandState, migrate_elites
from experiments.verge.models import PolicyGenome
from experiments.verge.operators import crossover, differential_mutation, mutate_numeric


def genome(**overrides):
    data = dict(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=2,
        confidence_threshold=0.75,
        verification_depth=2,
        operator_weights=(("numeric", 0.5), ("rule", 0.5)),
    )
    data.update(overrides)
    return PolicyGenome(**data)


def test_numeric_mutation_is_seed_deterministic_and_lineage_bound():
    parent = genome()
    child1, receipt1 = mutate_numeric(parent, seed=41)
    child2, receipt2 = mutate_numeric(parent, seed=41)
    assert child1 == child2
    assert receipt1 == receipt2
    assert receipt1.parent_ids == (parent.identity,)
    assert receipt1.child_id == child1.identity
    assert child1.identity != parent.identity


def test_crossover_binds_both_parent_ids():
    a = genome(parallelism=1)
    b = genome(parallelism=4, retry_ceiling=5)
    child, receipt = crossover(a, b, seed=3)
    assert set(receipt.parent_ids) == {a.identity, b.identity}
    assert receipt.child_id == child.identity


def test_differential_mutation_changes_numeric_subspace_only():
    base = genome()
    a = genome(parallelism=4, confidence_threshold=0.9)
    b = genome(parallelism=1, confidence_threshold=0.5)
    child, receipt = differential_mutation(base, a, b, seed=9, factor=0.5)
    assert child.routing_policy == base.routing_policy
    assert child.operator_weights == base.operator_weights
    assert receipt.operator_id == "differential"


def test_probability_matcher_stays_normalized_and_rewards_improvement():
    matcher = ProbabilityMatcher(("numeric", "rule"), minimum=0.05)
    before = matcher.probabilities()
    matcher.update("numeric", improvement=2.0, feasible=True)
    after = matcher.probabilities()
    assert math.isclose(sum(after.values()), 1.0)
    assert after["numeric"] > before["numeric"]


def test_probability_matcher_does_not_reward_infeasible_offspring():
    matcher = ProbabilityMatcher(("numeric", "rule"), minimum=0.05)
    before = matcher.probabilities()
    matcher.update("numeric", improvement=10.0, feasible=False)
    assert matcher.probabilities() == before


def test_island_migration_preserves_origin_lineage():
    islands = [
        IslandState("safe", (IslandMember("a", "safe"),)),
        IslandState("explore", (IslandMember("b", "explore"),)),
        IslandState("cheap", (IslandMember("c", "cheap"),)),
    ]
    migrated = migrate_elites(islands)
    explore_ids = {(m.candidate_id, m.origin_island) for m in migrated[1].members}
    assert ("a", "safe") in explore_ids
