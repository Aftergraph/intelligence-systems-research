from experiments.runtime_acceleration.host_preflight import check_preflight


def test_preflight_marks_busy_cpu_as_contaminated():
    verdict = check_preflight(
        {"cpu_percent": 80, "memory_percent": 20, "on_ac_power": True},
        {"cpu_percent_max": 25, "memory_percent_max": 85, "require_ac_power": True},
    )
    assert verdict["clean"] is False
    assert "cpu_percent" in verdict["reasons"]


def test_preflight_marks_missing_ac_power_when_required():
    verdict = check_preflight(
        {"cpu_percent": 10, "memory_percent": 20, "on_ac_power": False},
        {"cpu_percent_max": 25, "memory_percent_max": 85, "require_ac_power": True},
    )
    assert verdict["clean"] is False
    assert "on_ac_power" in verdict["reasons"]


def test_preflight_accepts_clean_snapshot():
    verdict = check_preflight(
        {"cpu_percent": 10, "memory_percent": 40, "on_ac_power": True},
        {"cpu_percent_max": 25, "memory_percent_max": 85, "require_ac_power": True},
    )
    assert verdict == {"clean": True, "reasons": []}
