from __future__ import annotations

from jev_engineering.evidence_campaign import (
    ContinuousRegressionMonitor,
    RegressionPolicy,
    plan_noninferiority_pairs,
)
from jev_engineering.learning_campaign import OutcomeSample


def test_power_plan_is_conservative_and_increases_for_tighter_margin():
    broad = plan_noninferiority_pairs(baseline_vsr=0.90, margin=0.05, alpha=0.05, power=0.80)
    tight = plan_noninferiority_pairs(baseline_vsr=0.90, margin=0.02, alpha=0.05, power=0.80)
    assert broad["recommended_pairs"] > 0
    assert tight["recommended_pairs"] > broad["recommended_pairs"]
    assert broad["method"] == "conservative-independent-proportions-approximation"


def test_post_promotion_monitor_quarantines_on_window_regression():
    monitor = ContinuousRegressionMonitor(
        RegressionPolicy(window_size=4, min_vsr=0.75, max_fcr=0.0, max_cpvo_usd=1.0)
    )
    for _ in range(3):
        verdict = monitor.observe(OutcomeSample(True, False, 0.2))
        assert verdict["quarantine"] is False
    verdict = monitor.observe(OutcomeSample(False, True, 0.2))
    assert verdict["quarantine"] is True
    assert "fcr" in " ".join(verdict["reasons"]).lower()
