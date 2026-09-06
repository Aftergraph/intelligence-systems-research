from pathlib import Path

from experiments.runtime_acceleration.protocol import load_protocol

ROOT = Path(__file__).resolve().parents[2]


def test_protocol_freezes_conditions_thresholds_and_source_pins():
    protocol = load_protocol(ROOT / "experiments/runtime_acceleration/protocol.yaml")
    assert list(protocol["conditions"]) == ["A", "B", "C", "D"]
    assert protocol["thresholds"]["tool_overhead_reduction_min"] == 0.30
    assert protocol["thresholds"]["combined_mission_wall_reduction_min"] == 0.15
    assert protocol["thresholds"]["mission_success_noninferiority_margin"] == 0.05
    assert protocol["confirmatory"]["minimum_mission_attempts_per_condition"] == 100
    assert protocol["pins"]["toolrush"] == "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"
    assert protocol["pins"]["obscura"] == "a1e09de68c7617b8079fbb1661b0548c501971c1"


def test_protocol_freezes_controlled_host_preflight_before_live_data():
    protocol = load_protocol(ROOT / "experiments/runtime_acceleration/protocol.yaml")
    assert protocol["revision"] == 3
    assert protocol["preflight"] == {
        "cpu_percent_max": 20.0,
        "memory_percent_max": 80.0,
        "require_ac_power": True,
    }


def test_protocol_r3_freezes_statistical_promotion_rules_before_live_data():
    protocol = load_protocol(ROOT / "experiments/runtime_acceleration/protocol.yaml")
    assert protocol["analysis"] == {
        "confidence_level": 0.95,
        "effect_interval_method": "paired_percentile_bootstrap",
        "bootstrap_resamples": 10000,
        "bootstrap_seed": 130013,
        "mission_success_interval_method": "newcombe_wilson",
        "promotion_requires_ci_lower_bound": True,
    }
    assert protocol["promotion_gates"]["G-TR"]["requires"]["mission_success_noninferiority_margin"] == 0.05


def test_protocol_rejects_wrong_experiment_id(tmp_path):
    bad = tmp_path / "protocol.yaml"
    bad.write_text("experiment_id: WRONG\n", encoding="utf-8")
    try:
        load_protocol(bad)
    except ValueError as exc:
        assert "unexpected experiment_id" in str(exc)
    else:
        raise AssertionError("wrong experiment id must be rejected")
