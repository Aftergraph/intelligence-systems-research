from scripts.study012_postrun_freeze_v4 import build,verify,RAW_SHA,FROZEN_ANALYZER_SHA

def test_v4_postrun_freeze_binds_complete_evidence():
 m=build()
 assert m["status"]=="CLOSED_EVIDENCE_FROZEN"
 assert m["raw_observations_sha256"]==RAW_SHA
 assert m["frozen_analyzer_sha256"]==FROZEN_ANALYZER_SHA
 assert m["summary"]["observations"]==960
 assert m["summary"]["unique_trace_ids"]==960
 assert m["summary"]["confirmatory_admissibility"]=="PASS"
 assert m["summary"]["task_provider_failures"]==0
 assert m["summary"]["jd_disagreements"]==0
 assert m["summary"]["sentinel_unique_receipts"]==240
 assert m["summary"]["hypothesis_dispositions"]=={
  "H1":"SUPPORTED","H2":"WALKED_BACK","H3":"SUPPORTED","H4":"SUPPORTED"
 }
 assert verify(m)

def test_v4_postrun_freeze_detects_drift():
 m=build()
 key=next(iter(m["files"]))
 m["files"][key]="0"*64
 assert not verify(m)
