#!/usr/bin/env python3
"""Track A Live-GO readiness checker — verifies all prerequisites for
running STUDY-008-LIVE-v2 with real API credits.

Checks:
  1. API key env vars (DIALAGRAM_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY,
     ANTHROPIC_API_KEY, GOOGLE_API_KEY) — presence only, never prints values.
  2. Provider/model matrix file exists and is loadable.
  3. Fault injection harness imports cleanly.
  4. Runner script has no syntax errors.

Usage:
  python track_a_go_check.py [--verbose]

Exit codes: 0 = READY, 1 = NOT READY (at least one check failed).
Prints a machine-readable JSON summary to stdout.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

WORKSPACE = Path(__file__).resolve().parent.parent.parent
REQUIRED_KEYS = [
    "DIALAGRAM_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
]
OPTIONAL_FILES = [
    "data/study008_v2_provider_model_matrix.json",
    "data/study008_v2_runs/run_study_008v2_results.json",
]


def main() -> int:
    checks = {}

    # 1. API keys (presence only — never log values)
    for key in REQUIRED_KEYS:
        checks[f"key:{key}"] = "SET" if os.environ.get(key) else "MISSING"

    # 2. Provider/model matrix
    matrix_path = WORKSPACE / "data" / "study008_v2_provider_model_matrix.json"
    checks["file:provider_model_matrix"] = "OK" if matrix_path.is_file() else "MISSING"

    # 3. Fault injection harness importable
    try:
        sys.path.insert(0, str(WORKSPACE / "experiments" / "live_benchmark"))
        import fault_injection  # noqa: F401
        checks["import:fault_injection"] = "OK"
    except ImportError as e:
        checks["import:fault_injection"] = f"FAIL: {e}"

    # 4. Runner script syntax check
    runner = Path(__file__).resolve().parent / "run_study_008v2.py"
    if runner.is_file():
        compile(runner.read_text(), str(runner), "exec")
        checks["syntax:run_study_008v2.py"] = "OK"
    else:
        checks["syntax:run_study_008v2.py"] = "MISSING"

    # Verdict
    failed = [k for k, v in checks.items() if "FAIL" in v or "MISSING" in v]
    ready = len(failed) == 0

    print(json.dumps({
        "ready": ready,
        "checks": checks,
        "failed": failed,
        "summary": f"{len(checks) - len(failed)}/{len(checks)} checks passed",
    }, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
