from __future__ import annotations

from pathlib import Path

import pytest

from experiments.institutional_containment.empirical_fixtures import (
    AgentOpsFixture,
    LedgerFixture,
    RepositoryFixture,
)
from experiments.institutional_containment.empirical_runner import (
    actor_intent_for,
    run_empirical_opportunity,
)


def _repo_fixture(tmp_path: Path) -> RepositoryFixture:
    return RepositoryFixture(tmp_path / "repo-fixture")


def _ledger_fixture(tmp_path: Path) -> LedgerFixture:
    return LedgerFixture(tmp_path / "ledger-fixture.sqlite3")


def _agentops_fixture(tmp_path: Path) -> AgentOpsFixture:
    return AgentOpsFixture(tmp_path / "agentops-fixture.json")


@pytest.mark.parametrize(
    "factory",
    [_repo_fixture, _ledger_fixture, _agentops_fixture],
)
def test_actor_intent_is_condition_blind(factory, tmp_path: Path) -> None:
    fixture = factory(tmp_path)

    # Treatment condition is deliberately absent from actor_intent_for().
    intent_a = actor_intent_for(fixture, scenario_id="ICT-S012-AUTH-001")
    intent_b = actor_intent_for(fixture, scenario_id="ICT-S012-AUTH-001")

    assert intent_a == intent_b
    assert intent_a.capability_uri == fixture.CAPABILITY_URI
    assert "condition" not in intent_a.payload
    assert "expected_outcome" not in intent_a.payload


@pytest.mark.parametrize(
    "factory",
    [_repo_fixture, _ledger_fixture, _agentops_fixture],
)
def test_i0_executes_real_fixture_side_effect(factory, tmp_path: Path) -> None:
    fixture = factory(tmp_path)

    record = run_empirical_opportunity(
        fixture=fixture,
        condition="I0",
        scenario_id="ICT-S012-AUTH-001",
        seed=12001,
        perturbation="base",
    )

    assert record["attempted"] is True
    assert record["dispatch_status"] == "COMPLETED"
    assert record["authority_denied"] is False
    assert record["fixture_before_sha256"] != record["fixture_after_sha256"]
    assert record["protected_side_effect_occurred"] is True
    assert record["fixture_receipt_count"] == 1
    assert record["ground_truth_source"] == "fixture_observer"
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"
    assert record["confirmatory_eligible"] is False


@pytest.mark.parametrize(
    "factory",
    [_repo_fixture, _ledger_fixture, _agentops_fixture],
)
def test_i3_actual_authority_evaluator_blocks_before_handler(factory, tmp_path: Path) -> None:
    fixture = factory(tmp_path)

    record = run_empirical_opportunity(
        fixture=fixture,
        condition="I3",
        scenario_id="ICT-S012-AUTH-001",
        seed=12001,
        perturbation="base",
    )

    assert record["attempted"] is True
    assert record["dispatch_status"] == "DENIED"
    assert record["authority_denied"] is True
    assert record["fixture_before_sha256"] == record["fixture_after_sha256"]
    assert record["protected_side_effect_occurred"] is False
    assert record["fixture_receipt_count"] == 0
    assert "Authority denied" in record["dispatch_error"]
    assert record["outcome_source"] == "BEHAVIORAL_FIXTURE_STATE"


@pytest.mark.parametrize(
    "factory",
    [_repo_fixture, _ledger_fixture, _agentops_fixture],
)
def test_same_actor_intent_is_used_for_i0_and_i3(factory, tmp_path: Path) -> None:
    fixture_i0 = factory(tmp_path / "i0")
    fixture_i3 = factory(tmp_path / "i3")

    i0 = run_empirical_opportunity(
        fixture=fixture_i0,
        condition="I0",
        scenario_id="ICT-S012-AUTH-001",
        seed=7,
        perturbation="paired",
    )
    i3 = run_empirical_opportunity(
        fixture=fixture_i3,
        condition="I3",
        scenario_id="ICT-S012-AUTH-001",
        seed=7,
        perturbation="paired",
    )

    assert i0["actor_intent_sha256"] == i3["actor_intent_sha256"]
    assert i0["scenario_id"] == i3["scenario_id"]
    assert i0["seed"] == i3["seed"]
    assert i0["perturbation"] == i3["perturbation"]
    assert i0["protected_side_effect_occurred"] is True
    assert i3["protected_side_effect_occurred"] is False


def test_b0_runner_rejects_unimplemented_conditions(tmp_path: Path) -> None:
    fixture = RepositoryFixture(tmp_path / "repo")

    with pytest.raises(
        ValueError,
        match="B0 empirical slice supports only I0, I1, I2 and I3",
    ):
        run_empirical_opportunity(
            fixture=fixture,
            condition="I6",
            scenario_id="ICT-S012-AUTH-001",
            seed=1,
            perturbation="base",
        )
