"""Final 9-call readiness gate for STUDY-012 recovery v2."""
from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from providers.google import GoogleProvider
from providers.nvidia import NvidiaProvider

TARGETS=[
 ("google","gemini-2.5-flash","Return exactly READY_OK and nothing else.","READY_OK"),
 ("nvidia","nvidia/nemotron-3-ultra-550b-a55b","Return exactly READY_OK and nothing else.","READY_OK"),
 ("nvidia","nvidia/nemotron-3-super-120b-a12b","Return exactly VERIFIED and nothing else.","VERIFIED"),
]
def _provider(name):
 return GoogleProvider() if name=="google" else NvidiaProvider()
def _one(provider_name,model,prompt,expected,phase,index):
 r=_provider(provider_name).generate(prompt,model=model,max_tokens=32,temperature=0.0,dry_run=False)
 return {
  "provider":provider_name,"model_id":model,"phase":phase,"index":index,
  "is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==expected),
  "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
  "prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,
  "cost_usd":r.cost_usd,"latency_ms":r.latency_ms,
  "failure":(r.raw_response or {}).get("failure") if not r.is_live else None,
 }
def run():
 rows=[]
 for provider_name,model,prompt,expected in TARGETS:
  rows.append(_one(provider_name,model,prompt,expected,"sequential",1))
  with ThreadPoolExecutor(max_workers=2) as pool:
   fut=[pool.submit(_one,provider_name,model,prompt,expected,"burst2",i) for i in range(1,3)]
   rows.extend(f.result() for f in fut)
 summary={}
 for provider_name,model,_,_ in TARGETS:
  subset=[r for r in rows if r["provider"]==provider_name and r["model_id"]==model]
  summary[f"{provider_name}:{model}"]={
   "calls":len(subset),"live":sum(r["is_live"] for r in subset),
   "semantic_match":sum(r["semantic_match"] for r in subset),
   "failures":[r["failure"] for r in subset if r["failure"]],
  }
 ready=len(rows)==9 and all(r["is_live"] and r["semantic_match"] for r in rows)
 return {"schema_version":"aftergraph.study012.recovery-v2-readiness.v0.1","decision":"READY" if ready else "BLOCKED","calls":len(rows),"rows":rows,"summary":summary}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
