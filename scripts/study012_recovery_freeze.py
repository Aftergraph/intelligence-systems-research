"""Immutable freeze builder for STUDY-012 provider-recovery replication v2."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 "STUDY-012-AMENDMENT-005-PROVIDER-RECOVERY-V2.md",
 "data/study012_r2_extension_v03.json",
 "data/study012_provider_model_matrix_v2.json",
 "data/study012_evaluator_bindings_v02.json",
 "data/study012_recovery_plan_v2.json",
 "data/study012_recovery_v2_pricing_v01.json",
 "data/study012_owner_approval_v2_readiness_20260918.json",
 "data/study012_recovery_v2_readiness_20260918.json",
 "data/study012_owner_approval_recovery_v2_full_20260918.json",
 "data/study012_sentinel_binding_v01.json",
 "data/study012_works_verification_binding_v01.json",
 "providers/google.py",
 "providers/nvidia.py",
 "providers/http_failure.py",
 "experiments/live_benchmark/study012_matrix_plan_v2.py",
 "experiments/live_benchmark/study012_recovery_v2_readiness.py",
 "experiments/live_benchmark/study012_full_runner_v2.py",
 "experiments/live_benchmark/study012_evaluators.py",
 "experiments/live_benchmark/study012_sentinel_adapter.py",
 "src/study012_oracles.py",
 "tests/test_study012_recovery_v2.py",
 "tests/test_study012_full_runner_v2.py",
 "tests/test_direct_recovery_providers.py",
 "tests/test_study012_evaluators.py",
 "tests/test_study012_sentinel_adapter.py",
]
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
 readiness=json.loads((ROOT/"data/study012_recovery_v2_readiness_20260918.json").read_text(encoding="utf-8"))
 approval=json.loads((ROOT/"data/study012_owner_approval_recovery_v2_full_20260918.json").read_text(encoding="utf-8"))
 return {
  "schema_version":"aftergraph.study012.recovery-freeze.v1",
  "study_id":"STUDY-012",
  "execution_id":"study012-recovery-v2-20260918",
  "parent_execution_id":"study012-full-matrix-20260918",
  "pooling_with_parent":False,
  "status":"FROZEN_AUTHORIZED_FOR_EXACT_V2_EXECUTION",
  "files":{p:sha(ROOT/p) for p in FILES},
  "execution_gate":{
   "readiness_decision":readiness.get("decision"),
   "readiness_calls":readiness.get("calls"),
   "full_owner_approval_ref":approval.get("approval_ref"),
   "network_calls_authorized":approval.get("network_calls_authorized") is True,
   "max_total_api_calls":approval.get("max_total_api_calls"),
   "hard_cost_stop_usd":approval.get("hard_cost_stop_usd"),
   "provider_substitution_allowed":False,
  }
 }
def verify(manifest):
 expected=build()
 return manifest.get("files")==expected["files"] and manifest.get("execution_gate")==expected["execution_gate"]
if __name__=="__main__":
 out=ROOT/"data/study012_recovery_freeze_manifest_v1.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
