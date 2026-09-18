"""STUDY-012 deterministic analysis. No provider calls."""
from __future__ import annotations
from collections import Counter
def analyze(rows):
 admissible=[r for r in rows if r.get("admissible") is True]
 by=Counter(r["condition"] for r in admissible)
 judge_only=sum(1 for r in admissible if r["condition"]=="J" and r.get("judge_verdict")=="VERIFIED")
 deterministic=sum(1 for r in admissible if r["condition"] in {"D","JD","DI"} and r.get("oracle_verdict")=="VERIFIED")
 independent=sum(1 for r in admissible if r["condition"]=="DI" and r.get("independent_verdict")=="VERIFIED")
 disagreements=sum(1 for r in admissible if r["condition"]=="JD" and r.get("judge_verdict")!=r.get("oracle_verdict"))
 classes={r["r2_class"] for r in admissible if r.get("r2_applicable")}
 covered={r["r2_class"] for r in admissible if r.get("r2_applicable") and r.get("oracle_executed")}
 return {"n":len(admissible),"by_condition":dict(by),"judge_only_verified":judge_only,"deterministically_verified":deterministic,"independently_verified":independent,"judge_oracle_disagreements":disagreements,"applicable_classes":len(classes),"covered_classes":len(covered)}
