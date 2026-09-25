"""Confirmatory admissibility and amendment validation for STUDY-015."""
from __future__ import annotations

import re
from typing import Any, Iterable

from .validate_envelope import validate_envelope

AMENDMENT_ID = re.compile(r"^S15-AMD-[0-9]{3}$")


class AdmissibilityError(ValueError):
    pass


def validate_amendment(amendment: dict[str, Any]) -> None:
    required = {
        "id","timestamp_utc","trigger","description",
        "before_protocol_sha256","after_protocol_sha256"
    }
    missing = sorted(required - set(amendment))
    if missing:
        raise AdmissibilityError(f"amendment missing fields: {missing}")
    if not AMENDMENT_ID.match(str(amendment["id"])):
        raise AdmissibilityError("invalid amendment id")
    for key in ("before_protocol_sha256","after_protocol_sha256"):
        value = str(amendment[key])
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise AdmissibilityError(f"invalid {key}")
    if amendment["before_protocol_sha256"] == amendment["after_protocol_sha256"]:
        raise AdmissibilityError("amendment must identify a protocol change")


def assert_confirmatory_admissible(
    records: Iterable[dict[str, Any]],
    *,
    freeze_manifest: dict[str, Any],
    owner_gate: dict[str, Any],
) -> None:
    if freeze_manifest.get("status") != "FROZEN":
        raise AdmissibilityError("freeze manifest is not FROZEN")
    if owner_gate.get("status") != "APPROVED" or owner_gate.get("authorize_confirmatory_execution") is not True:
        raise AdmissibilityError("owner gate has not authorized confirmatory execution")

    expected_fp = freeze_manifest.get("implementation_fingerprint")
    expected_heads = freeze_manifest.get("source_heads")
    if not expected_fp or not expected_heads:
        raise AdmissibilityError("freeze manifest lacks pinned implementation identity")

    run_ids: set[str] = set()
    condition_pairs: set[tuple[str, str, str, str, str]] = set()
    for raw in records:
        row = validate_envelope(dict(raw))
        if row["execution_class"] != "LIVE_VALID" or row["is_live"] is not True:
            raise AdmissibilityError(f"non-live record is inadmissible: {row['run_id']}")
        if row["implementation_fingerprint"] != expected_fp:
            raise AdmissibilityError(f"implementation fingerprint mismatch: {row['run_id']}")
        if row["source_heads"] != expected_heads:
            raise AdmissibilityError(f"source-head mismatch: {row['run_id']}")
        if row["run_id"] in run_ids:
            raise AdmissibilityError(f"duplicate run_id: {row['run_id']}")
        run_ids.add(row["run_id"])
        pair = (
            row["provider"], row["model"], row["workload_id"],
            str(row["replicate_id"]), row["condition"],
        )
        if pair in condition_pairs:
            raise AdmissibilityError(f"duplicate condition pairing key: {pair}")
        condition_pairs.add(pair)
