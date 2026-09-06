import pytest

from experiments.runtime_acceleration.phase2_analysis import analyze_phase2_summary


def _protocol():
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "thresholds": {"tool_overhead_reduction_min": 0.30},
        "analysis": {
            "confidence_level": 0.95,
            "effect_interval_method": "paired_percentile_bootstrap",
            "bootstrap_resamples": 500,
            "bootstrap_seed": 130013,
            "promotion_requires_ci_lower_bound": True,
        },
    }


def _run(pair_id, condition, operation, repetition, elapsed, verified=True, sample_kind="warm"):
    return {
        "pair_id": pair_id,
        "condition": condition,
        "operation": operation,
        "sample_kind": sample_kind,
        "repetition": repetition,
        "metrics": {"tool_wall_clock_ms": elapsed},
        "verifier": {"verified": verified},
    }


def _summary():
    runs = []
    for operation in ("bounded_read", "exact_search"):
        cold = f"{operation}-cold-00"
        runs.extend(
            [
                _run(cold, "A", operation, 0, 120.0, sample_kind="cold"),
                _run(cold, "B", operation, 0, 70.0, sample_kind="cold"),
            ]
        )
        for repetition in range(1, 4):
            pair_id = f"{operation}-warm-{repetition:02d}"
            runs.extend(
                [
                    _run(pair_id, "A", operation, repetition, 100.0),
                    _run(pair_id, "B", operation, repetition, 60.0),
                ]
            )
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TOOL_MICROBENCH",
        "execution_id": "phase2-test",
        "state": "COMPLETE",
        "workload_id": "phase2-test-workload",
        "clean_pairs": 8,
        "contaminated_pairs": 0,
        "correctness_failures": 0,
        "runs": runs,
    }


def test_phase2_analysis_uses_only_paired_warm_samples_and_marks_component_pass():
    result = analyze_phase2_summary(_summary(), _protocol())
    assert result["paired_warm_blocks_analyzed"] == 6
    assert result["cold_samples_reported"] == 2
    assert result["overall_warm_effect"]["observed_reduction"] == pytest.approx(0.40)
    assert result["overall_warm_effect"]["ci_low"] == pytest.approx(0.40)
    assert result["g_tr_tool_overhead_component"]["verdict"] == "PASS"
    assert result["promotion_gate_eligible"] is False
    assert result["promotion_gates"]["G-TR"]["verdict"] == "INCONCLUSIVE"


def test_phase2_analysis_is_inconclusive_when_a_warm_pair_is_missing():
    summary = _summary()
    summary["runs"] = [
        run for run in summary["runs"]
        if not (run["pair_id"] == "exact_search-warm-03" and run["condition"] == "B")
    ]
    result = analyze_phase2_summary(summary, _protocol())
    assert result["g_tr_tool_overhead_component"]["verdict"] == "INCONCLUSIVE"
    assert "incomplete_paired_warm_evidence" in result["g_tr_tool_overhead_component"]["reasons"]


def test_phase2_analysis_fails_component_on_correctness_regression():
    summary = _summary()
    summary["correctness_failures"] = 1
    for run in summary["runs"]:
        if run["condition"] == "B" and run["sample_kind"] == "warm":
            run["verifier"]["verified"] = False
            break
    result = analyze_phase2_summary(summary, _protocol())
    assert result["g_tr_tool_overhead_component"]["verdict"] == "FAIL"
    assert "correctness_failure" in result["g_tr_tool_overhead_component"]["reasons"]
