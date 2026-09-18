"""Sequential retry-bounded readiness for STUDY-012 v3."""
from __future__ import annotations
import hashlib,json,time
from providers.nvidia import NvidiaProvider

TARGETS=[
 ("task_m1","nvidia/nemotron-3-ultra-550b-a55b","Return exactly TASK_OK and nothing else.","TASK_OK"),
 ("task_m2","nvidia/nemotron-3-nano-omni-30b-a3b-reasoning","Return exactly TASK_OK and nothing else.","TASK_OK"),
 ("judge","nvidia/nemotron-3-super-120b-a12b","Return exactly VERIFIED and nothing else.","VERIFIED"),
]
RETRYABLE={408,429,500,502,503,504}
MAX_ATTEMPTS=2

def _failure(r):
 f=(r.raw_response or {}).get("failure") if not r.is_live else None
 return f if isinstance(f,dict) else None

def _one(role,model,prompt,expected,index):
 attempts=[]
 for attempt in range(1,MAX_ATTEMPTS+1):
  r=NvidiaProvider().generate(prompt,model=model,max_tokens=32,temperature=0.0,dry_run=False)
  f=_failure(r)
  rec={"attempt":attempt,"is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==expected),"content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),"latency_ms":r.latency_ms,"failure":f}
  attempts.append(rec)
  if rec["is_live"] and rec["semantic_match"]:break
  status=(f or {}).get("http_status")
  cat=(f or {}).get("category")
  if not (status in RETRYABLE or cat in {"URL_ERROR","TIMEOUT"}):break
  if attempt<MAX_ATTEMPTS:time.sleep(attempt)
 return {"role":role,"model_id":model,"index":index,"attempts":attempts,"final_live":attempts[-1]["is_live"],"final_semantic_match":attempts[-1]["semantic_match"]}

def run():
 rows=[]
 for role,model,prompt,expected in TARGETS:
  for i in range(1,4):
   rows.append(_one(role,model,prompt,expected,i))
 summary={}
 for role,model,_,_ in TARGETS:
  s=[r for r in rows if r["role"]==role]
  summary[role]={"model_id":model,"observations":3,"ready":sum(r["final_live"] and r["final_semantic_match"] for r in s),"attempts_total":sum(len(r["attempts"]) for r in s)}
 ready=len(rows)==9 and all(r["final_live"] and r["final_semantic_match"] for r in rows)
 return {"schema_version":"aftergraph.study012.v3-readiness.v0.1","decision":"READY" if ready else "BLOCKED","observations":9,"rows":rows,"summary":summary}
if __name__=="__main__":print(json.dumps(run(),indent=2,sort_keys=True))
