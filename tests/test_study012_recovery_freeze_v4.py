from scripts.study012_recovery_freeze_v4 import build,verify

def test_v4_freeze_is_exact_and_fail_closed():
 m=build()
 assert len(m["files"])>=25
 assert m["execution_id"]=="study012-recovery-v4-20260918"
 assert m["pooling_with_prior_runs"] is False
 assert m["execution_gate"]["readiness_decision"]=="READY"
 assert m["execution_gate"]["readiness_calls"]==9
 assert m["execution_gate"]["owner_status"]=="NOT_GRANTED"
 assert m["execution_gate"]["network_calls_authorized"] is False
 assert m["execution_gate"]["provider_substitution_allowed"] is False
 assert m["execution_gate"]["hard_cost_stop_usd"]==4.0
 assert verify(m)

def test_v4_freeze_detects_drift():
 m=build(); key=next(iter(m["files"])); m["files"][key]="0"*64
 assert not verify(m)
