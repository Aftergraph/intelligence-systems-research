"""Immutable freeze builder for STUDY-012 cross-model v3."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 "STUDY-012-AMENDMENT-006-NOVITA-NVIDIA-CROSS-MODEL-V3.md",
 "data/study012_v3_execution_plan_v01.json",
 "data/study012_provider_model_matrix_v3.json",
 "data/study012_v3_readiness_20260918.json",
 "data/study012_novita_sandbox_fabric_v01.json",
 "data/study012_novita_sandbox_resume_proof_20260918.json",
 "data/study012_r2_extension_v03.json",
 "data/study012_evaluator_bindings_v01.json",
 "data/study012_sentinel_binding_v01.json",
 "data/study012_works_verification_binding_v01.json",
 "experiments/live_benchmark/study012_matrix_plan_v3.py",
 "experiments/live_benchmark/study012_v3_readiness.py",
 "experiments/live_benchmark/study012_novita_sandbox_fabric.py",
 "experiments/live_benchmark/study012_novita_sandbox_resume_proof.py",
 "providers/nvidia.py",
 "src/study012_oracles.py",
 "tests/test_study012_v3_readiness.py",
 "tests/test_study012_novita_sandbox_fabric.py",
]
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
 readiness=json.loads((ROOT/"data/study012_v3_readiness_20260918.json").read_text(encoding="utf-8"))
 resume=json.loads((ROOT/"data/study012_novita_sandbox_resume_proof_20260918.json").read_text(encoding="utf-8"))
 plan=json.loads((ROOT/"data/study012_v3_execution_plan_v01.json").read_text(encoding="utf-8"))
 return {
  "schema_version":"aftergraph.study012.v3-freeze.v0.1",
  "study_id":"STUDY-012",
  "execution_id":"study012-cross-model-v3-20260918",
  "status":"FROZEN_READY_FOR_OWNER_APPROVAL",
  "files":{p:sha(ROOT/p) for p in FILES},
  "gates":{
   "readiness_decision":readiness.get("decision"),
   "readiness_observations":readiness.get("observations"),
   "sandbox_resume_complete":resume.get("complete"),
   "sandbox_resume_different_sandboxes":resume.get("different_sandboxes"),
   "provider_independence_claim_allowed":plan["claim_scope"]["provider_independence_claim_allowed"],
   "pooling_with_prior_runs":plan["pooling_with_prior_runs"],
   "full_run_owner_approval_required":plan["full_run_owner_approval_required"],
  }
 }
def verify(m):
 e=build()
 return m.get("files")==e["files"] and m.get("gates")==e["gates"]
if __name__=="__main__":
 out=ROOT/"data/study012_v3_freeze_manifest_v01.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
