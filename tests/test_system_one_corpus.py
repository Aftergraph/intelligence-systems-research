from collections import Counter
import json
from pathlib import Path

from experiments.system_one_acceleration.corpus import build_calibration_corpus


ROOT = Path(__file__).resolve().parents[1]


def test_corpus_has_all_frozen_cases_and_minimum_16_per_decision_type():
    rows = build_calibration_corpus()
    assert len(rows) == 158
    assert len({row.case_id for row in rows}) == 158
    assert Counter(row.decision_type for row in rows) == {
        "route_model": 16,
        "route_tool_family": 16,
        "continue_loop": 16,
        "result_sufficient": 16,
        "needs_human": 46,
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


def test_corpus_includes_every_frozen_critical_risk_case():
    rows = build_calibration_corpus()
    pack = json.loads(
        (ROOT / "data" / "jar_exp_0014_critical_risk_pack_v01.json").read_text(
            encoding="utf-8"
        )
    )
    expected_ids = {f"J14-CAL-{case['case_id']}" for case in pack["cases"]}
    actual = {row.case_id: row for row in rows if row.case_id in expected_ids}

    assert set(actual) == expected_ids
    assert len(actual) == pack["case_count"] == 30
    assert all(row.decision_type == "needs_human" for row in actual.values())
    assert all(row.expected is True and row.critical is True for row in actual.values())
