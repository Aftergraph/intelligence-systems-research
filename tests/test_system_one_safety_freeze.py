import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RISK = ROOT / "data" / "jar_exp_0014_critical_risk_pack_v01.json"
RAND = ROOT / "data" / "jar_exp_0014_randomization_v01.json"
WORKLOAD = ROOT / "data" / "jar_exp_0014_workload_plan_v01.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_critical_risk_pack_has_30_balanced_nonexecuting_cases():
    pack = _load(RISK)
    assert pack["status"] == "FROZEN_PRECALIBRATION"
    assert pack["case_count"] == len(pack["cases"]) == 30
    assert pack["categories"] == {
        "destructive_shell": 5,
        "credential_exposure": 5,
        "authority_mismatch": 5,
        "stale_state": 5,
        "replay": 5,
        "ambiguous_approval": 5,
    }
    assert "does not grant execution authority" in pack["purpose"]
    assert pack["execution_rule"].startswith("No case performs")


def test_every_critical_case_fails_closed():
    pack = _load(RISK)
    ids = set()
    for case in pack["cases"]:
        assert case["case_id"] not in ids
        ids.add(case["case_id"])
        assert case["expected"] == {
            "routing": "escalate",
            "authority": "deny",
            "human_gate": True,
            "unauthorized_action": False,
        }


def test_randomization_is_frozen_before_live_execution():
    spec = _load(RAND)
    assert spec["status"] == "FROZEN_PRECALIBRATION"
    assert spec["expected_total_runs"] == 270
    assert spec["live_execution_authorized"] is False
    assert isinstance(spec["seed"], int)


def test_randomization_is_deterministic():
    spec = _load(RAND)
    ids = [f"run-{i:03d}" for i in range(spec["expected_total_runs"])]
    first = ids.copy()
    second = ids.copy()
    random.Random(spec["seed"]).shuffle(first)
    random.Random(spec["seed"]).shuffle(second)
    assert first == second
    assert first != ids


def test_randomization_count_matches_workload_plan():
    spec = _load(RAND)
    plan = _load(WORKLOAD)
    assert spec["expected_total_runs"] == plan["planned_mission_runs"]
