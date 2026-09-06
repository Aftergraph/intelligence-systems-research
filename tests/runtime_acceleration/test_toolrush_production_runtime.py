from experiments.runtime_acceleration.toolrush_production_runtime import decide_runtime, toolrush_env


def test_auto_selects_toolrush_when_promoted_and_healthy():
    d = decide_runtime(promoted=True, doctor_ok=True, hashes_ok=True, disabled=False)
    assert d == {"runtime":"toolrush","fallback":False,"reason":"promoted_healthy"}


def test_auto_falls_back_stock_when_doctor_fails():
    d = decide_runtime(promoted=True, doctor_ok=False, hashes_ok=True, disabled=False)
    assert d == {"runtime":"stock","fallback":True,"reason":"doctor_failed"}


def test_kill_switch_forces_stock():
    d = decide_runtime(promoted=True, doctor_ok=True, hashes_ok=True, disabled=True)
    assert d == {"runtime":"stock","fallback":True,"reason":"kill_switch"}


def test_hash_mismatch_forces_stock():
    d = decide_runtime(promoted=True, doctor_ok=True, hashes_ok=False, disabled=False)
    assert d == {"runtime":"stock","fallback":True,"reason":"integrity_mismatch"}


def test_toolrush_env_enables_all_promoted_lanes():
    assert toolrush_env() == {"TOOLRUSH_FASTLANE":"1","TOOLRUSH_SEARCH":"1","TOOLRUSH_PERSIST":"1"}
