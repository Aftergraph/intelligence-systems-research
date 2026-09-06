import pytest

from experiments.runtime_acceleration.phase1_analysis import (
    analyze_phase1_summary,
    render_phase1_report,
)


def _run(pair_id, condition, wall_ms, tool_ms, browser_ms, verified=True):
    return {
        "pair_id": pair_id,
        "condition": condition,
        "verifier": {"verified": verified},
        "metrics": {
            "trace_wall_clock_ms": wall_ms,
            "tool_time_total_ms": tool_ms,
            "browser_time_total_ms": browser_ms,
        },
    }


def _summary():
    runs = []
    for index, scale in enumerate((1.0, 1.1, 0.9, 1.2), start=1):
        pair_id = f"pair-{index:02d}"
        runs.extend(
            [
                _run(pair_id, "A", 100 * scale, 50 * scale, 40 * scale),
                _run(pair_id, "B", 90 * scale, 35 * scale, 40 * scale),
                _run(pair_id, "C", 85 * scale, 50 * scale, 30 * scale),
                _run(pair_id, "D", 80 * scale, 35 * scale, 30 * scale),
            ]
        )
    return {
        "experiment_id": "JAR-EXP-0013",
        "phase": "TRACE_REPLAY",
        "execution_id": "phase1-test",
        "state": "COMPLETE",
        "planned_pairs": 4,
        "clean_pairs": 4,
        "contaminated_pairs": 0,
        "correctness_failures": 0,
        "runs": runs,
    }


def _protocol():
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "analysis": {
            "effect_interval_method": "paired_percentile_bootstrap",
            "bootstrap_resamples": 500,
            "bootstrap_seed": 130013,
            "confidence_level": 0.95,
        },
    }


def test_phase1_analysis_preserves_pairing_and_reports_trace_effects_only():
    result = analyze_phase1_summary(_summary(), _protocol())

    assert result["experiment_id"] == "JAR-EXP-0013"
    assert result["phase"] == "TRACE_REPLAY"
    assert result["paired_blocks_analyzed"] == 4
    assert result["performance_effects_complete"] is True
    assert result["promotion_gate_eligible"] is False
    assert result["promotion_gates"] == {
        "G-TR": {"verdict": "INCONCLUSIVE", "reasons": ["phase1_trace_only"]},
        "G-OB": {"verdict": "INCONCLUSIVE", "reasons": ["phase1_trace_only"]},
        "G-COMB": {"verdict": "INCONCLUSIVE", "reasons": ["phase1_trace_only"]},
    }

    effects = result["effects"]
    assert effects["tool_time_A_vs_B"]["status"] == "ESTIMATED"
    assert effects["tool_time_A_vs_B"]["observed_reduction"] == pytest.approx(0.30)
    assert effects["browser_time_A_vs_C"]["observed_reduction"] == pytest.approx(0.25)
    assert effects["trace_wall_A_vs_D"]["observed_reduction"] == pytest.approx(0.20)
    assert all(effect["method"] == "paired_percentile_bootstrap" for effect in effects.values())


def test_phase1_analysis_reports_verification_rates_without_dropping_pairs():
    summary = _summary()
    summary["runs"][1]["verifier"]["verified"] = False
    summary["correctness_failures"] = 1

    result = analyze_phase1_summary(summary, _protocol())

    assert result["paired_blocks_analyzed"] == 4
    assert result["verification_rate"]["A"] == 1.0
    assert result["verification_rate"]["B"] == pytest.approx(0.75)
    assert result["correctness_failures"] == 1
    assert result["promotion_gate_eligible"] is False


def test_phase1_analysis_retains_diagnostic_report_when_timing_is_missing():
    summary = _summary()
    summary["state"] = "COMPLETE_WITH_CORRECTNESS_FAILURES"
    summary["runs"][1]["metrics"]["tool_time_total_ms"] = None
    summary["runs"][1]["verifier"]["verified"] = False
    summary["correctness_failures"] = 1

    result = analyze_phase1_summary(summary, _protocol())

    assert result["performance_effects_complete"] is False
    assert result["effects"]["tool_time_A_vs_B"] == {
        "status": "INCONCLUSIVE",
        "reason": "invalid_or_missing_metric",
        "control_condition": "A",
        "treatment_condition": "B",
        "metric": "tool_time_total_ms",
        "paired_blocks": 4,
        "confidence_level": 0.95,
        "method": "paired_percentile_bootstrap",
    }
    assert result["promotion_gate_eligible"] is False
    report = render_phase1_report(result)
    assert "tool_time_A_vs_B: INCONCLUSIVE (invalid_or_missing_metric)" in report


def test_phase1_analysis_rejects_incomplete_or_duplicate_pairs():
    summary = _summary()
    summary["runs"] = summary["runs"][:-1]
    with pytest.raises(ValueError, match="A/B/C/D exactly once"):
        analyze_phase1_summary(summary, _protocol())

    summary = _summary()
    summary["runs"].append(dict(summary["runs"][0]))
    with pytest.raises(ValueError, match="A/B/C/D exactly once"):
        analyze_phase1_summary(summary, _protocol())


def test_phase1_report_explicitly_blocks_promotion_claims():
    report = render_phase1_report(analyze_phase1_summary(_summary(), _protocol()))
    assert "Phase-1 Trace Analysis" in report
    assert "Promotion gate eligible: NO" in report
    assert "G-TR: INCONCLUSIVE" in report
    assert "phase1_trace_only" in report
