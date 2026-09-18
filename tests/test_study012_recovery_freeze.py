import json
from scripts.study012_recovery_freeze import build,verify

def test_recovery_freeze_is_exact_and_authorized():
 m=build()
 assert len(m["files"])>=25
 assert m["execution_id"]=="study012-recovery-v2-20260918"
 assert m["pooling_with_parent"] is False
 assert m["execution_gate"]["readiness_decision"]=="READY"
 assert m["execution_gate"]["readiness_calls"]==9
 assert m["execution_gate"]["network_calls_authorized"] is True
 assert m["execution_gate"]["provider_substitution_allowed"] is False
 assert m["execution_gate"]["hard_cost_stop_usd"]==4.0
 assert verify(m)

def test_recovery_freeze_detects_drift():
 m=build();k=next(iter(m["files"]));m["files"][k]="0"*64
 assert not verify(m)
