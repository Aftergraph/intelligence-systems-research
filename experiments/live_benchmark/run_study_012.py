"""STUDY-012 dry-run harness. Synthetic only; never performs network calls."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def dry_run():
 m=json.loads((ROOT/"data/study012_workload_manifest.json").read_text())
 rows=[]
 for w in m["workload_classes"]:
  for condition in ["J","D","JD","DI"]:
   rows.append({"trace_id":f"{w['id']}-dry","r2_class":w["r2_class"],"r2_applicable":w["applicable"],"condition":condition,"admissible":True,"oracle_executed":condition!="J","judge_verdict":"FAILED" if condition in {"J","JD"} else None,"oracle_verdict":"FAILED" if condition in {"D","JD","DI"} else None,"independent_verdict":"FAILED" if condition=="DI" else None,"execution_class":"DRY_RUN"})
 return rows
if __name__=="__main__": print(json.dumps(dry_run(),indent=2))
