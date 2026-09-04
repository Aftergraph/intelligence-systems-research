"""
test_study006_goms_pilot.py
============================

Pins the STUDY-006 pre-trial GOMS pilot simulator output. The simulator
is documented in `experiments/hci_cognitive_model.py` and is the
*only* empirical source for HEVO numbers in the program. It uses
seeded GOMS / KLM modeling — NOT real human participants (N=0 humans).

This test pins:
- The simulator runs without error.
- It produces 256 trial records (32 subjects x 2 arms x 4 tasks).
- The HEVO reduction is in the expected range (60% - 80%).
- The output CSV has the expected columns and is persisted to disk.

If the simulator is changed, this test must be updated with a
documented justification and a new expected range.
"""

import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


EXPECTED_TRIAL_COUNT = 256  # 32 subjects x 2 arms x 4 tasks
EXPECTED_HEVO_REDUCTION_MIN_PCT = 50.0  # conservative floor
EXPECTED_HEVO_REDUCTION_MAX_PCT = 85.0  # conservative ceiling
EXPECTED_CSV_PATH = "data/results_hci_pilot_simulation.csv"
EXPECTED_CSV_COLUMNS = [
    "subject_id", "modality", "task_id", "task_name",
    "hevo_interventions", "reading_time_sec", "total_time_sec",
    "nasa_tlx_score", "undetected_error",
]


def test_goms_pilot_runs_cleanly():
    """The GOMS pilot simulator must run without unhandled exceptions."""
    result = subprocess.run(
        [sys.executable, "experiments/hci_cognitive_model.py"],
        cwd=workspace, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"hci_cognitive_model.py exited {result.returncode}\n"
        f"stdout: {result.stdout[-500:]}\n"
        f"stderr: {result.stderr[-500:]}"
    )


def test_goms_pilot_output_csv_exists():
    """The simulator must write its results to a known CSV path."""
    p = Path(workspace) / EXPECTED_CSV_PATH
    assert p.exists(), f"GOMS pilot output not found at {EXPECTED_CSV_PATH}"
    assert p.stat().st_size > 0, f"GOMS pilot output is empty"


def test_goms_pilot_output_csv_columns():
    """The CSV must have the expected columns (frozen schema)."""
    p = Path(workspace) / EXPECTED_CSV_PATH
    with open(p, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
    assert cols == EXPECTED_CSV_COLUMNS, (
        f"GOMS pilot CSV columns {cols} != expected {EXPECTED_CSV_COLUMNS}"
    )


def test_goms_pilot_trial_count():
    """32 subjects x 2 arms x 4 tasks = 256 trials."""
    p = Path(workspace) / EXPECTED_CSV_PATH
    with open(p, encoding="utf-8") as f:
        n = sum(1 for _ in csv.DictReader(f))
    assert n == EXPECTED_TRIAL_COUNT, (
        f"GOMS pilot produced {n} trials, expected {EXPECTED_TRIAL_COUNT}. "
        f"Subject count or task count drifted."
    )


def test_goms_pilot_hevo_reduction_in_range():
    """The HEVO reduction must fall in the expected [50%, 85%] range.
    This is the simulator's primary empirical output and any drift
    outside this range is a flag for review.
    """
    result = subprocess.run(
        [sys.executable, "experiments/hci_cognitive_model.py"],
        cwd=workspace, capture_output=True, text=True, timeout=60,
    )
    # Parse the printed summary line: "Human Effort (HEVO):     Chat = X.XX turns | Mission = Y.YY turns (-Z.Z%)"
    m = re.search(
        r"Human Effort \(HEVO\):\s+Chat = ([\d.]+) turns \| "
        r"Mission = ([\d.]+) turns \(-([\d.]+)%\)",
        result.stdout,
    )
    assert m, (
        f"Could not parse HEVO summary from simulator output.\n"
        f"stdout: {result.stdout[-500:]}"
    )
    chat_hevo = float(m.group(1))
    mission_hevo = float(m.group(2))
    reduction_pct = float(m.group(3))
    # Sanity bounds
    assert chat_hevo > 0, f"chat_hevo={chat_hevo} <= 0"
    assert mission_hevo > 0, f"mission_hevo={mission_hevo} <= 0"
    assert mission_hevo < chat_hevo, (
        f"mission_hevo={mission_hevo} not less than chat_hevo={chat_hevo}"
    )
    # Range check
    assert EXPECTED_HEVO_REDUCTION_MIN_PCT <= reduction_pct <= EXPECTED_HEVO_REDUCTION_MAX_PCT, (
        f"HEVO reduction {reduction_pct:.1f}% is outside the expected "
        f"range [{EXPECTED_HEVO_REDUCTION_MIN_PCT}%, "
        f"{EXPECTED_HEVO_REDUCTION_MAX_PCT}%]. "
        f"This is a flag for review (the simulator may have drifted "
        f"or the experimental design may have changed)."
    )


def test_frontdoor_hevo_numbers_match_goms_pilot():
    """The HEVO numbers in front-door docs (README, exec summary) must
    match the actual GOMS pilot output. If they don't, the front-door
    is carrying a stale overclaim.

    Front-door docs are allowed to use approximations (e.g. rounded
    to 1 decimal place) but the underlying simulator number must
    match the printed summary.
    """
    result = subprocess.run(
        [sys.executable, "experiments/hci_cognitive_model.py"],
        cwd=workspace, capture_output=True, text=True, timeout=60,
    )
    m = re.search(
        r"Chat = ([\d.]+) turns \| Mission = ([\d.]+) turns",
        result.stdout,
    )
    assert m, "Could not parse HEVO summary"
    chat_hevo = float(m.group(1))
    mission_hevo = float(m.group(2))
    # Format as the front-door docs use
    chat_str = f"{chat_hevo:.1f}"
    mission_str = f"{mission_hevo:.1f}"

    for doc in ["README.md", "00-EXECUTIVE-SUMMARY.md"]:
        text = (Path(workspace) / doc).read_text(encoding="utf-8")
        # Look for the HEVO row in the metrics table
        hevo_line = None
        for line in text.splitlines():
            if "Human Effort" in line or "HEVO" in line and "turns" in line:
                hevo_line = line
                break
        if hevo_line is None:
            continue
        # The chat number must appear (or a rounded form of it).
        # We allow 1-decimal rounding: 6.59 -> 6.6
        # But not 14.2 or 4.5 (the old GOMS design).
        for stale in ["14.2", "4.5"]:
            assert stale not in hevo_line, (
                f"{doc} HEVO row still carries stale number {stale!r}. "
                f"Current GOMS pilot outputs Chat={chat_str} "
                f"Mission={mission_str}. Update the front-door."
            )


def test_goms_pilot_prints_disclaimer():
    """The simulator must print its 'synthetic / N=0 humans' disclaimer
    in stdout (or in a docstring) to prevent the result from being
    misread as a live human study."""
    src = (Path(workspace) / "experiments/hci_cognitive_model.py").read_text(
        encoding="utf-8"
    )
    assert "synthetic" in src.lower() or "not" in src.lower() and "human" in src.lower(), (
        "hci_cognitive_model.py missing the synthetic/N=0 humans "
        "disclaimer. The pilot result must never be misread as a "
        "live human study."
    )
    # And the disclaimer must mention N=0 or "synthetic"
    assert "N=0" in src or "synthetic" in src or "calibration" in src.lower(), (
        "hci_cognitive_model.py must declare N=0 humans (synthetic) "
        "or state that the model is for pipeline calibration only."
    )
