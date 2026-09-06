from __future__ import annotations

import json
from pathlib import Path
import tempfile
from urllib.request import urlopen

from experiments.runtime_acceleration.analysis.analyze import evaluate_gates
from experiments.runtime_acceleration.evidence import write_run_evidence
from experiments.runtime_acceleration.fixture_server import fixture_server
from experiments.runtime_acceleration.protocol import load_protocol
from experiments.runtime_acceleration.runners.trace_replay import replay_trace

NEGATIVE_CONTROLS = (
    "toolrush_native_read_disabled",
    "toolrush_direct_search_disabled",
    "parallel_reads_serialized",
    "unsafe_scheduler_admission_restored",
    "obscura_dom_mismatch",
    "unsupported_feature_error_suppressed",
)


class _DryAdapter:
    def execute(self, operation: str, payload: dict) -> dict:
        return {"operation": operation, "payload": payload}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_dry_run(root: Path) -> dict:
    """Exercise the offline harness without provider spend or production mutation."""
    repo = _repo_root()
    protocol = load_protocol(repo / "experiments/runtime_acceleration/protocol.yaml")
    pins = json.loads((repo / "data/runtime_acceleration/manifests/source_pins.json").read_text(encoding="utf-8"))
    if pins.get("experiment_id") != "JAR-EXP-0013":
        raise ValueError("source pin manifest experiment mismatch")
    if pins["sources"]["toolrush"]["commit"] != protocol["pins"]["toolrush"]:
        raise ValueError("ToolRush source pin drift")
    if pins["sources"]["obscura"]["commit"] != protocol["pins"]["obscura"]:
        raise ValueError("Obscura source pin drift")

    with fixture_server() as base_url:
        body = urlopen(base_url + "/static", timeout=2).read().decode("utf-8")
        if "deterministic-marker" not in body:
            raise AssertionError("fixture server marker missing")

    trace_result = replay_trace(
        [
            {"operation": "read", "payload": {"path": "fixture/source.py"}},
            {"operation": "search", "payload": {"query": "marker"}},
        ],
        _DryAdapter(),
    )
    if [item["operation"] for item in trace_result] != ["read", "search"]:
        raise AssertionError("trace replay order mismatch")

    evidence_dir = Path(root) / "evidence"
    write_run_evidence(
        evidence_dir,
        "dry-run-contract",
        {
            "metadata": {"experiment_id": "JAR-EXP-0013", "mode": "OFFLINE_DRY_RUN"},
            "metrics": {"live_provider_calls": 0, "production_mutations": 0},
            "verifier": {"verified": True, "scope": "harness-contract-only"},
            "stdout": "offline dry run\n",
            "stderr": "",
        },
    )

    inconclusive = evaluate_gates(
        {
            "mission_attempts_per_condition": {"A": 0, "B": 0, "C": 0, "D": 0},
            "new_correctness_failures": 0,
            "safety_regressions": 0,
            "mission_success_noninferior": {},
        },
        protocol,
    )
    if {entry["verdict"] for entry in inconclusive.values()} != {"INCONCLUSIVE"}:
        raise AssertionError("dry run must never manufacture a promotion PASS")

    return {
        "experiment_id": "JAR-EXP-0013",
        "verdict": "READY_FOR_CONTROLLED_HOST_RUN",
        "live_provider_calls": 0,
        "production_mutations": 0,
        "protocol": "PASS",
        "source_pins": "PASS",
        "fixture_server": "PASS",
        "trace_replay": "PASS",
        "evidence_contract": "PASS",
        "promotion_gates": "INCONCLUSIVE_NO_LIVE_DATA",
        "negative_controls_defined": list(NEGATIVE_CONTROLS),
        "next_stage_requirements": [
            "controlled Windows Hermes host",
            "ToolRush pinned installation",
            "Chromium host runtime",
            "Obscura pinned installation",
        ],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="jar-exp-0013-dry-run-") as directory:
        result = run_dry_run(Path(directory))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
