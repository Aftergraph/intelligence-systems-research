"""STUDY-012 full-matrix admissibility gate. No network calls."""
from __future__ import annotations
import json
from pathlib import Path
import hashlib
from experiments.live_benchmark.study012_matrix_plan import allocation, summary
ROOT=Path(__file__).resolve().parents[2]

def evaluate():
    reasons=[]
    ext=json.loads((ROOT/"data/study012_r2_extension_v03.json").read_text(encoding="utf-8"))
    bindings=json.loads((ROOT/"data/study012_evaluator_bindings_v01.json").read_text(encoding="utf-8"))
    budget=json.loads((ROOT/"data/study012_execution_budget_v01.json").read_text(encoding="utf-8"))

    required_ext={"id","r2_class","oracle","prompt","fixture_hashes","acceptance_criteria_hash","response_contract","fixture"}
    incomplete=[]
    for w in ext.get("workloads",[]):
        missing=sorted(required_ext-set(w))
        if missing: incomplete.append({"id":w.get("id"),"missing":missing})
    if incomplete: reasons.append("r2_extension_workloads_not_execution_complete")
    classes=[w.get("r2_class") for w in ext.get("workloads",[])]
    expected_classes={"stale_state","revocation","contradiction","cross_subject_isolation","constraint_decay","replay","crash_recovery","adversarial_evidence"}
    if set(classes)!=expected_classes or len(classes)!=8: reasons.append("r2_class_coverage_not_exact_8")
    def chash(x):
        raw=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
    for w in ext.get("workloads",[]):
        if w.get("fixture_hashes",{}).get("input_fixture")!=chash(w.get("fixture")):
            reasons.append(f"fixture_hash_drift:{w.get('r2_class')}")
        if w.get("acceptance_criteria_hash")!=chash(w.get("response_contract")):
            reasons.append(f"criterion_hash_drift:{w.get('r2_class')}")

    plan=allocation(); s=summary(plan)
    if s["observations"] != 960: reasons.append("matrix_size_not_960")
    if s["by_provider"] != {"openrouter":480,"google":480}: reasons.append("provider_allocation_not_balanced")
    if len({x["trace_id"] for x in plan}) != 960: reasons.append("trace_ids_not_unique")

    cond=bindings.get("conditions",{})
    for name in ("J","D","JD","DI"):
        if name not in cond: reasons.append(f"condition_binding_missing:{name}")
    if cond.get("J",{}).get("canonical_verified_allowed") is not False:
        reasons.append("judge_only_not_fail_closed")
    if cond.get("JD",{}).get("canonical_authority")!="deterministic_oracle":
        reasons.append("jd_canonical_authority_not_deterministic")
    if cond.get("DI",{}).get("independent_receipt_required") is not True:
        reasons.append("di_independent_receipt_not_required")

    retry=budget.get("retry_policy",{})
    if retry.get("max_attempts_per_api_call") != 2 or retry.get("max_total_api_calls") != 2880:
        reasons.append("attempt_ceiling_not_frozen")
    cap=budget.get("hard_cost_stop_usd")
    if not isinstance(cap,(int,float)) or cap<=0:
        reasons.append("cost_cap_not_frozen")

    sentinel=json.loads((ROOT/"data/study012_sentinel_binding_v01.json").read_text(encoding="utf-8"))
    works=json.loads((ROOT/"data/study012_works_verification_binding_v01.json").read_text(encoding="utf-8"))
    if sentinel.get("exact_commit")!="f9a0f85a50cd4a74400b8b267c29a943da5af68b":
        reasons.append("sentinel_commit_not_pinned")
    if sentinel.get("fallback_allowed") is not False:
        reasons.append("sentinel_fallback_not_fail_closed")
    if works.get("route")!="POST /v1/works/{id}/verification":
        reasons.append("works_verification_route_not_bound")

    return {
      "decision":"READY_FOR_OWNER_APPROVAL" if not reasons else "NOT_ADMISSIBLE",
      "reasons":reasons,
      "matrix":s,
      "incomplete_extension_workloads":incomplete,
      "condition_bindings":cond,
      "retry_policy":retry,
      "hard_cost_stop_usd":cap,
      "network_calls_performed":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2))
