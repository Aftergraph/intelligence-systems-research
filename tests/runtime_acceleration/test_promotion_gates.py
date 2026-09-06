from pathlib import Path

from experiments.runtime_acceleration.analysis.analyze import evaluate_gates
from experiments.runtime_acceleration.protocol import load_protocol

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = load_protocol(ROOT / "experiments/runtime_acceleration/protocol.yaml")


def passing_results():
    return {
        "mission_attempts_per_condition": {"A": 100, "B": 100, "C": 100, "D": 100},
        "tool_overhead_reduction": 0.31,
        "tool_mission_wall_reduction": 0.11,
        "browser_peak_rss_reduction": 0.41,
        "browser_cold_startup_reduction": 0.21,
        "browser_compatibility": 0.96,
        "combined_mission_wall_reduction": 0.16,
        "metric_confidence_intervals": {
            "tool_overhead_reduction": {"ci_low": 0.305, "ci_high": 0.34},
            "tool_mission_wall_reduction": {"ci_low": 0.105, "ci_high": 0.14},
            "browser_peak_rss_reduction": {"ci_low": 0.405, "ci_high": 0.45},
            "browser_cold_startup_reduction": {"ci_low": 0.205, "ci_high": 0.25},
            "browser_compatibility": {"ci_low": 0.955, "ci_high": 0.99},
            "combined_mission_wall_reduction": {"ci_low": 0.155, "ci_high": 0.20},
        },
        "mission_success_difference_intervals": {
            "B": {"ci_low": -0.04, "ci_high": 0.03},
            "C": {"ci_low": -0.04, "ci_high": 0.03},
            "D": {"ci_low": -0.04, "ci_high": 0.03},
        },
        "new_correctness_failures": 0,
        "safety_regressions": 0,
    }


def test_99_attempts_is_inconclusive_not_pass():
    results = passing_results()
    results["mission_attempts_per_condition"]["D"] = 99
    verdicts = evaluate_gates(results, PROTOCOL)
    assert verdicts["G-COMB"]["verdict"] == "INCONCLUSIVE"


def test_14_percent_combined_speedup_fails_15_percent_threshold():
    results = passing_results()
    results["combined_mission_wall_reduction"] = 0.14
    verdicts = evaluate_gates(results, PROTOCOL)
    assert verdicts["G-COMB"]["verdict"] == "FAIL"


def test_correctness_regression_forces_all_relevant_gates_fail():
    results = passing_results()
    results["new_correctness_failures"] = 1
    verdicts = evaluate_gates(results, PROTOCOL)
    assert {v["verdict"] for v in verdicts.values()} == {"FAIL"}


def test_point_estimate_above_threshold_but_ci_crossing_threshold_is_inconclusive():
    results = passing_results()
    results["metric_confidence_intervals"]["combined_mission_wall_reduction"]["ci_low"] = 0.12
    verdicts = evaluate_gates(results, PROTOCOL)
    assert verdicts["G-COMB"]["verdict"] == "INCONCLUSIVE"
    assert "combined_mission_wall_reduction_ci_below_threshold" in verdicts["G-COMB"]["reasons"]


def test_missing_metric_ci_is_inconclusive_not_pass():
    results = passing_results()
    del results["metric_confidence_intervals"]["tool_overhead_reduction"]
    verdicts = evaluate_gates(results, PROTOCOL)
    assert verdicts["G-TR"]["verdict"] == "INCONCLUSIVE"
    assert "tool_overhead_reduction_ci_missing" in verdicts["G-TR"]["reasons"]


def test_noninferiority_requires_ci_lower_bound_above_negative_margin():
    results = passing_results()
    results["mission_success_difference_intervals"]["B"]["ci_low"] = -0.051
    verdicts = evaluate_gates(results, PROTOCOL)
    assert verdicts["G-TR"]["verdict"] == "INCONCLUSIVE"
    assert "mission_success_noninferiority_ci_not_established" in verdicts["G-TR"]["reasons"]


def test_passing_results_pass_all_gates():
    verdicts = evaluate_gates(passing_results(), PROTOCOL)
    assert {v["verdict"] for v in verdicts.values()} == {"PASS"}
