from __future__ import annotations

from dataclasses import replace
import random

from .models import MutationReceipt, PolicyGenome


_NUMERIC_FIELDS = (
    "parallelism",
    "retry_ceiling",
    "confidence_threshold",
    "verification_depth",
)


def _receipt(parents, operator_id, seed, parent, child):
    changed = tuple(
        field for field in parent.__dataclass_fields__
        if getattr(parent, field) != getattr(child, field)
    )
    return MutationReceipt(
        parent_ids=tuple(p.identity for p in parents),
        operator_id=operator_id,
        seed=seed,
        changed_fields=changed,
        child_id=child.identity,
    )


def mutate_numeric(parent: PolicyGenome, seed: int) -> tuple[PolicyGenome, MutationReceipt]:
    rng = random.Random(seed)
    field = rng.choice(_NUMERIC_FIELDS)
    direction = -1 if rng.random() < 0.5 else 1
    if field == "confidence_threshold":
        value = min(1.0, max(0.0, parent.confidence_threshold + 0.05 * direction))
        if value == parent.confidence_threshold:
            value = min(1.0, max(0.0, parent.confidence_threshold - 0.05 * direction))
    elif field == "parallelism":
        value = max(1, parent.parallelism + direction)
        if value == parent.parallelism:
            value = parent.parallelism + 1
    elif field == "retry_ceiling":
        value = max(0, parent.retry_ceiling + direction)
        if value == parent.retry_ceiling:
            value = parent.retry_ceiling + 1
    else:
        value = max(1, parent.verification_depth + direction)
        if value == parent.verification_depth:
            value = parent.verification_depth + 1
    child = replace(parent, **{field: value})
    return child, _receipt((parent,), "numeric", seed, parent, child)


def crossover(a: PolicyGenome, b: PolicyGenome, seed: int) -> tuple[PolicyGenome, MutationReceipt]:
    rng = random.Random(seed)
    values = {}
    for field in a.__dataclass_fields__:
        values[field] = getattr(a if rng.random() < 0.5 else b, field)
    child = PolicyGenome(**values)
    receipt = _receipt((a, b), "crossover", seed, a, child)
    return child, receipt


def differential_mutation(
    base: PolicyGenome,
    a: PolicyGenome,
    b: PolicyGenome,
    seed: int,
    factor: float = 0.5,
) -> tuple[PolicyGenome, MutationReceipt]:
    parallelism = max(1, round(base.parallelism + factor * (a.parallelism - b.parallelism)))
    retries = max(0, round(base.retry_ceiling + factor * (a.retry_ceiling - b.retry_ceiling)))
    confidence = min(1.0, max(0.0, base.confidence_threshold + factor * (a.confidence_threshold - b.confidence_threshold)))
    depth = max(1, round(base.verification_depth + factor * (a.verification_depth - b.verification_depth)))
    child = replace(
        base,
        parallelism=parallelism,
        retry_ceiling=retries,
        confidence_threshold=confidence,
        verification_depth=depth,
    )
    return child, _receipt((base, a, b), "differential", seed, base, child)
