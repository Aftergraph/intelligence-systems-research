"""Canonical STUDY-012 bridge to WORKS verification ingest.

This does not mint Sentinel receipts. It only validates and transports an already
independently-produced Sentinel domain-verifier verdict to canonical WORKS.
"""
from __future__ import annotations
import json,re
from urllib import request,error
from typing import Any

DVR=re.compile(r"^dvr_[a-f0-9]{64}$")
VERIFIER_HEADER="X-WORKS-Verifier-Token"

def validate_receipt(receipt:dict[str,Any])->tuple[bool,str|None]:
    if receipt.get("result") not in {"passed","failed"}: return False,"result_invalid"
    vid=receipt.get("verifier_id")
    if not isinstance(vid,str) or not vid.startswith("sentinel:") or vid.strip()!=vid:
        return False,"verifier_id_invalid"
    ref=receipt.get("evidence_ref")
    if not isinstance(ref,str) or not DVR.fullmatch(ref): return False,"evidence_ref_invalid"
    at=receipt.get("verified_at")
    if not isinstance(at,str) or "T" not in at or not at.endswith("Z"): return False,"verified_at_invalid"
    return True,None

def build_request(base_url:str,work_id:str,token:str,receipt:dict[str,Any]):
    ok,reason=validate_receipt(receipt)
    if not ok: raise ValueError(reason)
    if not token or len(token)<32: raise ValueError("verifier_token_too_short")
    url=base_url.rstrip("/") + f"/v1/works/{work_id}/verification"
    body=json.dumps(receipt,sort_keys=True,separators=(",",":")).encode("utf-8")
    return request.Request(url,data=body,headers={"Content-Type":"application/json",VERIFIER_HEADER:token},method="POST")

def ingest(base_url:str,work_id:str,token:str,receipt:dict[str,Any],timeout:float=15.0)->dict[str,Any]:
    req=build_request(base_url,work_id,token,receipt)
    try:
        with request.urlopen(req,timeout=timeout) as resp:
            return {"http_status":resp.status,"body":json.loads(resp.read().decode("utf-8"))}
    except error.HTTPError as exc:
        return {"http_status":exc.code,"body":None}
