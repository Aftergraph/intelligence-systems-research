import json
from pathlib import Path

import yaml

from experiments.runtime_acceleration.phase2_host_run import main as phase2_host_main
from experiments.runtime_acceleration.phase2_tool_microbench import main as phase2_plan_main


def _protocol():
    return {
        "experiment_id": "JAR-EXP-0013",
        "revision": 3,
        "conditions": {
            "A": {"tool_layer": "stock_hermes"},
            "B": {"tool_layer": "toolrush"},
        },
        "pins": {"toolrush": "4ecd8810fdc9e6e0c64af3d532f876d06f6a278e"},
        "preflight": {
            "cpu_percent_max": 20.0,
            "memory_percent_max": 80.0,
            "require_ac_power": True,
        },
        "confirmatory": {
            "minimum_microbenchmark_warm_repetitions": 2,
            "run_order": "randomized_within_paired_blocks",
        },
        "analysis": {"bootstrap_seed": 130013},
    }


def test_phase2_plan_cli_writes_exclusive_json(tmp_path: Path):
    workload = tmp_path / "workload.yaml"
    protocol = tmp_path / "protocol.yaml"
    output = tmp_path / "plan.json"
    workload.write_text(
        yaml.safe_dump(
            {
                "workload_id": "phase2-cli-test",
                "warm_repetitions": 2,
                "operations": ["bounded_read"],
            }
        ),
        encoding="utf-8",
    )
    protocol.write_text(yaml.safe_dump(_protocol()), encoding="utf-8")

    assert phase2_plan_main(
        ["--workload", str(workload), "--protocol", str(protocol), "--output", str(output)]
    ) == 0
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["phase"] == "TOOL_MICROBENCH"
    assert plan["planned_runs"] == 6


def test_phase2_host_cli_loads_inputs_and_returns_nonzero_for_nonclean_summary(tmp_path: Path):
    config_path = tmp_path / "config.json"
    plan_path = tmp_path / "plan.json"
    probe_path = tmp_path / "probe.json"
    protocol_path = tmp_path / "protocol.yaml"
    for path, payload in (
        (config_path, {"experiment_id": "JAR-EXP-0013", "workspace": str(tmp_path / "workspace")}),
        (plan_path, {"experiment_id": "JAR-EXP-0013", "phase": "TOOL_MICROBENCH"}),
        (probe_path, {"experiment_id": "JAR-EXP-0013", "state": "READY"}),
    ):
        path.write_text(json.dumps(payload), encoding="utf-8")
    protocol_path.write_text(yaml.safe_dump(_protocol()), encoding="utf-8")

    seen = {}

    def fake_runner(config, plan, probe, protocol, *, evidence_root, execution_id):
        seen.update(
            config=config,
            plan=plan,
            probe=probe,
            protocol=protocol,
            evidence_root=Path(evidence_root),
            execution_id=execution_id,
        )
        return {"state": "COMPLETE_WITH_EXCLUSIONS", "phase": "TOOL_MICROBENCH"}

    code = phase2_host_main(
        [
            "--config", str(config_path),
            "--plan", str(plan_path),
            "--probe", str(probe_path),
            "--protocol", str(protocol_path),
            "--evidence-root", str(tmp_path / "evidence"),
            "--execution-id", "phase2-cli-run",
        ],
        runner=fake_runner,
    )
    assert code == 2
    assert seen["execution_id"] == "phase2-cli-run"
    assert seen["protocol"]["experiment_id"] == "JAR-EXP-0013"
