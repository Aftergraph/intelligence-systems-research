import json
from pathlib import Path
from scripts.study012_freeze_v02 import build, verify
from scripts.study012_go_no_go import evaluate
ROOT=Path(__file__).resolve().parents[1]
def test_freeze_manifest_binds_all_critical_artifacts(tmp_path):
 m=build()
 assert len(m["files"]) >= 12
 assert m["execution_gate"]["network_calls_authorized"] is False
 assert verify(m)
def test_go_no_go_is_fail_closed_before_provider_and_owner_freeze():
 g=evaluate()
 assert g["decision"]=="NO_GO"
 assert "provider_model_matrix_unfrozen" in g["reasons"]
 assert "owner_approval_not_granted" in g["reasons"]
def test_freeze_manifest_detects_drift():
 m=build(); k=next(iter(m["files"])); m["files"][k]="0"*64
 assert not verify(m)
