import json
from pathlib import Path
from scripts.study012_v3_execution_freeze import build,verify

def test_v3_execution_freeze_is_exact_and_fail_closed():
 m=build()
 assert m["status"]=="FROZEN_AUTHORIZED_FOR_EXACT_V3_EXECUTION"
 assert m["gates"]["readiness_decision"]=="READY"
 assert m["gates"]["readiness_observations"]==9
 assert m["gates"]["network_calls_authorized"] is True
 assert m["gates"]["pooling_with_prior_runs"] is False
 assert m["gates"]["provider_independence_claim_allowed"] is False
 assert m["gates"]["execution_fabric"]=="novita_sandbox"
 assert verify(m)

def test_v3_execution_freeze_detects_drift():
 m=build();k=next(iter(m["files"]));m["files"][k]="0"*64
 assert not verify(m)
