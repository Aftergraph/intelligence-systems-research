from scripts.study012_freeze_v02 import build, verify
from scripts.study012_go_no_go import evaluate
def test_freeze_manifest_binds_all_critical_artifacts():
 m=build()
 assert len(m["files"]) >= 18
 assert m["execution_gate"]["provider_model_matrix_ready"] is True
 assert m["execution_gate"]["network_calls_authorized"] is False
 assert verify(m)
def test_go_no_go_reflects_granted_recovery_v4_execution_gate():
 g=evaluate()
 assert g["decision"]=="GO"
 assert g["execution_id"]=="study012-recovery-v4-20260918"
 assert g["reasons"]==[]
def test_freeze_manifest_detects_drift():
 m=build(); k=next(iter(m["files"])); m["files"][k]="0"*64
 assert not verify(m)
