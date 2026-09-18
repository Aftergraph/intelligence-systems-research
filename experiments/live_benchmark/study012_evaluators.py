"""STUDY-012 frozen evaluation semantics. No network calls."""
from __future__ import annotations
from typing import Any

VALID_JUDGE={"VERIFIED","FAILED","ABSTAIN"}

def deterministic_exact(response_text:str, workload:dict[str,Any])->dict[str,Any]:
    expected=workload["response_contract"]["expected"]
    observed=(response_text or "").strip()
    passed=observed==expected
    return {"verdict":"VERIFIED" if passed else "FAILED","expected":expected,"observed":observed,"oracle":workload["oracle"]}

def parse_judge_observation(text:str)->dict[str,Any]:
    verdict=(text or "").strip().upper()
    if verdict not in VALID_JUDGE:
        return {"verdict":"ABSTAIN","admissible":False,"reason":"judge_output_not_enum"}
    return {"verdict":verdict,"admissible":True}

def canonicalize(condition:str, deterministic:dict|None=None, judge:dict|None=None, independent_receipt:dict|None=None)->dict[str,Any]:
    if condition=="J":
        return {"canonical_verdict":"UNESTABLISHED","judge_verdict":(judge or {}).get("verdict"),"reason":"judge_only_cannot_establish_verified"}
    if condition=="D":
        if not deterministic: return {"canonical_verdict":"BLOCKED","reason":"deterministic_evidence_missing"}
        return {"canonical_verdict":deterministic["verdict"]}
    if condition=="JD":
        if not deterministic: return {"canonical_verdict":"BLOCKED","reason":"deterministic_evidence_missing"}
        return {"canonical_verdict":deterministic["verdict"],"judge_verdict":(judge or {}).get("verdict")}
    if condition=="DI":
        if not deterministic: return {"canonical_verdict":"BLOCKED","reason":"deterministic_evidence_missing"}
        ok,reason=validate_independent_receipt(independent_receipt)
        if not ok: return {"canonical_verdict":"BLOCKED","reason":reason}
        if deterministic["verdict"]!="VERIFIED" or independent_receipt["result"]!="passed":
            return {"canonical_verdict":"FAILED"}
        return {"canonical_verdict":"VERIFIED"}
    raise ValueError(f"unknown_condition:{condition}")

def validate_independent_receipt(receipt:dict|None)->tuple[bool,str|None]:
    if not receipt: return False,"independent_receipt_missing"
    if receipt.get("verifier_id")!="sentinel:domain-verifier": return False,"independent_verifier_wrong"
    if receipt.get("result") not in {"passed","failed"}: return False,"independent_result_invalid"
    ref=receipt.get("evidence_ref","")
    if not isinstance(ref,str) or not ref.startswith("dvr_"): return False,"independent_evidence_ref_invalid"
    return True,None
