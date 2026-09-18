"""STUDY-012 provider-recovery replication v2 full runner.

This execution is independent from the provider-confounded v1 run. No pooling,
provider substitution, or silent model fallback is permitted.
"""
from __future__ import annotations
import argparse,hashlib,json,os,threading,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from experiments.live_benchmark.study012_matrix_plan_v2 import allocation
from experiments.live_benchmark.study012_evaluators import deterministic_exact,parse_judge_observation,canonicalize
from experiments.live_benchmark.study012_sentinel_adapter import verify_checkout,verify_research_envelope
from providers.google import GoogleProvider
from providers.nvidia import NvidiaProvider
from scripts.study012_recovery_freeze import verify as verify_recovery_freeze

ROOT=Path(__file__).resolve().parents[2]
EXECUTION_ID="study012-recovery-v2-20260918"
APPROVAL_REF="OWNER-RECOVERY-V2-FULL-MATRIX-20260918-CHAT-RUN"
JUDGE_MODEL="nvidia/nemotron-3-super-120b-a12b"
MAX_ATTEMPTS=2
MAX_API_CALLS=2880
HARD_COST_USD=4.0
GATES={"google":threading.BoundedSemaphore(2),"nvidia":threading.BoundedSemaphore(2)}
RETRYABLE_HTTP={408,429,500,502,503,504}

def canonical_hash(obj:Any)->str:
 raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
 return hashlib.sha256(raw).hexdigest()

def text_hash(text:str)->str:
 return hashlib.sha256((text or "").encode()).hexdigest()

def load_fixtures()->dict[str,dict[str,Any]]:
 obj=json.loads((ROOT/"data/study012_r2_extension_v03.json").read_text(encoding="utf-8"))
 out={w["r2_class"]:w for w in obj["workloads"]}
 if len(out)!=8: raise RuntimeError("fixture_class_count_not_8")
 return out

def failure_provenance(response)->dict[str,Any]|None:
 if not response or response.is_live:return None
 f=(response.raw_response or {}).get("failure")
 return f if isinstance(f,dict) else {"category":"UNKNOWN"}

def retryable(response)->bool:
 f=failure_provenance(response) or {}
 return f.get("category") in {"URL_ERROR","TIMEOUT"} or f.get("http_status") in RETRYABLE_HTTP

def retry_delay(response,attempt:int)->float:
 f=failure_provenance(response) or {}; h=f.get("headers") or {}
 try:
  v=float(h.get("retry-after"))
  if 0<=v<=30:return v
 except Exception:pass
 return float(attempt)

def provider(name:str):
 if name=="google":return GoogleProvider()
 if name=="nvidia":return NvidiaProvider()
 raise RuntimeError("unfrozen_provider")

def estimate_cost(provider_name:str,model_id:str,prompt_tokens:int,completion_tokens:int,reported:float|None)->float:
 if provider_name=="google":
  est=(prompt_tokens*0.30+completion_tokens*2.50)/1_000_000
  return max(float(reported or 0.0),est)
 if provider_name=="nvidia":
  return max(float(reported or 0.0),0.0)
 raise RuntimeError("pricing_missing")

class Budget:
 def __init__(self,api_calls:int=0,cost:float=0.0):
  self.lock=threading.Lock();self.api_calls=api_calls;self.cost=cost
 def before_call(self):
  with self.lock:
   if self.api_calls>=MAX_API_CALLS:raise RuntimeError("api_call_ceiling_reached")
   if self.cost>=HARD_COST_USD:raise RuntimeError("cost_ceiling_reached")
   self.api_calls+=1
 def add(self,cost:float):
  with self.lock:
   self.cost+=cost
   if self.cost>HARD_COST_USD:raise RuntimeError("cost_ceiling_exceeded")
 def snapshot(self):
  with self.lock:return {"api_calls":self.api_calls,"cost_usd":round(self.cost,8)}

def call_model(budget:Budget,provider_name:str,model_id:str,prompt:str,max_tokens:int):
 last=None;total_cost=0.0
 for attempt in range(1,MAX_ATTEMPTS+1):
  budget.before_call();p=provider(provider_name)
  with GATES[provider_name]:
   r=p.generate(prompt,model=model_id,max_tokens=max_tokens,temperature=0.0,dry_run=False)
  cost=estimate_cost(provider_name,model_id,r.prompt_tokens,r.completion_tokens,r.cost_usd)
  budget.add(cost);total_cost+=cost;last=r
  if r.is_live:return r,total_cost,attempt
  if not retryable(r):break
  if attempt<MAX_ATTEMPTS:time.sleep(retry_delay(r,attempt))
 return last,total_cost,attempt

