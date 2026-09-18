"""Deterministic STUDY-012 recovery-v2 allocation. No network calls."""
from __future__ import annotations
import hashlib,json
R2_CLASSES=["stale_state","revocation","contradiction","cross_subject_isolation","constraint_decay","replay","crash_recovery","adversarial_evidence"]
CONDITIONS=["J","D","JD","DI"]
REPLICATES=30
STRATA=[
 ("M1","google","gemini-2.5-flash"),
 ("M2","nvidia","nvidia/nemotron-3-ultra-550b-a55b"),
]
def allocation():
 rows=[]
 for r2 in R2_CLASSES:
  for condition in CONDITIONS:
   for replicate in range(1,REPLICATES+1):
    stratum,provider,model=STRATA[(replicate-1)%2]
    trace_id=f"S12V2-{r2}-{condition}-R{replicate:02d}"
    rows.append({
      "trace_id":trace_id,"r2_class":r2,"condition":condition,"replicate":replicate,
      "stratum":stratum,"provider":provider,"model_id":model,
      "result_partition":f"recovery-v2/{provider}/{model.replace('/','__')}/{r2}/{condition}",
      "seed":int(hashlib.sha256(trace_id.encode()).hexdigest()[:8],16),
    })
 return rows
def summary(rows=None):
 rows=rows or allocation()
 by_provider={}
 for r in rows: by_provider[r["provider"]]=by_provider.get(r["provider"],0)+1
 return {"observations":len(rows),"by_provider":by_provider,"classes":len({r["r2_class"] for r in rows}),"conditions":len({r["condition"] for r in rows}),"replicates_per_class_condition":REPLICATES}
if __name__=="__main__": print(json.dumps({"summary":summary(),"rows":allocation()},indent=2))
