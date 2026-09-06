from collections import Counter

from experiments.runtime_acceleration.runners.factorial import build_counterbalanced_schedule


def test_schedule_is_seeded_and_balanced():
    missions = ["m1", "m2", "m3"]
    conditions = ["A", "B", "C", "D"]
    a = build_counterbalanced_schedule(missions, conditions, 130013)
    b = build_counterbalanced_schedule(missions, conditions, 130013)
    assert a == b
    assert len(a) == 12
    counts = Counter(item["condition"] for item in a)
    assert counts == Counter({"A": 3, "B": 3, "C": 3, "D": 3})
    for mission in missions:
        assert {x["condition"] for x in a if x["mission"] == mission} == set(conditions)
