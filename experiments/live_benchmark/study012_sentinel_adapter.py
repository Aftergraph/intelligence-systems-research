"""Pinned subprocess adapter to Sentinel research verifier.

The adapter requires an exact Sentinel checkout and never falls back to another
verifier or revision.
"""
from __future__ import annotations
import json,subprocess
from pathlib import Path
from typing import Any

PINNED_SENTINEL_COMMIT="f9a0f85a50cd4a74400b8b267c29a943da5af68b"
CLI_RELATIVE=Path("bin/sentinel-research-verify.js")

def verify_checkout(repo_dir:str|Path)->tuple[bool,str|None]:
    repo=Path(repo_dir)
    if not (repo/CLI_RELATIVE).exists(): return False,"sentinel_cli_missing"
    try:
        got=subprocess.run(["git","rev-parse","HEAD"],cwd=repo,capture_output=True,text=True,timeout=5,check=True).stdout.strip()
    except Exception:
        return False,"sentinel_git_head_unavailable"
    if got!=PINNED_SENTINEL_COMMIT: return False,"sentinel_commit_mismatch"
    return True,None

def verify_research_envelope(repo_dir:str|Path,envelope:dict[str,Any],verifier_ref:str="sentinel:domain-verifier")->dict[str,Any]:
    ok,reason=verify_checkout(repo_dir)
    if not ok: return {"verdict":"INDETERMINATE","reason":reason}
    proc=subprocess.run(
      ["node",str(CLI_RELATIVE),"--verifier-ref",verifier_ref],
      cwd=Path(repo_dir),input=json.dumps(envelope,separators=(",",":")),
      capture_output=True,text=True,timeout=15
    )
    try: out=json.loads(proc.stdout)
    except Exception: return {"verdict":"INDETERMINATE","reason":"sentinel_output_invalid"}
    if out.get("verdict")=="VERIFIED" and proc.returncode!=0:
        return {"verdict":"INDETERMINATE","reason":"sentinel_exit_verdict_mismatch"}
    return out
