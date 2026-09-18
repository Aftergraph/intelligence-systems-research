import json
from pathlib import Path
from experiments.live_benchmark.study012_execution import RunManifest,ReceiptJournal,Checkpoint,pending,sha256_obj
from experiments.live_benchmark.study012_preflight import evaluate

def test_run_manifest_hash_is_stable():
 m=RunManifest("v1","STUDY-012","run-1","abc","f","p","w","a",("J","D","JD","DI"))
 assert m.manifest_hash==m.manifest_hash
 assert len(m.manifest_hash)==64

def test_receipt_and_checkpoint_resume(tmp_path):
 j=ReceiptJournal(tmp_path/"receipts.jsonl"); c=Checkpoint(tmp_path/"checkpoint.jsonl")
 r={"run_id":"r1","trace_id":"t1","condition":"D","provider":"google","model_id":"gemini-2.5-flash","execution_class":"DRY_RUN","request_hash":"a"*64,"response_hash":"b"*64,"is_live":False}
 h=j.append(r); c.record("t1",h)
 assert j.read_all()[0]["receipt_hash"]==h
 assert pending([{"trace_id":"t1"},{"trace_id":"t2"}],c)==[{"trace_id":"t2"}]

def test_receipt_rejects_false_live_claim(tmp_path):
 import pytest
 j=ReceiptJournal(tmp_path/"r.jsonl")
 r={"run_id":"r1","trace_id":"t1","condition":"D","provider":"google","model_id":"x","execution_class":"DRY_RUN","request_hash":"a"*64,"response_hash":"b"*64,"is_live":True}
 with pytest.raises(ValueError,match="non_live_execution"):
  j.append(r)

def test_preflight_stops_at_owner_gate_without_network():
 result=evaluate()
 assert result["decision"]=="BLOCKED"
 assert result["network_calls_performed"]==0
 assert result["reasons"]==["owner_approval_missing"]
 assert set(result["provider_strata"])=={"openrouter","google"}
