"""Evidence-bound provider-stratum selection for research execution."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

def load_matrix(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def ready_strata(matrix: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [s for s in matrix.get("model_strata", []) if s.get("readiness") == "READY"]

def validate_independence(matrix: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Require >=2 ready strata with distinct provider endpoints."""
    strata = ready_strata(matrix)
    reasons=[]
    if len(strata) < 2:
        reasons.append("fewer_than_two_ready_strata")
    providers={s.get("provider") for s in strata}
    endpoints={s.get("endpoint") for s in strata}
    if len(providers) != len(strata):
        reasons.append("provider_identity_not_distinct")
    if len(endpoints) != len(strata):
        reasons.append("endpoint_not_distinct")
    if any(not s.get("models") for s in strata):
        reasons.append("empty_model_set")
    return (not reasons, reasons)

def execution_plan(matrix: Dict[str, Any]) -> Dict[str, Any]:
    ok,reasons=validate_independence(matrix)
    return {
        "decision":"READY_FOR_OWNER_GATE" if ok else "BLOCKED",
        "strata":[{"id":s["id"],"provider":s["provider"],"endpoint":s["endpoint"],
                   "models":[m["exact_model_id"] for m in s["models"]]}
                  for s in ready_strata(matrix)],
        "reasons":reasons,
    }
