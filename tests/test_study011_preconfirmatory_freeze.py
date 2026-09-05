"""
test_study011_preconfirmatory_freeze.py
========================================

Pre-run gate (blocker #2 + #5): pins the STUDY-011-PRECONFIRMATORY
freeze snapshot — code hash, dependency lock, runtime versions, frozen
artifacts, verifier hash — and enforces the no-silent-change invariant
via data/study011_impl_fingerprint.json (regenerate + compare = drift
detection).

The fingerprint is written at gate time; any subsequent change to a
frozen artifact (confirmatory code, verifier, workloads, matrix,
preregistration) changes the hash and the study must be re-gated.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

FP = Path(workspace) / "data" / "study011_impl_fingerprint.json"


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


FROZEN_FILES = [
    "experiments/live_benchmark/run_study_011.py",
    "experiments/live_benchmark/study011_analyze.py",
    "experiments/live_benchmark/study011_rate_limit.py",
    "experiments/live_benchmark/verifier_v2.py",
    "data/study011_workload_manifest.json",
    "data/study011_workloads_frozen.json",
    "data/study011_provider_model_matrix.json",
    "data/study011_run_math.json",
    "data/study011_preregistration_manifest.json",
    "data/study011_dependency_lock.txt",
]


def compute_fingerprint() -> dict:
    import platform
    files = {}
    for rel in FROZEN_FILES:
        p = Path(workspace) / rel
        files[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    lock = Path(workspace) / "data/study011_dependency_lock.txt"
    return {
        "tag": "STUDY-011-PRECONFIRMATORY",
        "created_utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "dependency_lock_hash": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
        "files": files,
    }


@pytest.fixture(scope="module")
def fingerprint():
    fp_path = Path(workspace) / "data" / "study011_impl_fingerprint.json"
    if not fp_path.exists():
        fp_path.write_text(
            json.dumps(compute_fingerprint(), indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
    return json.load(open(fp_path, encoding="utf-8"))


def test_fingerprint_tag(fingerprint):
    assert fingerprint["tag"] == "STUDY-011-PRECONFIRMATORY"


def test_all_frozen_files_hashed(fingerprint):
    missing = [rel for rel in FROZEN_FILES if rel not in fingerprint["files"]]
    assert not missing, f"fingerprint missing frozen files: {missing}"


def test_no_drift_since_gate(fingerprint):
    """Blocker #5 hard invariant: frozen artifacts must not have changed
    since the fingerprint was written."""
    current = compute_fingerprint()
    drift = []
    for rel, h in fingerprint["files"].items():
        p = Path(workspace) / rel
        if not p.exists():
            drift.append(f"{rel}: FILE DELETED")
            continue
        now_h = hashlib.sha256(p.read_bytes()).hexdigest()
        if now_h != h:
            drift.append(f"{rel}: hash changed")
    assert not drift, (
        "FROZEN ARTIFACT DRIFT DETECTED (no-silent-change invariant): "
        + "; ".join(drift)
    )


def test_dependency_lock_present_and_hashed(fingerprint):
    h = fingerprint.get("dependency_lock_hash") or fingerprint["files"].get(
        "data/study011_dependency_lock.txt")
    assert h, "dependency lock hash missing from fingerprint"
    lock = Path(workspace) / "data/study011_dependency_lock.txt"
    assert lock.exists()
    n = len(lock.read_text(encoding="utf-8").strip().splitlines())
    assert n >= 50, f"dependency lock suspiciously small: {n} packages"


def test_runtime_versions_recorded(fingerprint):
    assert fingerprint.get("python_version")
    assert fingerprint.get("platform")


def test_verifier_version_recorded():
    """The verifier version must be pinned and match verifier_v2."""
    sys.path.insert(0, str(Path(workspace) / "experiments" / "live_benchmark"))
    from verifier_v2 import VERIFIER_VERSION
    assert VERIFIER_VERSION == "2.0.0"


def test_run_math_matches_prereg():
    """Blocker #4: the frozen run math must reconcile with the prereg."""
    rm = json.load(open(Path(workspace) / "data" / "study011_run_math.json", encoding="utf-8"))
    d = rm["derivation"]
    assert d["live_valid_target_per_cell"] == 58
    assert d["cells"] == 8
    assert d["phase1_min_live_valid"] == 464
    assert 4 * 2 * 58 == 464
    assert d["nominal_attempts_total"] == 480
    assert 8 * 60 == 480
    # Amendment 010: per-cell cap for openrouter cells 5-8 extended 78→156
    # (429-burn = deterministic quota exhaustion, not sampling failure).
    # Global ceiling 931 = 619 + 4×78.
    assert d["attempts_ceiling_total"] == 931
    assert d["attempts_ceiling_per_cell"] == 156
    import math
    assert math.ceil(464 / 0.75) == 619  # base ceiling pre-amendment still holds
    assert 619 + 4 * 78 == 931
    assert rm["maximum_attempts_per_cell"] == 78  # dialagram cells 1-4 retain 78
    assert rm["stopping_rule"]["per_cell"].startswith("stop the cell when LIVE_VALID >= 58")
    assert "no simulation fallback" in rm["stopping_rule"]["on_non_viable"].lower()


def test_runner_loop_implements_frozen_math():
    """The runner must reference the frozen run math + per-cell caps."""
    src = (Path(workspace) / "experiments" / "live_benchmark" / "run_study_011.py").read_text(encoding="utf-8")
    for marker in [
        "LIVE_VALID_MIN_PER_CELL",
        "ATTEMPTS_MAX_PER_CELL",
        "ATTEMPTS_CEILING_TOTAL",
        "study011_run_math.json",
        "study011_replicate_seed_table.json",
        "viable",
    ]:
        assert marker in src, f"runner loop missing frozen-math marker: {marker}"


def test_runner_no_silent_config_change():
    """Blocker #5: the runner must compute a fingerprint at startup and
    abort if frozen artifacts changed mid-batch."""
    src = (Path(workspace) / "experiments" / "live_benchmark" / "run_study_011.py").read_text(encoding="utf-8")
    assert "study011_impl_fingerprint.json" in src, (
        "runner must check the frozen implementation fingerprint at startup"
    )
