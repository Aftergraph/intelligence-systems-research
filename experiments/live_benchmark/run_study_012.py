"""STUDY-012 v0.2 dry-run adapter. Never performs network calls."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def _row(source_id,r2,condition):
 return {"trace_id":f"{source_id}-{condition}-dry","source_workload_id":source_id,"r2_class":r2,"r2_applicable":True,"condition":condition,"admissible":True,"oracle_executed":condition!="J","judge_verdict":"FAILED" if condition in {"J","JD"} else None,"oracle_verdict":"FAILED" if condition in {"D","JD","DI"} else None,"independent_verdict":"FAILED" if condition=="DI" else None,"execution_class":"DRY_RUN"}
def dry_run():
 parent=json.loads((ROOT/"data/study012_workload_manifest.json").read_text())
 ext=json.loads((ROOT/"data/study012_r2_extension_v01.json").read_text())
 rows=[]
 for w in parent["workloads"]:
  r2="revocation" if "Revocation" in w["task_family"] else "adversarial_evidence"
  for condition in ["J","D","JD","DI"]: rows.append(_row(w["workload_id"],r2,condition))
 for w in ext["workloads"]:
  for condition in ["J","D","JD","DI"]: rows.append(_row(w["id"],w["r2_class"],condition))
 return rows
if __name__=="__main__": print(json.dumps(dry_run(),indent=2))
