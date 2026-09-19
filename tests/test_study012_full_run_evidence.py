import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"data/study012_runs/full-matrix-live-20260918-v1"

def test_full_matrix_raw_dataset_is_exact_and_unique():
 p=RUN/"observations.jsonl"
 assert hashlib.sha256(p.read_bytes()).hexdigest()=="9e712249555180fcc32fb22c0a0b99298d09e7dda114f92b97d2e6de3ce08411"
 rows=[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
 assert len(rows)==960
 assert len({r["trace_id"] for r in rows})==960
 assert sum(r["execution_class"]=="LIVE_VALID" for r in rows)==222
 assert sum(r["execution_class"]=="LIVE_PROVIDER_FAILURE" for r in rows)==738

def test_full_matrix_provider_and_independence_accounting():
 rows=[json.loads(x) for x in (RUN/"observations.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
 google=[r for r in rows if r["provider"]=="google"]
 openrouter=[r for r in rows if r["provider"]=="openrouter"]
 assert len(google)==480 and len(openrouter)==480
 assert sum(r["execution_class"]=="LIVE_VALID" for r in google)==7
 assert sum(r["execution_class"]=="LIVE_VALID" for r in openrouter)==215
 di=[r for r in rows if r["condition"]=="DI" and r["execution_class"]=="LIVE_VALID"]
 assert len(di)==47
 assert all((r.get("sentinel") or {}).get("verdict")=="VERIFIED" for r in di)
 assert all((r.get("independent_receipt") or {}).get("evidence_ref","").startswith("dvr_") for r in di)

def test_claim_disposition_remains_fail_closed():
 d=json.loads((ROOT/"data/study012_claim_disposition_v01.json").read_text())
 assert d["confirmatory_status"]=="NOT_ESTABLISHED_PROVIDER_AVAILABILITY_CONFOUND"
 assert d["hypotheses"]["H1_grounding"]["status"]=="UNKNOWN"
 assert d["hypotheses"]["H3_trace_robustness"]["status"]=="UNKNOWN"
 assert d["next_execution_requires_new_owner_approval"] is True
