"""Nine-call NVIDIA tri-model readiness probe for STUDY-012 v3."""
from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from providers.nvidia import NvidiaProvider

TARGETS=[
 ("nvidia/nemotron-3-super-120b-a12b","Return exactly TASK_OK and nothing else.","TASK_OK","task_m1"),
 ("mistralai/mistral-7b-instruct-v0.3","Return exactly TASK_OK and nothing else.","TASK_OK","task_m2"),
 ("google/gemma-3-4b-it","Return exactly VERIFIED and nothing else.","VERIFIED","judge"),
]
def _one(model,prompt,expected,role,phase,index):
 r=NvidiaProvider().generate(prompt,model=model,max_tokens=32,temperature=0.0,dry_run=False)
 return {"model_id":model,"role":role,"phase":phase,"index":index,"is_live":bool(r.is_live),
         "semantic_match":bool(r.is_live and (r.content or "").strip()==expected),
         "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
         "prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,
         "latency_ms":r.latency_ms,"cost_usd":r.cost_usd,
         "failure":(r.raw_response or {}).get("failure") if not r.is_live else None}
def run():
 rows=[]
 for model,prompt,expected,role in TARGETS:
  rows.append(_one(model,prompt,expected,role,"sequential",1))
  with ThreadPoolExecutor(max_workers=2) as pool:
   fs=[pool.submit(_one,model,prompt,expected,role,"burst2",i) for i in range(1,3)]
   rows.extend(f.result() for f in fs)
 summary={}
 for model,_,_,role in TARGETS:
  s=[r for r in rows if r["model_id"]==model]
  summary[role]={"model_id":model,"calls":3,"live":sum(r["is_live"] for r in s),"semantic_match":sum(r["semantic_match"] for r in s),"failures":[r["failure"] for r in s if r["failure"]]}
 ready=len(rows)==9 and all(r["is_live"] and r["semantic_match"] for r in rows)
 return {"schema_version":"aftergraph.study012.nvidia-v3-readiness.v0.1","decision":"READY" if ready else "BLOCKED","calls":len(rows),"rows":rows,"summary":summary}
if __name__=="__main__":print(json.dumps(run(),indent=2,sort_keys=True))
