from scripts.study012_freeze_v02 import build, verify
from scripts.study012_go_no_go import evaluate
def test_freeze_manifest_binds_all_critical_artifacts():
 m=build()
 assert len(m["files"]) >= 18
 assert m["execution_gate"]["provider_model_matrix_ready"] is True
 assert m["execution_gate"]["network_calls_authorized"] is False
 assert verify(m)
def test_go_no_go_reaches_owner_gate_only_after_provider_freeze():
 g=evaluate()
 assert g["decision"]=="NO_GO"
 assert g["reasons"]==["owner_approval_not_granted"]
def test_freeze_manifest_detects_drift():
 m=build(); k=next(iter(m["files"])); m["files"][k]="0"*64
 assert not verify(m)
