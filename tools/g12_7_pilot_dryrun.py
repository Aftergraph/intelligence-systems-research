"""G12-7 generator: pilot dry-run plan for ICT-EXP-001 over synthetic fixtures.

Walks the frozen v1.0.0 manifest + fixtures, validates integrity, and emits a
DRY-RUN execution plan: what WOULD run, in which order, with which declared
inputs. Performs ZERO agent execution, makes ZERO live API calls, draws ZERO
empirical conclusions. Output: data/study012_pilot_dryrun_report.json (+ .sha256).
"""
import hashlib
import json
from pathlib import Path

WS = Path("/root/workspace/aftergraph/intelligence-systems-research")
MANIFEST = WS / "data" / "study012_workload_manifest.json"
FIXDIR = WS / "data" / "study012_fixtures"
REPORT = WS / "data" / "study012_pilot_dryrun_report.json"


def canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["freeze_version"] == "v1.0.0"
    plan = []
    seen_pairs = set()
    for w in manifest["workloads"]:
        wid = w["workload_id"]
        fixture = json.loads((FIXDIR / f"{wid}.json").read_text())
        # Validate fixture hash against manifest (dry-run integrity check)
        assert hashlib.sha256(canon(fixture)).hexdigest() == w["sha256"], wid
        pair = tuple(sorted([wid, w["comparison_pair"]]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            plan.append(
                {
                    "pair": list(pair),
                    "task_family": w["task_family"],
                    "would_execute": f"Run {pair[0]} (I5) then {pair[1]} (I6) against synthetic fixtures; collect verdicts via pinned IndependentVerifier; compare containment outcomes.",
                    "declared_inputs": [f"data/study012_fixtures/{pair[0]}.json", f"data/study012_fixtures/{pair[1]}.json"],
                    "live_api_calls": 0,
                    "status": "PLANNED-NOT-EXECUTED",
                }
            )
    report = {
        "_notice": "DRY-RUN ONLY. This plan was never executed. No agent ran, no live API was called, no empirical conclusions exist. Executing this plan requires G12-8 clearance + G12-10 window.",
        "study_id": "STUDY-012",
        "experiment_id": "ICT-EXP-001",
        "gate": "G12-7 pilot dry-run (synthetic, no live APIs)",
        "freeze_version": "DRAFT",
        "manifest_root_hash": manifest["root_hash"],
        "manifest_freeze_version": manifest["freeze_version"],
        "fixtures_validated": len(manifest["workloads"]),
        "comparison_pairs": plan,
        "execution_occurred": False,
        "empirical_conclusions": [],
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (WS / "data" / "study012_pilot_dryrun_report.json.sha256").write_text(
        hashlib.sha256(REPORT.read_bytes()).hexdigest() + "\n"
    )
    print(f"pairs={len(plan)} validated={report['fixtures_validated']}")


if __name__ == "__main__":
    main()
