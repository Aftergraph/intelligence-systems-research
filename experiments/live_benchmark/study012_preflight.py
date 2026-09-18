"""STUDY-012 zero-inference pre-execution self-test."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from providers.stratum_resolver import validate_independence
ROOT=Path(__file__).resolve().parents[2]

def file_sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def evaluate(owner_approval_ref: str|None=None) -> dict:
    reasons=[]
    matrix_path=ROOT/"data/study012_provider_model_matrix.json"
    freeze_path=ROOT/"data/study012_freeze_manifest_v02.json"
    matrix=json.loads(matrix_path.read_text(encoding="utf-8"))
    freeze=json.loads(freeze_path.read_text(encoding="utf-8"))
    ok,independence_reasons=validate_independence(matrix)
    if not ok: reasons.extend(independence_reasons)
    if freeze.get("execution_gate",{}).get("provider_model_matrix_ready") is not True:
        reasons.append("provider_matrix_not_frozen")
    if freeze.get("execution_gate",{}).get("network_calls_authorized") is not False:
        reasons.append("freeze_network_authorization_not_false")
    pinned=freeze.get("files",{}).get("data/study012_provider_model_matrix.json")
    if pinned != file_sha(matrix_path):
        reasons.append("provider_matrix_hash_drift")
    if not owner_approval_ref:
        reasons.append("owner_approval_missing")
    return {
      "decision":"READY_TO_EXECUTE" if not reasons else "BLOCKED",
      "reasons":reasons,
      "network_calls_performed":0,
      "provider_strata":[s["provider"] for s in matrix.get("model_strata",[]) if s.get("readiness")=="READY"],
    }
if __name__=="__main__": print(json.dumps(evaluate(),indent=2))
