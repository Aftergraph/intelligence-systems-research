"""STUDY-012 frozen full-matrix runner.

Live execution requires exact frozen artifacts, explicit full-matrix owner approval,
and a pinned Sentinel checkout. No provider/model substitution is permitted.
"""
from __future__ import annotations
import argparse, hashlib, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from experiments.live_benchmark.study012_admissibility import evaluate as admissibility
from experiments.live_benchmark.study012_matrix_plan import allocation
from experiments.live_benchmark.study012_evaluators import deterministic_exact, parse_judge_observation, canonicalize
from experiments.live_benchmark.study012_sentinel_adapter import verify_research_envelope, verify_checkout
from providers.google import GoogleProvider
from providers.openrouter import OpenRouterProvider

ROOT=Path(__file__).resolve().parents[2]
APPROVAL_REF="OWNER-FULL-MATRIX-20260918-CHAT-CONTINUE"
MAX_API_CALLS=2880
HARD_COST_USD=4.0
MAX_ATTEMPTS=2
JUDGE_MODEL="z-ai/glm-5.2"

PRICE={
 ("openrouter","google/gemma-4-31b-it"):(0.09,0.34),
 ("google","gemini-2.5-flash"):(0.30,2.50),
 ("openrouter",JUDGE_MODEL):(0.4875,1.56),
}

def canonical_hash(obj:Any)->str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def text_hash(s:str)->str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def estimate_cost(provider:str,model:str,prompt_tokens:int,completion_tokens:int,reported:float|None)->float:
    rates=PRICE[(provider,model)]
    estimated=(prompt_tokens*rates[0]+completion_tokens*rates[1])/1_000_000
    return max(float(reported or 0.0),estimated)

def load_fixtures()->dict[str,dict[str,Any]]:
    obj=json.loads((ROOT/"data/study012_r2_extension_v03.json").read_text(encoding="utf-8"))
    out={w["r2_class"]:w for w in obj["workloads"]}
    if len(out)!=8: raise RuntimeError("fixture_class_count_not_8")
    return out

def provider(name:str):
    if name=="google": return GoogleProvider()
    if name=="openrouter": return OpenRouterProvider()
    raise RuntimeError("provider_not_frozen")

class Budget:
    def __init__(self):
        self.lock=threading.Lock(); self.api_calls=0; self.cost=0.0
    def before_call(self):
        with self.lock:
            if self.api_calls>=MAX_API_CALLS: raise RuntimeError("api_call_ceiling_reached")
            if self.cost>=HARD_COST_USD: raise RuntimeError("cost_ceiling_reached")
            self.api_calls+=1
    def add_cost(self,cost:float):
        with self.lock:
            self.cost+=cost
            if self.cost>HARD_COST_USD: raise RuntimeError("cost_ceiling_exceeded")
    def snapshot(self):
        with self.lock:return {"api_calls":self.api_calls,"cost_usd":round(self.cost,8)}

def call_model(budget:Budget,provider_name:str,model_id:str,prompt:str,max_tokens:int)->tuple[Any,float,int]:
    last=None
    for attempt in range(1,MAX_ATTEMPTS+1):
        budget.before_call()
        p=provider(provider_name)
        r=p.generate(prompt,model=model_id,max_tokens=max_tokens,temperature=0.0,dry_run=False)
        cost=estimate_cost(provider_name,model_id,r.prompt_tokens,r.completion_tokens,r.cost_usd)
        budget.add_cost(cost)
        last=r
        if r.is_live:
            return r,cost,attempt
    return last,cost,MAX_ATTEMPTS

def judge_prompt(workload:dict[str,Any],response_text:str)->str:
    expected=workload["response_contract"]["expected"]
    return (
      "You are an observational evaluator. Compare candidate output against the exact expected token. "
      "Return exactly VERIFIED if they match after trimming whitespace; otherwise return exactly FAILED. "
      "If the evidence is malformed, return exactly ABSTAIN.\n"
      f"EXPECTED: {expected}\nCANDIDATE: {response_text}"
    )

def sentinel_envelope(row:dict[str,Any],workload:dict[str,Any],response_text:str)->dict[str,Any]:
    body={"responseText":response_text,"responseSha256":text_hash(response_text),"provider":row["provider"],"modelId":row["model_id"]}
    criterion=workload["response_contract"]
    return {
      "schema":"aftergraph.research-evidence/1.0",
      "subject":{
        "studyId":"STUDY-012","executionId":"study012-full-matrix-20260918",
        "traceId":row["trace_id"],"workloadId":workload["id"],"condition":row["condition"],
        "executorRef":"runtime:study012-full-runner","missionId":"research:"+row["trace_id"],
      },
      "evidence":{"body":body,"digestSha256":canonical_hash(body),"observedAt":"2026-09-18T18:00:00Z"},
      "criterion":{**criterion,"acceptanceCriteriaHash":canonical_hash(criterion)},
    }

