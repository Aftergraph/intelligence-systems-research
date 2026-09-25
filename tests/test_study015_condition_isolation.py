import pytest

from experiments.study015.condition_isolation import (
    ConditionIsolationError,
    assert_matched_pair,
    assert_mechanism_isolation,
    expected_mechanisms,
)


def test_exact_profile_passes():
    assert_mechanism_isolation(
        condition="S3",
        observed_enabled=set(expected_mechanisms("S3")),
    )


def test_leaked_mechanism_fails():
    observed = set(expected_mechanisms("S3"))
    observed.add("governed_recovery")
    with pytest.raises(ConditionIsolationError, match="leaked"):
        assert_mechanism_isolation(condition="S3", observed_enabled=observed)


def test_full_minus_removes_exactly_one_named_mechanism():
    full = expected_mechanisms("FULL")
    reduced = expected_mechanisms("FULL_MINUS", "independent_verification")
    assert len(full - reduced) == 1
    assert "independent_verification" not in reduced


def test_matched_inputs_ignore_condition_but_not_budget_or_prompt():
    base = {
        "provider":"p","model":"m","workload_id":"w","replicate_id":1,
        "budget_hash":"b","acceptance_hash":"a","prompt_hash":"p1",
    }
    assert_matched_pair(dict(base, condition="S2"), dict(base, condition="S3"))
    changed = dict(base, budget_hash="different")
    with pytest.raises(ConditionIsolationError, match="matched inputs"):
        assert_matched_pair(base, changed)
