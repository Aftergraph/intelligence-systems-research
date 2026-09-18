"""STUDY-012 execution package v1.

This module defines canonical run identity, append-only receipts, checkpoint/resume,
and pre-execution validation. It does not perform model inference.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json
from pathlib import Path
from typing import Any, Iterable

def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()

@dataclass(frozen=True)
class RunManifest:
    schema_version: str
    study_id: str
    execution_id: str
    source_commit: str
    freeze_manifest_sha256: str
    provider_matrix_sha256: str
    workload_manifest_sha256: str
    amendment_manifest_sha256: str
    conditions: tuple[str, ...]
    owner_approval_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d=asdict(self)
        d["conditions"]=list(self.conditions)
        return d

    @property
    def manifest_hash(self) -> str:
        return sha256_obj(self.to_dict())

class ReceiptJournal:
    def __init__(self, path: str | Path):
        self.path=Path(path)

    def append(self, receipt: dict[str, Any]) -> str:
        required={"run_id","trace_id","condition","provider","model_id","execution_class","request_hash","response_hash","is_live"}
        missing=sorted(required-set(receipt))
        if missing:
            raise ValueError(f"receipt_missing_fields:{','.join(missing)}")
        if receipt["execution_class"] in {"DRY_RUN","SIMULATED","LIVE_PROVIDER_FAILURE"} and receipt["is_live"] is True:
            raise ValueError("non_live_execution_cannot_claim_is_live")
        if receipt["execution_class"] in {"LIVE_VALID","LIVE_SEMANTIC_FAILURE"} and receipt["is_live"] is not True:
            raise ValueError("live_execution_class_requires_is_live")
        payload=dict(receipt)
        payload["receipt_hash"]=sha256_obj(receipt)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a",encoding="utf-8",newline="\n") as fh:
            fh.write(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n")
        return payload["receipt_hash"]

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        return [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]

class Checkpoint:
    def __init__(self,path: str | Path):
        self.path=Path(path)

    def completed_trace_ids(self) -> set[str]:
        if not self.path.exists(): return set()
        out=set()
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row=json.loads(line)
                out.add(row["trace_id"])
        return out

    def record(self,trace_id: str,receipt_hash: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row={"trace_id":trace_id,"receipt_hash":receipt_hash}
        with self.path.open("a",encoding="utf-8",newline="\n") as fh:
            fh.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")

def pending(rows: Iterable[dict[str, Any]], checkpoint: Checkpoint) -> list[dict[str, Any]]:
    done=checkpoint.completed_trace_ids()
    return [r for r in rows if r["trace_id"] not in done]
