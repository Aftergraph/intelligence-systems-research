from __future__ import annotations

import json
from pathlib import Path

from jev_engineering.campaign_readiness import (
    CompletionReadinessPolicy,
    analyze_completion_readiness,
    plan_powered_campaign,
    recommend_turn_budgets,
)

root = Path(__file__).resolve().parents[1]
evidence = json.loads((root / "evidence/v216-lineage-proof/evidence.json").read_text())
records = evidence["execution"]["records"]
readiness = analyze_completion_readiness(
    records,
    incumbent_condition="qwen-frontier-control",
    candidate_condition="qwen-jev-control",
    policy=CompletionReadinessPolicy(),
)
turns = recommend_turn_budgets(readiness, current_max_turns=4)
plan = plan_powered_campaign(
    readiness=readiness,
    baseline_vsr_assumption=0.90,
    noninferiority_margin=0.02,
    alpha=0.05,
    power=0.80,
    shadow_pairs=5,
    experiment_pairs=10,
    min_holdout_pairs=20,
    live_lineage_proven=bool(evidence.get("live_provider_measurement")),
    pricing_reviewed=False,
    preregistered=False,
)
out = {
    "version": "2.17.0",
    "source_campaign_sha256": evidence["campaign_sha256"],
    "completion_readiness": readiness.to_dict(),
    "turn_budget_recommendations": [x.__dict__ if hasattr(x, "__dict__") else {name: getattr(x, name) for name in x.__slots__} for x in turns],
    "powered_campaign_plan": plan.to_dict(),
    "truth_boundary": "v2.16 live proof is used only to gate readiness; no powered provider campaign is executed by this script.",
}
print(json.dumps(out, indent=2, sort_keys=True))