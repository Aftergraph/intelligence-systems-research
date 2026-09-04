"""
test_hci_cognitive_model_script.py
==================================

Pins experiments/hci_cognitive_model.py (STUDY-006 pre-trial GOMS
pilot) as proper pytest tests. The script simulates 64 operator
personas (32 per arm) across 4 tasks and validates the measurement
pipeline (HEVO, NASA-TLX, undetected-error instrumentation)
BEFORE live human recruitment.

Contract pinned (matches tests/test_study006_goms_pilot.py and the
audit walk-back: HEVO 6.59 -> 1.99, N=0 humans):
- 256 trials (2 arms x 32 subjects x 4 tasks)
- Chat arm HEVO > Mission arm HEVO (the design hypothesis direction)
- Mission arm has fewer undetected errors than chat arm
- NASA-TLX lower in mission arm
- Deterministic seed=777 reproducibility
- CSV is LF
- SIMULATED status: this is a synthetic cognitive model, never
  treated as live human evidence (N=0 humans)
"""

import csv
import importlib.util
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

experiments_path = os.path.join(workspace, "experiments")
if experiments_path not in sys.path:
    sys.path.insert(0, experiments_path)

spec = importlib.util.spec_from_file_location(
    "hci_cognitive_model_module",
    os.path.join(experiments_path, "hci_cognitive_model.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.fixture(scope="module")
def hci_run():
    return mod.simulate_hci_experiment()


@pytest.fixture(scope="module")
def hci_records():
    csv_path = Path(workspace) / "data" / "results_hci_pilot_simulation.csv"
    return list(csv.DictReader(open(csv_path, encoding="utf-8")))


def test_trial_count(hci_records):
    """2 arms x 32 subjects x 4 tasks = 256 trials."""
    assert len(hci_records) == 256, (
        f"Expected 256 trials; got {len(hci_records)}"
    )


def test_two_arms_present(hci_records):
    modalities = {r["modality"] for r in hci_records}
    assert modalities == {"chat_only", "mission_ux"}


def test_32_subjects_per_arm(hci_records):
    chat_subjects = {r["subject_id"] for r in hci_records if r["modality"] == "chat_only"}
    mission_subjects = {r["subject_id"] for r in hci_records if r["modality"] == "mission_ux"}
    assert len(chat_subjects) == 32
    assert len(mission_subjects) == 32


def test_hevo_direction_chat_above_mission(hci_records):
    """The pilot's purpose is to validate the instrumentation can
    detect the expected direction: mission UX requires fewer
    operator interventions than chat."""
    chat = [int(r["hevo_interventions"]) for r in hci_records if r["modality"] == "chat_only"]
    mission = [int(r["hevo_interventions"]) for r in hci_records if r["modality"] == "mission_ux"]
    avg_chat = sum(chat) / len(chat)
    avg_mission = sum(mission) / len(mission)
    assert avg_chat > avg_mission, (
        f"HEVO direction violated: chat={avg_chat:.2f} not > mission={avg_mission:.2f}. "
        f"The GOMS model or the instrumentation has drifted."
    )
    # And the reduction is substantial (audit walk-back: 6.59 -> 1.99, ~70%)
    reduction = 1 - (avg_mission / avg_chat)
    assert reduction >= 0.40, (
        f"HEVO reduction {reduction:.0%} below the 40% design floor. "
        f"Front-door claims (6.6 -> 2.0) would be invalidated."
    )


def test_nasa_tlx_direction(hci_records):
    chat = [float(r["nasa_tlx_score"]) for r in hci_records if r["modality"] == "chat_only"]
    mission = [float(r["nasa_tlx_score"]) for r in hci_records if r["modality"] == "mission_ux"]
    avg_chat = sum(chat) / len(chat)
    avg_mission = sum(mission) / len(mission)
    assert avg_mission < avg_chat, (
        f"TLX direction violated: mission={avg_mission:.1f} not < chat={avg_chat:.1f}"
    )


def test_undetected_error_direction(hci_records):
    """Mission UX isolates errors in exception cards; the chat arm
    must have MORE undetected errors."""
    chat_miss = sum(1 for r in hci_records if r["modality"] == "chat_only" and r["undetected_error"].lower() == "true")
    mission_miss = sum(1 for r in hci_records if r["modality"] == "mission_ux" and r["undetected_error"].lower() == "true")
    assert chat_miss >= mission_miss, (
        f"Undetected-error direction violated: chat={chat_miss}, mission={mission_miss}"
    )


def test_pipeline_status_validated(hci_run):
    assert hci_run["pipeline_status"] == "VALIDATED"


def test_deterministic_seed_reproducible():
    """seed=777 must produce identical summary stats on re-run."""
    r1 = mod.simulate_hci_experiment(seed=777)
    r2 = mod.simulate_hci_experiment(seed=777)
    assert r1["hevo_reduction_pct"] == r2["hevo_reduction_pct"]
    assert r1["tlx_reduction_pct"] == r2["tlx_reduction_pct"]


def test_csv_is_lf(hci_records):
    csv_path = Path(workspace) / "data" / "results_hci_pilot_simulation.csv"
    text = csv_path.read_bytes()
    assert b"\r\n" not in text, "results_hci_pilot_simulation.csv must be LF"
