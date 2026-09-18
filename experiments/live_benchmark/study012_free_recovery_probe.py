"""Bounded credit-independent recovery probes for STUDY-012."""
from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from providers.openrouter import OpenRouterProvider

TARGETS=[
 ("google/gemma-4-31b-it:free","Return exactly FORENSIC_OK and nothing else.","FORENSIC_OK"),
 ("thinkingmachines/inkling-small:free","Return exactly VERIFIED and nothing else.","VERIFIED"),
]

def _one(model,prompt,expected,phase,index):
 r=OpenRouterProvider().generate(prompt,model=model,max_tokens=16,temperature=0.0,dry_run=False)
 return {
  "model_id":model,"phase":phase,"index":index,"is_live":bool(r.is_live),
  "semantic_match":bool(r.is_live and (r.content or "").strip()==expected),
  "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
  "prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,
  "cost_usd":r.cost_usd,"latency_ms":r.latency_ms,
  "failure":(r.raw_response or {}).get("failure") if not r.is_live else None,
 }
def run():
 rows=[]
 for model,prompt,expected in TARGETS:
  rows.append(_one(model,prompt,expected,"sequential",1))
  with ThreadPoolExecutor(max_workers=3) as pool:
   fut=[pool.submit(_one,model,prompt,expected,"burst3",i) for i in range(1,4)]
   rows.extend(f.result() for f in fut)
 summary={}
 for model,_,_ in TARGETS:
  s=[r for r in rows if r["model_id"]==model]
  summary[model]={
   "calls":len(s),"live":sum(r["is_live"] for r in s),
   "semantic_match":sum(r["semantic_match"] for r in s),
   "sequential_live":sum(r["is_live"] for r in s if r["phase"]=="sequential"),
   "burst_live":sum(r["is_live"] for r in s if r["phase"]=="burst3"),
   "failures":[r["failure"] for r in s if r["failure"]],
  }
 return {"schema_version":"aftergraph.study012.free-recovery-probe.v0.1","rows":rows,"summary":summary}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
