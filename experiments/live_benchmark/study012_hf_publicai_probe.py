from __future__ import annotations
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from providers.hf_publicai import HuggingFacePublicAIProvider,HF_MODEL
PROMPT="Return exactly READY_OK and nothing else.";EXPECTED="READY_OK"
def _one(phase,index):
 r=HuggingFacePublicAIProvider().generate(PROMPT,model=HF_MODEL,max_tokens=16,temperature=0.0,dry_run=False)
 return {"phase":phase,"index":index,"is_live":bool(r.is_live),"semantic_match":bool(r.is_live and (r.content or "").strip()==EXPECTED),"content_sha256":hashlib.sha256((r.content or "").encode()).hexdigest(),"prompt_tokens":r.prompt_tokens,"completion_tokens":r.completion_tokens,"total_tokens":r.total_tokens,"cost_usd":r.cost_usd,"latency_ms":r.latency_ms,"failure":(r.raw_response or {}).get("failure") if not r.is_live else None}
def run():
 rows=[_one("sequential",1)]
 with ThreadPoolExecutor(max_workers=3) as pool:
  fs=[pool.submit(_one,"burst3",i) for i in range(1,4)]
  rows.extend(f.result() for f in fs)
 return {"schema_version":"aftergraph.study012.hf-publicai-probe.v0.1","model_id":HF_MODEL,"rows":rows,"summary":{"calls":4,"live":sum(r["is_live"] for r in rows),"semantic_match":sum(r["semantic_match"] for r in rows),"failures":[r["failure"] for r in rows if r["failure"]]}}
if __name__=="__main__":print(json.dumps(run(),indent=2,sort_keys=True))
