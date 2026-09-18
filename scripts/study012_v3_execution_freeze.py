"""Immutable execution freeze for STUDY-012 cross-model v3."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 "data/study012_v3_freeze_manifest_v01.json",
 "data/study012_owner_approval_v3_full_20260918.json",
 "data/study012_provider_model_matrix_v3.json",
 "data/study012_v3_execution_plan_v01.json",
 "data/study012_v3_readiness_20260918.json",
 "data/study012_novita_sandbox_resume_proof_20260918.json",
 "data/study012_r2_extension_v03.json",
 "data/study012_sentinel_binding_v01.json",
 "experiments/live_benchmark/study012_matrix_plan_v3.py",
 "experiments/live_benchmark/study012_v3_sandbox_runner.py",
 "experiments/live_benchmark/study012_evaluators.py",
 "experiments/live_benchmark/study012_sentinel_adapter.py",
 "tests/test_study012_v3_sandbox_runner.py",
]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 readiness=json.loads((ROOT/"data/study012_v3_readiness_20260918.json").read_text())
 approval=json.loads((ROOT/"data/study012_owner_approval_v3_full_20260918.json").read_text())
 plan=json.loads((ROOT/"data/study012_v3_execution_plan_v01.json").read_text())
 return {
  "schema_version":"aftergraph.study012.v3-execution-freeze.v0.2",
  "study_id":"STUDY-012",
  "execution_id":"study012-cross-model-v3-20260918",
  "status":"FROZEN_AUTHORIZED_FOR_EXACT_V3_EXECUTION",
  "files":{p:sha(ROOT/p) for p in FILES},
  "gates":{
   "readiness_decision":readiness.get("decision"),
   "readiness_observations":readiness.get("observations"),
   "owner_approval_ref":approval.get("approval_ref"),
   "network_calls_authorized":approval.get("network_calls_authorized") is True,
   "max_total_api_calls":approval.get("max_total_api_calls"),
   "hard_cost_stop_usd":approval.get("hard_cost_stop_usd"),
   "pooling_with_prior_runs":plan.get("pooling_with_prior_runs"),
   "provider_independence_claim_allowed":plan.get("claim_scope",{}).get("provider_independence_claim_allowed"),
   "execution_fabric":plan.get("execution_fabric",{}).get("provider"),
  }
 }
def verify(m):
 e=build()
 return m.get("files")==e["files"] and m.get("gates")==e["gates"] and m.get("execution_id")==e["execution_id"]
if __name__=="__main__":
 out=ROOT/"data/study012_v3_execution_freeze_v02.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
