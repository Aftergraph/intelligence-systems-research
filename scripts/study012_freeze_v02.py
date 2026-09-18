"""STUDY-012 immutable freeze manifest builder/verifier."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
"STUDY-012-GROUNDED-VERIFICATION-TRACE-PREREGISTRATION.md",
"STUDY-012-SAMPLE-POWER-FREEZE.md",
"STUDY-012-AMENDMENT-001-R2-TRACE-EXTENSION.md",
"data/study012_workload_manifest.json",
"data/study012_r2_extension_v01.json",
"data/study012_provider_model_matrix.json",
"src/study012_oracles.py",
"experiments/live_benchmark/run_study_012.py",
"experiments/live_benchmark/study012_analyze.py",
"tests/test_study012_preregistration.py",
"tests/test_study012_oracles.py",
"tests/test_study012_harness.py",
]
def sha256(path: Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
 return {
  "schema_version":"aftergraph.study012.freeze.v0.2",
  "study_id":"STUDY-012",
  "status":"REVIEW_FROZEN_EXECUTION_BLOCKED",
  "files":{p:sha256(ROOT/p) for p in FILES},
  "execution_gate":{
    "network_calls_authorized":False,
    "provider_model_matrix_ready":False,
    "owner_approval_required":True
  }
 }
def verify(manifest):
 expected=build()
 if manifest["files"]!=expected["files"]: return False
 return manifest["execution_gate"]["network_calls_authorized"] is False
if __name__=="__main__":
 out=ROOT/"data/study012_freeze_manifest_v02.json"
 out.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
