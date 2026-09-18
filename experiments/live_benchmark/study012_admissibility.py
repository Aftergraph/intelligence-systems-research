"""STUDY-012 full-matrix admissibility gate. No network calls."""
from __future__ import annotations
import json
from pathlib import Path
from experiments.live_benchmark.study012_matrix_plan import allocation, summary
ROOT=Path(__file__).resolve().parents[2]

def evaluate():
    reasons=[]
    parent=json.loads((ROOT/"data/study012_workload_manifest.json").read_text(encoding="utf-8"))
    ext=json.loads((ROOT/"data/study012_r2_extension_v01.json").read_text(encoding="utf-8"))
    matrix=json.loads((ROOT/"data/study012_provider_model_matrix.json").read_text(encoding="utf-8"))

    # Parent frozen workloads are evidence-rich; amendment workloads must reach same bar.
    required_ext={"id","r2_class","oracle","prompt","fixture_hashes","acceptance_criteria_hash"}
    incomplete=[]
    for w in ext.get("workloads",[]):
        missing=sorted(required_ext-set(w))
        if missing: incomplete.append({"id":w.get("id"),"missing":missing})
    if incomplete: reasons.append("r2_extension_workloads_not_execution_complete")

    # Provider allocation is deterministic and balanced.
    plan=allocation()
    s=summary(plan)
    if s["observations"] != 960: reasons.append("matrix_size_not_960")
    if s["by_provider"] != {"openrouter":480,"google":480}: reasons.append("provider_allocation_not_balanced")

    # Conditions need executable bindings, not names alone.
    condition_bindings={
      "J": None,
      "D": "src.study012_oracles",
      "JD": None,
      "DI": None,
    }
    if any(v is None for v in condition_bindings.values()):
        reasons.append("condition_evaluator_bindings_incomplete")

    # Retry/attempt ceiling must be preregistered before paid/live matrix execution.
    attempt_ceiling=None
    if attempt_ceiling is None: reasons.append("attempt_ceiling_not_frozen")

    # Cost cap must be an explicit owner-controlled execution bound.
    cost_cap_usd=None
    if cost_cap_usd is None: reasons.append("cost_cap_not_frozen")

    return {
      "decision":"READY_FOR_OWNER_APPROVAL" if not reasons else "NOT_ADMISSIBLE",
      "reasons":reasons,
      "matrix":s,
      "incomplete_extension_workloads":incomplete,
      "condition_bindings":condition_bindings,
      "attempt_ceiling":attempt_ceiling,
      "cost_cap_usd":cost_cap_usd,
      "network_calls_performed":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2))
