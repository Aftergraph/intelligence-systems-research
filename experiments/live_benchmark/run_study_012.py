"""STUDY-012 v0.2 dry-run adapter. Never performs network calls.

The repo already owns a frozen ICT-EXP-001 STUDY-012 workload manifest. This
adapter preserves it and projects its frozen workloads into the new R1/R2
analysis shape rather than overwriting historical evidence.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def dry_run():
 m=json.loads((ROOT/"data/study012_workload_manifest.json").read_text())
 rows=[]
 for w in m["workloads"]:
  r2="revocation" if "Revocation" in w["task_family"] else "adversarial_evidence"
  for condition in ["J","D","JD","DI"]:
   rows.append({"trace_id":f"{w['workload_id']}-{condition}-dry","source_workload_id":w["workload_id"],"r2_class":r2,"r2_applicable":True,"condition":condition,"admissible":True,"oracle_executed":condition!="J","judge_verdict":"FAILED" if condition in {"J","JD"} else None,"oracle_verdict":"FAILED" if condition in {"D","JD","DI"} else None,"independent_verdict":"FAILED" if condition=="DI" else None,"execution_class":"DRY_RUN"})
 return rows
if __name__=="__main__": print(json.dumps(dry_run(),indent=2))
