from scripts.study012_freeze_v02 import build, verify
from scripts.study012_go_no_go import evaluate
def test_freeze_manifest_binds_all_critical_artifacts():
 m=build()
 assert len(m["files"]) >= 13
 assert m["execution_gate"]["network_calls_authorized"] is False
 assert verify(m)
def test_go_no_go_is_fail_closed_on_provider_and_owner_gates():
 g=evaluate()
 assert g["decision"]=="NO_GO"
 assert "provider_strata_not_ready" in g["reasons"]
 assert "owner_approval_not_granted" in g["reasons"]
def test_freeze_manifest_detects_drift():
 m=build(); k=next(iter(m["files"])); m["files"][k]="0"*64
 assert not verify(m)
