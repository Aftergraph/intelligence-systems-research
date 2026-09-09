from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from experiments.institutional_containment.empirical_matrix import (
    B1_CONDITIONS,
    run_paired_empirical_matrix,
)
from experiments.institutional_containment.empirical_runner import actor_intent_for


@pytest.mark.parametrize("fixture_kind", ["repository", "ledger", "agentops"])
def test_each_pair_contains_exactly_i0_and_i3_with_identical_actor_intent(tmp_path: Path, fixture_kind: str) -> None:
    records = run_paired_empirical_matrix(
        root=tmp_path,
        replicate_id="r001",
        seed=17,
        perturbation="nominal",
        fixture_kinds=(fixture_kind,),
    )

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record["pair_id"])].append(record)

    assert grouped
    for pair_records in grouped.values():
        assert {record["condition"] for record in pair_records} == set(B1_CONDITIONS)
        assert len(pair_records) == 2
        assert len({record["actor_intent_sha256"] for record in pair_records}) == 1
        assert len({record["fixture_initial_sha256"] for record in pair_records}) == 1


def test_condition_order_is_randomized_but_reproducible(tmp_path: Path) -> None:
    first = run_paired_empirical_matrix(
        root=tmp_path / "a",
        replicate_id="r001",
        seed=101,
        perturbation="nominal",
    )
    second = run_paired_empirical_matrix(
        root=tmp_path / "b",
        replicate_id="r001",
        seed=101,
        perturbation="nominal",
    )

    first_order = [(record["pair_id"], record["condition_order_index"], record["condition"]) for record in first]
    second_order = [(record["pair_id"], record["condition_order_index"], record["condition"]) for record in second]
    assert first_order == second_order

    orders_by_pair: dict[str, tuple[str, ...]] = {}
    for record in first:
        pair_id = str(record["pair_id"])
        orders_by_pair.setdefault(pair_id, tuple())
    for pair_id in list(orders_by_pair):
        ordered = sorted(
            (record for record in first if record["pair_id"] == pair_id),
            key=lambda record: int(record["condition_order_index"]),
        )
        orders_by_pair[pair_id] = tuple(str(record["condition"]) for record in ordered)

    assert set(orders_by_pair.values()).issubset({("I0", "I3"), ("I3", "I0")})
    assert len(set(orders_by_pair.values())) == 2


def test_each_condition_uses_fresh_fixture_instance_and_no_cross_condition_receipts(tmp_path: Path) -> None:
    records = run_paired_empirical_matrix(
        root=tmp_path,
        replicate_id="r002",
        seed=23,
        perturbation="nominal",
        fixture_kinds=("repository",),
    )

    assert len(records) == 2
    i0 = next(record for record in records if record["condition"] == "I0")
    i3 = next(record for record in records if record["condition"] == "I3")

    assert i0["fixture_instance_id"] != i3["fixture_instance_id"]
    assert i0["fixture_receipt_count"] == 1
    assert i3["fixture_receipt_count"] == 0
    assert i0["protected_side_effect_occurred"] is True
    assert i3["protected_side_effect_occurred"] is False


def test_pair_id_is_immutable_and_bound_to_replicate_seed_fixture_and_scenario(tmp_path: Path) -> None:
    records = run_paired_empirical_matrix(
        root=tmp_path,
        replicate_id="r003",
        seed=31,
        perturbation="nominal",
    )

    for record in records:
        expected = (
            f"STUDY-012B:{record['replicate_id']}:{record['seed']}:"
            f"{record['fixture_kind']}:{record['scenario_id']}"
        )
        assert record["pair_id"] == expected


def test_matrix_records_are_validation_only_and_never_confirmatory(tmp_path: Path) -> None:
    records = run_paired_empirical_matrix(
        root=tmp_path,
        replicate_id="r004",
        seed=41,
        perturbation="nominal",
    )

    assert records
    assert all(record["evidence_scope"] == "HARNESS_VALIDATION_ONLY" for record in records)
    assert all(record["confirmatory_eligible"] is False for record in records)
    assert all(record["fallback_used"] is False for record in records)


def test_invalid_replicate_id_fails_closed_before_execution(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="replicate_id"):
        run_paired_empirical_matrix(
            root=tmp_path,
            replicate_id="../escape",
            seed=1,
            perturbation="nominal",
        )
