"""Zero-inference preflight for STUDY-012 v3 full execution."""
from __future__ import annotations
import json,os
from pathlib import Path
from scripts.study012_v3_execution_freeze import verify
from experiments.live_benchmark.study012_sentinel_adapter import verify_checkout
from experiments.live_benchmark.study012_matrix_plan_v3 import allocation
ROOT=Path(__file__).resolve().parents[2]
def evaluate(sentinel_dir:Path):
 reasons=[]
 freeze_path=ROOT/"data/study012_v3_execution_freeze_v02.json"
 if not freeze_path.exists():reasons.append("execution_freeze_missing")
 else:
  try:
   if not verify(json.loads(freeze_path.read_text())):reasons.append("execution_freeze_drift")
  except Exception:reasons.append("execution_freeze_invalid")
 readiness=json.loads((ROOT/"data/study012_v3_readiness_20260918.json").read_text())
 if readiness.get("decision")!="READY" or readiness.get("observations")!=9:reasons.append("readiness_not_ready")
 if not all(r.get("final_live") and r.get("final_semantic_match") for r in readiness.get("rows",[])):reasons.append("readiness_row_failure")
 approval=json.loads((ROOT/"data/study012_owner_approval_v3_full_20260918.json").read_text())
 if approval.get("scope")!="V3_CROSS_MODEL_FULL_MATRIX_ONLY":reasons.append("owner_scope_invalid")
 if not approval.get("network_calls_authorized"):reasons.append("network_not_authorized")
 plan=json.loads((ROOT/"data/study012_v3_execution_plan_v01.json").read_text())
 if plan.get("pooling_with_prior_runs") is not False:reasons.append("pooling_not_fail_closed")
 if plan.get("claim_scope",{}).get("provider_independence_claim_allowed") is not False:reasons.append("provider_independence_not_fail_closed")
 rows=allocation()
 if len(rows)!=960 or len({r["trace_id"] for r in rows})!=960:reasons.append("matrix_not_exact")
 ok,reason=verify_checkout(sentinel_dir)
 if not ok:reasons.append(reason)
 if not os.environ.get("NOVITA_API_KEY"):reasons.append("novita_key_missing")
 if not os.environ.get("NVIDIA_API_KEY"):reasons.append("nvidia_key_missing")
 return {"decision":"READY_TO_EXECUTE" if not reasons else "BLOCKED","reasons":reasons,"network_calls_performed":0}
if __name__=="__main__":
 import sys
 print(json.dumps(evaluate(Path(sys.argv[1])),indent=2))