def execute_one(row:dict[str,Any],workload:dict[str,Any],budget:Budget,sentinel_dir:Path)->dict[str,Any]:
    started=time.time()
    response,task_cost,task_attempts=call_model(budget,row["provider"],row["model_id"],workload["prompt"],256)
    execution_class="LIVE_VALID" if response and response.is_live else "LIVE_PROVIDER_FAILURE"
    response_text=(response.content or "") if response else ""
    det=None; judge=None; sentinel=None
    if row["condition"] in {"D","JD","DI"} and response and response.is_live:
        det=deterministic_exact(response_text,workload)
    judge_cost=0.0; judge_attempts=0
    if row["condition"] in {"J","JD"} and response and response.is_live:
        jr,jc,ja=call_model(budget,"openrouter",JUDGE_MODEL,judge_prompt(workload,response_text),32)
        judge_cost=jc; judge_attempts=ja
        judge=parse_judge_observation(jr.content if jr and jr.is_live else "ABSTAIN")
        judge["is_live"]=bool(jr and jr.is_live)
        judge["response_hash"]=text_hash(jr.content if jr else "")
    independent_receipt=None
    if row["condition"]=="DI" and response and response.is_live:
        sentinel=verify_research_envelope(sentinel_dir,sentinel_envelope(row,workload,response_text))
        rec=sentinel.get("receipt") if isinstance(sentinel,dict) else None
        if rec:
            independent_receipt={
              "result":"passed" if sentinel.get("verdict")=="VERIFIED" else "failed",
              "verifier_id":rec.get("verifierRef"),
              "evidence_ref":rec.get("receiptId"),
              "verified_at":rec.get("verifiedAt"),
            }
    canonical=canonicalize(row["condition"],deterministic=det,judge=judge,independent_receipt=independent_receipt)
    return {
      **row,
      "study_id":"STUDY-012","execution_id":"study012-full-matrix-20260918",
      "source_workload_id":workload["id"],"workload_hash":canonical_hash(workload),
      "execution_class":execution_class,
      "response_hash":text_hash(response_text),"response_text":response_text,
      "task_prompt_tokens":getattr(response,"prompt_tokens",0),"task_completion_tokens":getattr(response,"completion_tokens",0),
      "task_attempts":task_attempts,"task_cost_usd":task_cost,
      "deterministic":det,"judge":judge,"judge_attempts":judge_attempts,"judge_cost_usd":judge_cost,
      "sentinel":sentinel,"independent_receipt":independent_receipt,
      "canonical":canonical,"elapsed_ms":round((time.time()-started)*1000,3),
    }

def append_jsonl(path:Path,obj:dict[str,Any],lock:threading.Lock):
    path.parent.mkdir(parents=True,exist_ok=True)
    line=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    with lock:
        with path.open("a",encoding="utf-8",newline="\n") as fh: fh.write(line+"\n")

def completed(path:Path)->set[str]:
    if not path.exists():return set()
    out=set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip(): out.add(json.loads(line)["trace_id"])
    return out

def preflight(sentinel_dir:Path)->dict[str,Any]:
    a=admissibility()
    ok,reason=verify_checkout(sentinel_dir)
    approval=json.loads((ROOT/"data/study012_owner_approval_full_matrix_20260918.json").read_text(encoding="utf-8"))
    reasons=list(a["reasons"])
    if a["decision"]!="READY_FOR_OWNER_APPROVAL": reasons.append("admissibility_not_ready")
    if not ok: reasons.append(reason)
    if approval.get("approval_ref")!=APPROVAL_REF or approval.get("scope")!="FULL_FROZEN_MATRIX_ONLY": reasons.append("owner_approval_invalid")
    if approval.get("hard_cost_stop_usd")!=HARD_COST_USD: reasons.append("cost_cap_approval_mismatch")
    return {"decision":"READY_TO_EXECUTE" if not reasons else "BLOCKED","reasons":reasons,"network_calls_performed":0}

def run(out_dir:Path,sentinel_dir:Path,workers:int=12)->dict[str,Any]:
    gate=preflight(sentinel_dir)
    if gate["decision"]!="READY_TO_EXECUTE": return gate
    fixtures=load_fixtures(); plan=allocation(); observations=out_dir/"observations.jsonl"
    done=completed(observations); pending=[r for r in plan if r["trace_id"] not in done]
    budget=Budget(); lock=threading.Lock(); failures=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut={pool.submit(execute_one,row,fixtures[row["r2_class"]],budget,sentinel_dir):row for row in pending}
        for f in as_completed(fut):
            row=fut[f]
            try: append_jsonl(observations,f.result(),lock)
            except Exception as exc:
                failures.append({"trace_id":row["trace_id"],"error":type(exc).__name__+":"+str(exc)})
                if "ceiling" in str(exc): break
    rows=[]
    if observations.exists():
        rows=[json.loads(x) for x in observations.read_text(encoding="utf-8").splitlines() if x.strip()]
    result={
      "decision":"COMPLETED" if len(rows)==960 and not failures else "PARTIAL",
      "observations":len(rows),"unique_traces":len({r["trace_id"] for r in rows}),
      "budget":budget.snapshot(),"failures":failures,
      "canonical_counts":{},
      "execution_class_counts":{},
    }
    for r in rows:
        cv=r.get("canonical",{}).get("canonical_verdict","MISSING"); result["canonical_counts"][cv]=result["canonical_counts"].get(cv,0)+1
        ec=r.get("execution_class","MISSING"); result["execution_class_counts"][ec]=result["execution_class_counts"].get(ec,0)+1
    (out_dir/"RUN-SUMMARY.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--out-dir",required=True); ap.add_argument("--sentinel-dir",required=True); ap.add_argument("--workers",type=int,default=12)
    args=ap.parse_args()
    print(json.dumps(run(Path(args.out_dir),Path(args.sentinel_dir),args.workers),indent=2))
