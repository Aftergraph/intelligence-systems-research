from __future__ import annotations

import json
from importlib.resources import files

import jsonschema

from jev_engineering.system_efficiency import (
    EfficiencyLever,
    FrontierWorkloadProfile,
    SystemEfficiencyCompiler,
)


def _schema(name: str):
    return json.loads((files("jev_engineering") / "schemas" / name).read_text(encoding="utf-8"))


def test_frontier_workload_profile_conforms_to_packaged_schema():
    profile = FrontierWorkloadProfile(
        "p", {"context": 100, "control": 20}, verified_outcomes=9, missions=10
    )
    jsonschema.validate(profile.to_dict(), _schema("frontier-workload-profile.v1.schema.json"))


def test_system_efficiency_plan_conforms_to_packaged_schema():
    profile = FrontierWorkloadProfile("p", {"context": 100})
    plan = SystemEfficiencyCompiler().compile(
        profile,
        [EfficiencyLever("compress", {"context": 0.5}, evidence_level="observed")],
        target_ratio=2.0,
        minimum_evidence_level="observed",
    )
    jsonschema.validate(plan.to_dict(), _schema("system-efficiency-plan.v1.schema.json"))
