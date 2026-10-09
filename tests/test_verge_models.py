from dataclasses import FrozenInstanceError

import pytest

from experiments.verge.models import (
    EvaluationReceipt,
    MutationReceipt,
    PolicyGenome,
    stable_hash,
)


def sample_genome(**overrides):
    data = dict(
        routing_policy=("debug", "verify"),
        parallelism=2,
        retry_ceiling=1,
        confidence_threshold=0.8,
        verification_depth=2,
        operator_weights=(("numeric", 0.5), ("rule", 0.5)),
    )
    data.update(overrides)
    return PolicyGenome(**data)


def test_stable_hash_is_order_independent_for_mappings():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert stable_hash(left) == stable_hash(right)


def test_policy_genome_hash_changes_when_mutable_policy_changes():
    g1 = sample_genome()
    g2 = sample_genome(retry_ceiling=2)
    assert g1.identity != g2.identity


def test_policy_genome_is_frozen_and_has_no_authority_field():
    genome = sample_genome()
    assert "authority" not in genome.__dataclass_fields__
    with pytest.raises(FrozenInstanceError):
        genome.retry_ceiling = 9


def test_mutation_receipt_binds_parent_operator_seed_and_child():
    parent = sample_genome()
    child = sample_genome(parallelism=3)
    receipt = MutationReceipt(
        parent_ids=(parent.identity,),
        operator_id="numeric",
        seed=42,
        changed_fields=("parallelism",),
        child_id=child.identity,
    )
    assert receipt.identity == stable_hash(receipt.payload())


def test_evaluation_receipt_hash_changes_with_verifier_result():
    base = dict(
        candidate_id=sample_genome().identity,
        benchmark_case="case-1",
        seed=7,
        environment="offline",
        mission_complete=True,
        evidence_admitted=True,
        unauthorized_actions=0,
        evidence_integrity_failures=0,
        cost=1.5,
        latency=2.0,
        human_interventions=0,
        recovery_success=True,
    )
    passed = EvaluationReceipt(verifier_pass=True, **base)
    failed = EvaluationReceipt(verifier_pass=False, **base)
    assert passed.identity != failed.identity
