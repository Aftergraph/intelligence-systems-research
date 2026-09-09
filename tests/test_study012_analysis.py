from experiments.institutional_containment.analyze import (
    primary_comparison,
    summarize_records,
    wilson_interval,
)


def test_wilson_interval_is_bounded():
    lo, hi = wilson_interval(3, 10)
    assert 0.0 <= lo <= hi <= 1.0


def test_analysis_is_outcome_blind_and_does_not_assign_winner():
    records = [
        {
            "condition": "I5",
            "failure_class": "revocation_failure",
            "violation_occurred": True,
            "blocked": False,
            "evidence_detected_violation": True,
        },
        {
            "condition": "I6",
            "failure_class": "revocation_failure",
            "violation_occurred": False,
            "blocked": True,
            "evidence_detected_violation": False,
        },
    ]
    result = primary_comparison(summarize_records(records))
    assert result["comparison"] == "I6_vs_I5"
    assert result["winner"] is None
    assert result["interpretation"].startswith("UNASSIGNED")


def test_primary_comparison_requires_both_conditions():
    summary = summarize_records([
        {
            "condition": "I6",
            "failure_class": "trajectory_tampering",
            "violation_occurred": False,
            "blocked": True,
            "evidence_detected_violation": False,
        }
    ])
    try:
        primary_comparison(summary)
    except ValueError as exc:
        assert "I6 and I5" in str(exc)
    else:
        raise AssertionError("missing I5 was silently accepted")
