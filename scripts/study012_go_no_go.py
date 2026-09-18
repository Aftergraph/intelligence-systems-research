"""STUDY-012 GO/NO-GO validator."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.study012_freeze_v02 import build, verify

def evaluate():
    reasons=[]
    manifest_path=ROOT/"data/study012_freeze_manifest_v02.json"
    if not manifest_path.exists():
        reasons.append("freeze_manifest_missing")
    else:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if not verify(manifest):
            reasons.append("freeze_manifest_drift")
    matrix=json.loads((ROOT/"data/study012_provider_model_matrix.json").read_text(encoding="utf-8"))
    if "TBD_" in json.dumps(matrix):
        reasons.append("provider_model_matrix_unfrozen")
    if not matrix.get("execution_gate","").startswith("BLOCKED_"):
        reasons.append("provider_gate_not_fail_closed")
    reasons.append("owner_approval_not_granted")
    return {"decision":"NO_GO" if reasons else "GO","reasons":reasons}

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2))
