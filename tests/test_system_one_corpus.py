from collections import Counter

from experiments.system_one_acceleration.corpus import build_calibration_corpus


def test_corpus_has_128_unique_cases_and_16_per_decision_type():
    rows = build_calibration_corpus()
    assert len(rows) == 128
    assert len({row.case_id for row in rows}) == 128
    assert Counter(row.decision_type for row in rows) == {
        "route_model": 16,
        "route_tool_family": 16,
        "continue_loop": 16,
        "result_sufficient": 16,
        "needs_human": 16,
        "risk_level": 16,
        "retryable_failure": 16,
        "evidence_conflict": 16,
    }


def test_corpus_contains_both_binary_labels_for_every_noul_contract():
    rows = build_calibration_corpus()
    for decision_type in (
        "continue_loop",
        "result_sufficient",
        "needs_human",
        "retryable_failure",
        "evidence_conflict",
    ):
        labels = {row.expected for row in rows if row.decision_type == decision_type}
        assert labels == {True, False}


def test_corpus_contains_all_route_and_risk_classes():
    rows = build_calibration_corpus()
    assert {row.expected for row in rows if row.decision_type == "route_model"} == {
        "fast", "powerful", "escalate"
    }
    assert {row.expected for row in rows if row.decision_type == "route_tool_family"} == {
        "search", "filesystem", "browser", "code_execution", "none"
    }
    assert {row.expected for row in rows if row.decision_type == "risk_level"} == {
        0, 1, 2, 3
    }


def test_critical_cases_exist_and_are_label_frozen():
    rows = build_calibration_corpus()
    critical = [row for row in rows if row.critical]
    assert len(critical) >= 16
    assert all(row.expected is not None for row in critical)