def judge_prompt(workload,response_text):
 expected=workload["response_contract"]["expected"]
 return (
  "You are an observational evaluator. Compare candidate output with the exact expected token. "
  "Return exactly VERIFIED if they match after trimming whitespace, FAILED if they do not, "
  "or ABSTAIN if the evidence is malformed.\n"
  f"EXPECTED: {expected}\nCANDIDATE: {response_text}"
 )

def sentinel_envelope(row,workload,response_text):
 body={"responseText":response_text,"responseSha256":text_hash(response_text),"provider":row["provider"],"modelId":row["model_id"]}
 criterion=workload["response_contract"]
 return {
  "schema":"aftergraph.research-evidence/1.0",
  "subject":{"studyId":"STUDY-012","executionId":EXECUTION_ID,"traceId":row["trace_id"],"workloadId":workload["id"],
             "condition":row["condition"],"executorRef":"runtime:study012-recovery-v2","missionId":"research:"+row["trace_id"]},
  "evidence":{"body":body,"digestSha256":canonical_hash(body),"observedAt":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")},
  "criterion":{**criterion,"acceptanceCriteriaHash":canonical_hash(criterion)}
 }

def execute_one(row,workload,budget,sentinel_dir):
 started=time.time()
 response,task_cost,task_attempts=call_model(budget,row["provider"],row["model_id"],workload["prompt"],256)
 live=bool(response and response.is_live); response_text=(response.content or "") if response else ""
 execution_class="LIVE_VALID" if live else "LIVE_PROVIDER_FAILURE"
 det=None;judge=None;sentinel=None;independent=None
 if row["condition"] in {"D","JD","DI"} and live:
  det=deterministic_exact(response_text,workload)
 judge_attempts=0;judge_cost=0.0
 if row["condition"] in {"J","JD"} and live:
  jr,judge_cost,judge_attempts=call_model(budget,"nvidia",JUDGE_MODEL,judge_prompt(workload,response_text),32)
  judge=parse_judge_observation(jr.content if jr and jr.is_live else "ABSTAIN")
  judge.update({"is_live":bool(jr and jr.is_live),"response_text":jr.content if jr else "",
                "response_hash":text_hash(jr.content if jr else ""),"failure_provenance":failure_provenance(jr)})
 if row["condition"]=="DI" and live:
  sentinel=verify_research_envelope(sentinel_dir,sentinel_envelope(row,workload,response_text))
  rec=sentinel.get("receipt") if isinstance(sentinel,dict) else None
  if rec:
   independent={"result":"passed" if sentinel.get("verdict")=="VERIFIED" else "failed",
                "verifier_id":rec.get("verifierRef"),"evidence_ref":rec.get("receiptId"),"verified_at":rec.get("verifiedAt")}
 canonical=canonicalize(row["condition"],deterministic=det,judge=judge,independent_receipt=independent)
 return {**row,"study_id":"STUDY-012","execution_id":EXECUTION_ID,"parent_execution_id":"study012-full-matrix-20260918",
         "pooling_with_parent":False,"source_workload_id":workload["id"],"workload_hash":canonical_hash(workload),
         "execution_class":execution_class,"response_text":response_text,"response_hash":text_hash(response_text),
         "task_prompt_tokens":getattr(response,"prompt_tokens",0),"task_completion_tokens":getattr(response,"completion_tokens",0),
         "task_attempts":task_attempts,"task_cost_usd":task_cost,"task_failure_provenance":failure_provenance(response),
         "deterministic":det,"judge":judge,"judge_attempts":judge_attempts,"judge_cost_usd":judge_cost,
         "sentinel":sentinel,"independent_receipt":independent,"canonical":canonical,
         "elapsed_ms":round((time.time()-started)*1000,3)}

def append_jsonl(path,obj,lock):
 path.parent.mkdir(parents=True,exist_ok=True)
 line=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)
 with lock:
  with path.open("a",encoding="utf-8",newline="\n") as fh:fh.write(line+"\n")

