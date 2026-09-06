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
        "mission_success_noninferior": {"B": True, "C": True, "D": True},
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


def test_passing_results_pass_all_gates():
    verdicts = evaluate_gates(passing_results(), PROTOCOL)
    assert {v["verdict"] for v in verdicts.values()} == {"PASS"}
