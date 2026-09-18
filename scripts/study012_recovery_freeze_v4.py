"""Immutable freeze builder for STUDY-012 recovery v4."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=[
 "STUDY-012-AMENDMENT-007-LOCAL-OLLAMA-NVIDIA-RECOVERY-V4.md",
 "data/study012_r2_extension_v03.json",
 "data/study012_provider_model_matrix_v4.json",
 "data/study012_ollama_local_binding_v01.json",
 "data/study012_recovery_v4_readiness_20260918.json",
 "data/study012_owner_approval_recovery_v4_readiness_20260918.json",
 "data/study012_owner_approval_recovery_v4_full_20260918.json",
 "data/study012_novita_sandbox_fabric_v01.json",
 "data/study012_novita_sandbox_resume_proof_20260918.json",
 "data/study012_sentinel_binding_v01.json",
 "data/study012_works_verification_binding_v01.json",
 "providers/ollama_local.py",
 "providers/nvidia.py",
 "providers/http_failure.py",
 "experiments/live_benchmark/study012_matrix_plan_v4.py",
 "experiments/live_benchmark/study012_recovery_v4_readiness.py",
 "experiments/live_benchmark/study012_full_runner_v4.py",
 "experiments/live_benchmark/study012_evaluators.py",
 "experiments/live_benchmark/study012_sentinel_adapter.py",
 "src/study012_oracles.py",
 "tests/test_study012_matrix_plan_v4.py",
 "tests/test_study012_recovery_v4.py",
 "tests/test_study012_full_runner_v4.py",
 "tests/test_ollama_local_provider.py",
 "tests/test_direct_recovery_providers.py",
 "tests/test_study012_evaluators.py",
 "tests/test_study012_sentinel_adapter.py",
]

def sha(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
 readiness=json.loads((ROOT/"data/study012_recovery_v4_readiness_20260918.json").read_text(encoding="utf-8"))
 approval=json.loads((ROOT/"data/study012_owner_approval_recovery_v4_full_20260918.json").read_text(encoding="utf-8"))
 return {
  "schema_version":"aftergraph.study012.recovery-freeze.v4",
  "study_id":"STUDY-012",
  "execution_id":"study012-recovery-v4-20260918",
  "pooling_with_prior_runs":False,
  "status":"FROZEN_PENDING_EXPLICIT_OWNER_GRANT",
  "files":{p:sha(ROOT/p) for p in FILES},
  "execution_gate":{
   "readiness_decision":readiness.get("decision"),
   "readiness_calls":readiness.get("calls"),
   "owner_status":approval.get("status"),
   "network_calls_authorized":approval.get("network_calls_authorized") is True,
   "max_total_model_calls":(approval.get("authorization_requirements") or {}).get("max_total_model_calls"),
   "hard_cost_stop_usd":(approval.get("authorization_requirements") or {}).get("hard_cost_stop_usd"),
   "provider_substitution_allowed":False,
  },
 }

def verify(manifest):
 expected=build()
 return manifest.get("files")==expected["files"] and manifest.get("execution_gate")==expected["execution_gate"]

if __name__=="__main__":
 out=ROOT/"data/study012_recovery_freeze_manifest_v4.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
