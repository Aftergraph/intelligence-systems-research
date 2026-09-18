"""Create/verify STUDY-012 immutable review manifest."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=["STUDY-012-GROUNDED-VERIFICATION-TRACE-PREREGISTRATION.md","STUDY-012-SAMPLE-POWER-FREEZE.md","data/study012_workload_manifest.json","data/study012_provider_model_matrix.json","src/study012_oracles.py","experiments/live_benchmark/study012_analyze.py","experiments/live_benchmark/run_study_012.py"]
def hashes():
 return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
def write(path=ROOT/"data/study012_freeze_manifest.json"):
 payload={"schema_version":"aftergraph.study012.freeze.v0.1","status":"REVIEW_FROZEN_EXECUTION_BLOCKED","files":hashes()}
 path.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); return payload
if __name__=="__main__": write()