def read_rows(path):
 if not path.exists():return []
 return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def preflight(sentinel_dir:Path):
 reasons=[]
 freeze_path=ROOT/"data/study012_recovery_freeze_manifest_v1.json"
 if not freeze_path.exists():
  reasons.append("recovery_freeze_missing")
 else:
  try:
   freeze=json.loads(freeze_path.read_text(encoding="utf-8"))
   if not verify_recovery_freeze(freeze):reasons.append("recovery_freeze_drift")
  except Exception:
   reasons.append("recovery_freeze_invalid")
 readiness=json.loads((ROOT/"data/study012_recovery_v2_readiness_20260918.json").read_text(encoding="utf-8"))
 approval=json.loads((ROOT/"data/study012_owner_approval_recovery_v2_full_20260918.json").read_text(encoding="utf-8"))
 matrix=json.loads((ROOT/"data/study012_provider_model_matrix_v2.json").read_text(encoding="utf-8"))
 if readiness.get("decision")!="READY" or readiness.get("calls")!=9:reasons.append("readiness_not_ready")
 if not all(r.get("is_live") and r.get("semantic_match") for r in readiness.get("rows",[])):reasons.append("readiness_row_failure")
 if approval.get("approval_ref")!=APPROVAL_REF or approval.get("scope")!="RECOVERY_V2_FULL_FROZEN_MATRIX_ONLY":reasons.append("owner_approval_invalid")
 if approval.get("hard_cost_stop_usd")!=HARD_COST_USD:reasons.append("cost_cap_mismatch")
 if matrix.get("substitution_allowed") is not False:reasons.append("substitution_not_fail_closed")
 ok,reason=verify_checkout(sentinel_dir)
 if not ok:reasons.append(reason)
 if not os.environ.get("GOOGLE_API_KEY"):reasons.append("google_credential_missing")
 if not os.environ.get("NVIDIA_API_KEY"):reasons.append("nvidia_credential_missing")
 return {"decision":"READY_TO_EXECUTE" if not reasons else "BLOCKED","reasons":reasons,"network_calls_performed":0}

def prior_accounting(rows):
 calls=sum(int(r.get("task_attempts") or 0)+int(r.get("judge_attempts") or 0) for r in rows)
 cost=sum(float(r.get("task_cost_usd") or 0)+float(r.get("judge_cost_usd") or 0) for r in rows)
 return calls,cost

def run(out_dir:Path,sentinel_dir:Path,workers:int=4):
 gate=preflight(sentinel_dir)
 if gate["decision"]!="READY_TO_EXECUTE":return gate
 fixtures=load_fixtures();plan=allocation();obs=out_dir/"observations.jsonl"
 rows=read_rows(obs);done={r["trace_id"] for r in rows};pending=[r for r in plan if r["trace_id"] not in done]
 calls,cost=prior_accounting(rows);budget=Budget(calls,cost);lock=threading.Lock();failures=[]
 with ThreadPoolExecutor(max_workers=workers) as pool:
  futures={pool.submit(execute_one,row,fixtures[row["r2_class"]],budget,sentinel_dir):row for row in pending}
  for future in as_completed(futures):
   row=futures[future]
   try:append_jsonl(obs,future.result(),lock)
   except Exception as exc:
    failures.append({"trace_id":row["trace_id"],"error":type(exc).__name__+":"+str(exc)})
    if "ceiling" in str(exc):break
 rows=read_rows(obs)
 result={"decision":"COMPLETED" if len(rows)==960 and len({r["trace_id"] for r in rows})==960 and not failures else "PARTIAL",
         "observations":len(rows),"unique_traces":len({r["trace_id"] for r in rows}),"budget":budget.snapshot(),"failures":failures,
         "execution_class_counts":{},"canonical_counts":{}}
 for r in rows:
  e=r.get("execution_class","MISSING");result["execution_class_counts"][e]=result["execution_class_counts"].get(e,0)+1
  v=(r.get("canonical") or {}).get("canonical_verdict","MISSING");result["canonical_counts"][v]=result["canonical_counts"].get(v,0)+1
 out_dir.mkdir(parents=True,exist_ok=True)
 (out_dir/"RUN-SUMMARY.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 return result

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--out-dir",required=True);ap.add_argument("--sentinel-dir",required=True);ap.add_argument("--workers",type=int,default=4);ap.add_argument("--preflight-only",action="store_true")
 args=ap.parse_args();result=preflight(Path(args.sentinel_dir)) if args.preflight_only else run(Path(args.out_dir),Path(args.sentinel_dir),args.workers)
 print(json.dumps(result,indent=2))
