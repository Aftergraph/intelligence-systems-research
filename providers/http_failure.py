"""Sanitized provider HTTP failure provenance."""
from __future__ import annotations
import json
from urllib import error
from typing import Any

SAFE_HEADERS=("retry-after","x-ratelimit-limit","x-ratelimit-remaining","x-ratelimit-reset","x-request-id")

def _clean_text(value:Any, secret:str|None=None, limit:int=500)->str:
    s=str(value or "")
    if secret: s=s.replace(secret,"[REDACTED_API_KEY]")
    return s[:limit]

def provider_error_snapshot(exc:Exception, secret:str|None=None)->dict[str,Any]:
    out={"exception_type":type(exc).__name__}
    if isinstance(exc,error.HTTPError):
        out["category"]="HTTP_ERROR"
        out["http_status"]=int(exc.code)
        out["reason"]=_clean_text(exc.reason,secret)
        headers={}
        available={}
        if exc.headers:
            try:
                available={str(k).lower():v for k,v in exc.headers.items()}
            except Exception:
                available={}
        for name in SAFE_HEADERS:
            v=available.get(name)
            if v is not None: headers[name]=_clean_text(v,secret,200)
        if headers: out["headers"]=headers
        try:
            raw=exc.read(16384).decode("utf-8","replace")
            parsed=json.loads(raw)
            err=parsed.get("error",parsed) if isinstance(parsed,dict) else {}
            if isinstance(err,dict):
                if err.get("status") is not None: out["provider_status"]=_clean_text(err.get("status"),secret,120)
                if err.get("code") is not None: out["provider_code"]=err.get("code")
                if err.get("message") is not None: out["provider_message"]=_clean_text(err.get("message"),secret,500)
        except Exception:
            pass
        return out
    if isinstance(exc,error.URLError):
        out["category"]="URL_ERROR"
        out["reason"]=_clean_text(exc.reason,secret)
        return out
    if isinstance(exc,TimeoutError):
        out["category"]="TIMEOUT"
        out["reason"]="timeout"
        return out
    out["category"]="OTHER"
    out["reason"]=_clean_text(exc,secret)
    return out
