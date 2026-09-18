"""Post-run immutable evidence freeze for STUDY-012 recovery-v4."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"data/study012_runs/recovery-v4-live-20260918"
FILES=[
 "data/study012_runs/recovery-v4-live-20260918/observations.jsonl",
 "data/study012_runs/recovery-v4-live-20260918/RUN-SUMMARY.json",
 "data/study012_runs/recovery-v4-live-20260918/POSTRUN-ANALYSIS.json",
 "data/study012_runs/recovery-v4-live-20260918/RESEARCH-METRICS-RECEIPT.json",
 "data/study012_runs/recovery-v4-live-20260918/FROZEN-ANALYZER-CROSSCHECK.json",
 "data/study012_recovery_freeze_manifest_v4.json",
 "experiments/live_benchmark/study012_full_runner_v4.py",
 "experiments/live_benchmark/study012_analyze.py",
 "scripts/study012_postrun_v4.py",
 "tests/test_study012_postrun_v4.py",
 "STUDY-012-RECOVERY-V4-POSTRUN-REPORT.md",
]
RAW_SHA="7530a46da7faa935448f207dd3a276e751a4cc8b38d48585d29764b184fe71bd"
FROZEN_ANALYZER_SHA="94f8f329a8322c622ffb0109d4961d805ce35ed406ce145a4d2234c81a6f7ecd"

def sha(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
 analysis=json.loads((RUN/"POSTRUN-ANALYSIS.json").read_text(encoding="utf-8"))
 return {
  "schema_version":"aftergraph.study012.postrun-freeze.v4",
  "study_id":"STUDY-012",
  "execution_id":"study012-recovery-v4-20260918",
  "execution_source_commit":"0ce31cb4c9b9ad125db9e3ddfd314618aa930bee",
  "status":"CLOSED_EVIDENCE_FROZEN",
  "raw_observations_sha256":sha(ROOT/"data/study012_runs/recovery-v4-live-20260918/observations.jsonl"),
  "frozen_analyzer_sha256":sha(ROOT/"experiments/live_benchmark/study012_analyze.py"),
  "files":{p:sha(ROOT/p) for p in FILES},
  "summary":{
   "observations":analysis["observations"],
   "unique_trace_ids":analysis["unique_trace_ids"],
   "confirmatory_admissibility":analysis["confirmatory_admissibility"],
   "task_provider_failures":analysis["task_provider_failures"],
   "jd_disagreements":analysis["jd_disagreement"]["disagreements"],
   "sentinel_unique_receipts":analysis["sentinel_audit"]["unique_receipts"],
   "hypothesis_dispositions":{k:v["status"] for k,v in analysis["hypothesis_dispositions"].items()},
  },
 }

def verify(manifest):
 expected=build()
 return (
  expected["raw_observations_sha256"]==RAW_SHA
  and expected["frozen_analyzer_sha256"]==FROZEN_ANALYZER_SHA
  and manifest==expected
 )

if __name__=="__main__":
 m=build()
 out=ROOT/"data/study012_recovery_v4_postrun_freeze_manifest.json"
 out.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(out)
