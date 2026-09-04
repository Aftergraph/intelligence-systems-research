import json
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, "..", ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from experiments.live_benchmark.harness import LiveModelClient, run_condition_trial, CONDITIONS

def test_live_harness_dry_run():
    print("==================================================================")
    print(" TESTING LIVE BENCHMARK HARNESS (DRY-RUN VALIDATION)")
    print(" Validating Provenance & 7 Conditions (A -> G)")
    print("==================================================================")

    output_dir = os.path.join(workspace, "data", "live_benchmark_dry_runs")
    client = LiveModelClient(provider="openai", model_id="gpt-4o")

    sample_task = {
        "id": "TASK-LIVE-01",
        "prompt": "Fix null pointer in auth middleware.",
        "mission": {
            "apiVersion": "intelligence.systems/v0alpha1",
            "kind": "Mission",
            "metadata": {"id": "mission-live-01", "version": 1},
            "objective": {"outcome": "Fix null pointer bug."},
            "success": {"all": ["tests_passed"]},
            "budget": {"tokens": {"max": 10000}}
        },
        "delegation": {
            "id": "del-live-01",
            "principal": "urn:principal:lead-dev",
            "delegate": "urn:agent:coder-bot",
            "purpose": "mission-live-01",
            "scope": {"allowed_capabilities": ["mcp://git/*", "mcp://pytest/*"]},
            "valid_from": "2026-09-01T00:00:00Z",
            "expires_at": "2026-09-30T00:00:00Z"
        }
    }

    manifests = []
    for cond_code in ["A", "B", "C", "D", "E", "F", "G"]:
        manifest_path, verified = run_condition_trial(
            condition=cond_code,
            task=sample_task,
            model_client=client,
            output_dir=output_dir,
            dry_run=True
        )
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            assert manifest_data["manifest_sha256"] is not None
            assert manifest_data["condition"] == cond_code
        manifests.append(manifest_path)
        print(f"[PASS] Condition {cond_code} ({CONDITIONS[cond_code]}): Manifest generated with SHA-256 {manifest_data['manifest_sha256'][:12]}")

    print("==================================================================")
    print(f"SUCCESS: All 7 benchmark conditions validated. Ready for live API execution.")
    print("==================================================================")

if __name__ == "__main__":
    test_live_harness_dry_run()
