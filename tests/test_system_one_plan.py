from collections import Counter
from pathlib import Path

from experiments.system_one_acceleration.plan import build_run_plan

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / "data" / "jar_exp_0014_workload_plan_v01.json"
RANDOMIZATION = ROOT / "data" / "jar_exp_0014_randomization_v01.json"


def _plan():
    return build_run_plan(WORKLOAD, RANDOMIZATION)


def test_expands_exactly_270_unique_runs():
    plan = _plan()
    assert len(plan) == 270
    assert len({row.run_id for row in plan}) == 270


def test_each_arm_has_90_runs_and_each_family_has_90_runs():
    plan = _plan()
    assert Counter(row.arm for row in plan) == {"A": 90, "B": 90, "C": 90}
    assert Counter(row.family for row in plan) == {
        "Software Engineering": 90,
        "Operational/Tool Workflow": 90,
        "Research/Structured Evidence": 90,
    }


def test_replication_distribution_is_8_8_7_7_per_arm_family():
    plan = _plan()
    for arm in ("A", "B", "C"):
        for family in {
            "Software Engineering",
            "Operational/Tool Workflow",
            "Research/Structured Evidence",
        }:
            rows = [row for row in plan if row.arm == arm and row.family == family]
            counts = Counter(row.source_workload_id for row in rows)
            assert sorted(counts.values(), reverse=True) == [8, 8, 7, 7]


def test_randomization_is_reproducible_and_not_lexical():
    first = _plan()
    second = _plan()
    assert [row.run_id for row in first] == [row.run_id for row in second]
    assert [row.run_id for row in first] != sorted(row.run_id for row in first)


def test_first_ten_are_stable_regression_sentinel():
    assert [row.run_id for row in _plan()[:10]] == [
        "J14-C-software-engineering-S11-SWE-03-R04",
        "J14-C-research-structured-evidence-S11-RES-02-R05",
        "J14-A-software-engineering-S11-SWE-02-R04",
        "J14-B-operational-tool-workflow-S11-OPS-01-R03",
        "J14-C-operational-tool-workflow-S11-OPS-03-R04",
        "J14-C-research-structured-evidence-S11-RES-01-R07",
        "J14-B-research-structured-evidence-S11-RES-01-R08",
        "J14-A-operational-tool-workflow-S11-OPS-04-R07",
        "J14-A-software-engineering-S11-SWE-04-R06",
        "J14-B-software-engineering-S11-SWE-03-R03",
    ]
