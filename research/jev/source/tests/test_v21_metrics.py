from jev_engineering.live_metrics import MissionMeasurement, paired_frontier_efficiency_ratio, summarize_measurements


def test_metrics_distinguish_verified_success_and_false_completion():
    rows = [
        MissionMeasurement("m1", "frontier", True, True, 1.0, 10, 900, 100),
        MissionMeasurement("m2", "frontier", True, False, 1.0, 20, 900, 100),
        MissionMeasurement("m1", "jev", True, True, 0.4, 8, 90, 10),
        MissionMeasurement("m2", "jev", False, True, 0.4, 9, 90, 10),
    ]
    a = summarize_measurements(rows, condition="frontier")
    b = summarize_measurements(rows, condition="jev")
    assert a.vsr == 0.5 and a.fcr == 0.5 and a.cpvo_usd == 2.0
    assert b.vsr == 1.0 and b.fcr == 0.0 and b.cpvo_usd == 0.4
    assert paired_frontier_efficiency_ratio(a, b) == 20.0
