from experiments.runtime_acceleration.environment import capture_environment


def test_environment_capture_has_reproducibility_fields():
    env = capture_environment()
    for key in ["os", "os_release", "python", "cpu_logical_count", "timestamp_utc"]:
        assert key in env
    assert env["cpu_logical_count"] >= 1
    assert env["timestamp_utc"].endswith("Z")
