"""STUDY-012 immutable freeze manifest builder/verifier."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
"STUDY-012-GROUNDED-VERIFICATION-TRACE-PREREGISTRATION.md",
"STUDY-012-SAMPLE-POWER-FREEZE.md",
"STUDY-012-AMENDMENT-001-R2-TRACE-EXTENSION.md",
"STUDY-012-AMENDMENT-002-PROVIDER-STRATUM.md",
"tests/test_study012_works_verification_bridge.py",
"tests/test_study012_sentinel_adapter.py",
"tests/test_study012_evaluators.py",
"tests/test_study012_matrix_admissibility.py",
"experiments/live_benchmark/study012_works_verification_bridge.py",
"experiments/live_benchmark/study012_sentinel_adapter.py",
"experiments/live_benchmark/study012_evaluators.py",
"experiments/live_benchmark/study012_admissibility.py",
"experiments/live_benchmark/study012_matrix_plan.py",
"data/study012_works_verification_binding_v01.json",
"data/study012_sentinel_binding_v01.json",
"data/study012_execution_budget_v01.json",
"data/study012_evaluator_bindings_v01.json",
"data/study012_r2_extension_v02.json",
"STUDY-012-AMENDMENT-003-EXECUTION-ADMISSIBILITY.md",
"data/study012_workload_manifest.json",
"data/study012_r2_extension_v01.json",
"data/study012_provider_model_matrix.json",
"data/study012_provider_readiness_20260918.json",
"providers/google.py",
"providers/stratum_resolver.py",
"src/study012_oracles.py",
"experiments/live_benchmark/run_study_012.py",
"experiments/live_benchmark/study012_analyze.py",
"tests/test_study012_preregistration.py",
"tests/test_study012_oracles.py",
"tests/test_study012_harness.py",
"tests/test_study012_provider_strata.py",
"tests/test_google_provider.py",
"tests/test_openrouter_provider.py",
"tests/test_study012_live_runner.py",
"providers/openrouter.py",
"experiments/live_benchmark/study012_live_runner.py",
"experiments/live_benchmark/study012_execution.py",
"experiments/live_benchmark/study012_preflight.py",
"tests/test_study012_execution_package.py",
"data/study012_execution_manifest_v1.json",
"tests/test_study012_canary_audit.py",
"data/study012_runs/canary-20260918/CANARY-AUDIT.json",
"data/study012_runs/canary-20260918/GOOGLE-DIAGNOSIS.json",
"data/study012_runs/canary-20260918/openrouter/receipts.jsonl",
"data/study012_runs/canary-20260918/google/receipts.jsonl",
"data/study012_owner_approval_20260918.json",
"tests/test_study012_google_retry_audit.py",
"data/study012_runs/canary-google-retry-20260918/GOOGLE-RETRY-AUDIT.json",
"data/study012_runs/canary-google-retry-20260918/receipts.jsonl",
"data/study012_owner_approval_google_retry_20260918.json",
]
def sha256(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
 return {
  "schema_version":"aftergraph.study012.freeze.v0.3",
  "study_id":"STUDY-012",
  "status":"PROVIDER_FROZEN_EXECUTION_BLOCKED_OWNER_GATE",
  "files":{p:sha256(ROOT/p) for p in FILES},
  "execution_gate":{
    "network_calls_authorized":False,
    "provider_model_matrix_ready":True,
    "owner_approval_required":True
  }
 }
def verify(manifest):
 expected=build()
 return manifest.get("files")==expected["files"] and manifest.get("execution_gate",{}).get("network_calls_authorized") is False
if __name__=="__main__":
 out=ROOT/"data/study012_freeze_manifest_v02.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
