"""Bounded BytePlus Ark recovery probe for STUDY-012."""
from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from providers.byteplus import BytePlusProvider

MODEL="seed-2-0-lite-260428"
PROMPT="Return exactly BYTEPLUS_READY_OK and nothing else."
EXPECTED="BYTEPLUS_READY_OK"

def _one(phase,index):
 r=BytePlusProvider().generate(PROMPT,model=MODEL,max_tokens=32,temperature=0.0,dry_run=False)
 return {
  "phase":phase,"index":index,"is_live":bool(r.is_live),
  "semantic_match":bool(r.is_live and (r.content or "").strip()==EXPECTED),
  "content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),
  "prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,
  "cost_usd":r.cost_usd,"latency_ms":r.latency_ms,
  "failure":(r.raw_response or {}).get("failure") if not r.is_live else None,
 }
def run():
 rows=[_one("sequential",1)]
 with ThreadPoolExecutor(max_workers=3) as pool:
  fut=[pool.submit(_one,"burst3",i) for i in range(1,4)]
  rows.extend(f.result() for f in fut)
 return {"schema_version":"aftergraph.study012.byteplus-recovery-probe.v0.1","model_id":MODEL,"rows":rows,
         "summary":{"calls":4,"live":sum(r["is_live"] for r in rows),"semantic_match":sum(r["semantic_match"] for r in rows),
                    "failures":[r["failure"] for r in rows if r["failure"]]}}
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
