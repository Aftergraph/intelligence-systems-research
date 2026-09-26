from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

import jsonschema

from jev_engineering.campaign_evidence import CampaignEvidenceBundle
from jev_engineering.campaign_runtime import BenchmarkCostModel, TokenPrice
from jev_engineering.evidence_campaign import EvidenceCampaignPolicy, evaluate_evidence_campaign


def _schema(name: str):
    return json.loads((files("jev_engineering") / "schemas" / name).read_text(encoding="utf-8"))


def _record(condition: str, case: str, repeat: int):
    return {
        "condition": condition, "case_id": case, "repeat": repeat, "status": "verified",
        "metrics": {
            "completion_claims": 1, "false_completion_claims": 0,
            "provider_input_tokens": 1000, "provider_output_tokens": 100,
            "provider_cached_input_tokens": 0, "decision_input_tokens": 100 if condition == "jev" else 1000,
            "decision_output_tokens": 0 if condition == "jev" else 100, "wall_time_ms": 1000,
        },
    }


def test_evidence_campaign_report_conforms_to_packaged_schema():
    rows = []
    for repeat in range(1, 4):
        for case in ("a", "b"):
            rows += [_record("frontier", case, repeat), _record("jev", case, repeat)]
    report = evaluate_evidence_campaign(
        rows, incumbent_condition="frontier", candidate_condition="jev",
        cost_model=BenchmarkCostModel(
            generator=TokenPrice(4, 20, 0.4),
            decision_by_condition={"frontier": TokenPrice(4, 20), "jev": TokenPrice(0.042, 0)},
            frontier_decision_conditions=frozenset({"frontier"}),
        ),
        shadow_pairs=2, experiment_pairs=2, holdout_pairs=2,
        policy=EvidenceCampaignPolicy(min_holdout_pairs=2, bootstrap_samples=1000),
    )
    jsonschema.validate(report, _schema("evidence-campaign-report.v1.schema.json"))


def test_campaign_evidence_bundle_conforms_to_packaged_schema(tmp_path: Path):
    files_in = []
    for name in ("manifest.yaml", "pricing.json", "results.jsonl", "report.json"):
        path = tmp_path / name
        path.write_text("{}\n", encoding="utf-8")
        files_in.append(path)
    bundle = CampaignEvidenceBundle.create(
        manifest=files_in[0], pricing=files_in[1], results=files_in[2], report=files_in[3],
        output=tmp_path / "bundle.json", package_version="2.5.0",
    )
    jsonschema.validate(bundle.payload, _schema("campaign-evidence-bundle.v1.schema.json"))
