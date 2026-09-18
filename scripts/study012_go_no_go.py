"""STUDY-012 GO/NO-GO validator.

Selects the newest explicitly frozen execution generation without mutating or
reinterpreting historical freeze manifests.
"""
from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

def _evaluate_v4():
    from scripts.study012_recovery_freeze_v4 import verify
    reasons=[]
    manifest_path=ROOT/"data/study012_recovery_freeze_manifest_v4.json"
    if not manifest_path.exists():
        reasons.append("recovery_v4_freeze_missing")
    else:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if not verify(manifest):
            reasons.append("recovery_v4_freeze_drift")
    readiness=json.loads((ROOT/"data/study012_recovery_v4_readiness_20260918.json").read_text(encoding="utf-8"))
    if readiness.get("decision")!="READY" or readiness.get("calls")!=9:
        reasons.append("recovery_v4_readiness_not_ready")
    matrix=json.loads((ROOT/"data/study012_provider_model_matrix_v4.json").read_text(encoding="utf-8"))
    if matrix.get("substitution_allowed") is not False:
        reasons.append("provider_gate_not_fail_closed")
    approval=json.loads((ROOT/"data/study012_owner_approval_recovery_v4_full_20260918.json").read_text(encoding="utf-8"))
    if approval.get("status")!="GRANTED" or approval.get("network_calls_authorized") is not True:
        reasons.append("owner_approval_not_granted")
    return {
        "decision":"NO_GO" if reasons else "GO",
        "execution_id":"study012-recovery-v4-20260918",
        "reasons":reasons,
    }

def _evaluate_legacy():
    from scripts.study012_freeze_v02 import verify
    reasons=[]
    manifest_path=ROOT/"data/study012_freeze_manifest_v02.json"
    if not manifest_path.exists():
        reasons.append("freeze_manifest_missing")
    else:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if not verify(manifest):
            reasons.append("freeze_manifest_drift")
    matrix=json.loads((ROOT/"data/study012_provider_model_matrix.json").read_text(encoding="utf-8"))
    strata=matrix.get("model_strata",[])
    if not strata or any(s.get("readiness") not in {"READY","READY_FOR_FREEZE"} for s in strata):
        reasons.append("provider_strata_not_ready")
    if not matrix.get("execution_gate","").startswith("BLOCKED_"):
        reasons.append("provider_gate_not_fail_closed")
    reasons.append("owner_approval_not_granted")
    return {
        "decision":"NO_GO" if reasons else "GO",
        "execution_id":"study012-legacy",
        "reasons":reasons,
    }

def evaluate():
    if (ROOT/"data/study012_recovery_freeze_manifest_v4.json").exists():
        return _evaluate_v4()
    return _evaluate_legacy()

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2))
