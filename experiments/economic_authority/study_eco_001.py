#!/usr/bin/env python3
"""Frozen analysis for STUDY-ECO-001.

This module intentionally uses only the Python standard library. It validates
one captured execution against preregistered deterministic gates. It performs
no payment, custody, settlement, or network actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "aftergraph.study-eco-001-evidence/v1"
RESULT_SCHEMA = "aftergraph.study-eco-001-result/v1"
SHA1_LEN = 40
SHA256_LEN = 64
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024

FROZEN_SUBJECTS = {
    "core_labs_fabric": "57ae5bb65dc3de0e0ab358cba6e53fc88626b974",
    "trust_gateway": "49d9d1d43c80f4dae34dc3df6778e9a8cccb39db",
    "works_execution": "e7bc30a56ad14410927daa5c83e561d918ccb1da",
    "runtime": "e97b465faa34044d6e573f5f228efec79884e230",
    "fihim_eval_lab": "6e2b83679446e4e3c67c6166228bceafff222656",
    "fihim_vnext": "e209f21b9b226613a83f2ce63bb4107e60e266ab",
    "sentinel": "065a7bbfafac53f3425feecdf3ec1c1f81036394",
}

REQUIRED_SUITES = {
    "TG_CUSTODY_CANARY",
    "WORKS_SETTLEMENT_RECOVERY",
    "SENTINEL_CUSTODY_VERIFICATION",
    "SENTINEL_RAIL_VERIFICATION",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_hex(value: Any, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def canonical_json(value: Any) -> str:
    """Match the Labs Fabric / Sentinel recursive canonical JSON form."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return "null"
        if value.is_integer():
            return str(int(value))
        return json.dumps(value, allow_nan=False, separators=(",", ":"))
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(str(key), ensure_ascii=False) + ":" + canonical_json(value[key])
            for key in sorted(value)
        ) + "}"
    return "null"


def _document_digest(document: dict[str, Any], digest_field: str) -> str:
    base = {key: value for key, value in document.items() if key != digest_field}
    return _sha256_bytes(canonical_json(base).encode("utf-8"))


def _resolve_artifact(artifact_root: Path, reference: Any) -> tuple[Path | None, str | None]:
    if not isinstance(reference, str) or not reference.strip():
        return None, "missing_reference"
    candidate = Path(reference)
    if candidate.is_absolute():
        return None, "absolute_path_forbidden"
    root = artifact_root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None, "path_escape"
    if not resolved.is_file():
        return None, "file_missing"
    try:
        size = resolved.stat().st_size
    except OSError:
        return None, "file_unreadable"
    if size > MAX_ARTIFACT_BYTES:
        return None, "file_too_large"
    return resolved, None


def _load_json_artifact(
    artifact_root: Path,
    reference: Any,
    label: str,
    failures: list[str],
) -> dict[str, Any] | None:
    path, error = _resolve_artifact(artifact_root, reference)
    if error:
        failures.append(f"{label}:{error}")
        return None
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        failures.append(f"{label}:invalid_json")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label}:not_object")
        return None
    return value


def _bind_preflight_raw(
    summary: dict[str, Any],
    artifact_root: Path,
    failures: list[str],
) -> dict[str, Any] | None:
    raw = _load_json_artifact(artifact_root, summary.get("receiptPath"), "preflight_raw", failures)
    if raw is None:
        return None

    raw_digest = raw.get("receiptDigest")
    if not _is_hex(raw_digest, SHA256_LEN):
        failures.append("preflight_raw:receipt_digest_format")
    elif _document_digest(raw, "receiptDigest") != str(raw_digest).lower():
        failures.append("preflight_raw:receipt_digest_mismatch")

    if summary.get("receiptDigest") != raw_digest:
        failures.append("preflight_summary:receipt_digest_mismatch")
    if raw.get("schemaVersion") != "aftergraph.labs-preflight/v1":
        failures.append("preflight_raw:schema")
    if summary.get("state") != raw.get("state"):
        failures.append("preflight_summary:state_mismatch")
    if summary.get("missingAdapterCount") != len(raw.get("missingAdapterIds", [])):
        failures.append("preflight_summary:missing_adapter_count_mismatch")
    unresolved = raw.get("httpBundle", {}).get("unresolvedTargets", [])
    if not isinstance(unresolved, list):
        failures.append("preflight_raw:unresolved_targets")
        unresolved = [None]
    if summary.get("unresolvedTargetCount") != len(unresolved):
        failures.append("preflight_summary:unresolved_target_count_mismatch")

    for field in ("authorityGranted", "verificationGranted", "scientificValidityGranted"):
        if summary.get(field) != raw.get(field):
            failures.append(f"preflight_summary:{field}_mismatch")
    return raw


def _bind_sentinel_raw(
    summary: dict[str, Any],
    artifact_root: Path,
    preflight_digest: Any,
    failures: list[str],
) -> dict[str, Any] | None:
    raw = _load_json_artifact(
        artifact_root,
        summary.get("verificationPath"),
        "sentinel_raw",
        failures,
    )
    if raw is None:
        return None

    raw_digest = raw.get("verificationDigest")
    if not _is_hex(raw_digest, SHA256_LEN):
        failures.append("sentinel_raw:verification_digest_format")
    elif _document_digest(raw, "verificationDigest") != str(raw_digest).lower():
        failures.append("sentinel_raw:verification_digest_mismatch")

    if summary.get("verificationDigest") != raw_digest:
        failures.append("sentinel_summary:verification_digest_mismatch")
    if raw.get("schemaVersion") != "aftergraph.sentinel-labs-preflight-verification/v1":
        failures.append("sentinel_raw:schema")
    if raw.get("sourceReceiptDigest") != preflight_digest:
        failures.append("sentinel_raw:source_receipt_digest_mismatch")

    for field in (
        "state",
        "valid",
        "coverageComplete",
        "promotionAuthority",
        "scientificValidityGranted",
    ):
        if summary.get(field) != raw.get(field):
            failures.append(f"sentinel_summary:{field}_mismatch")
    return raw


def analyze(evidence: dict[str, Any], artifact_root: Path | None = None) -> dict[str, Any]:
    invalid: list[str] = []
    failures: list[str] = []
    root = (artifact_root or Path.cwd()).resolve()

    if evidence.get("schemaVersion") != SCHEMA:
        invalid.append("schema")
    if evidence.get("studyId") != "STUDY-ECO-001":
        invalid.append("study_id")
    if not str(evidence.get("executionId", "")).strip():
        invalid.append("execution_id")
    if not str(evidence.get("executedAt", "")).strip():
        invalid.append("executed_at")
    if not str(evidence.get("runner", "")).strip():
        invalid.append("runner")

    subjects = evidence.get("sourceCommits")
    if not isinstance(subjects, dict):
        invalid.append("source_commits")
        subjects = {}
    for key, expected in FROZEN_SUBJECTS.items():
        if subjects.get(key) != expected:
            invalid.append(f"source_commit:{key}")
    workflow_commit = subjects.get("core_workflow")
    if not _is_hex(workflow_commit, SHA1_LEN):
        invalid.append("source_commit:core_workflow")
    if evidence.get("corePackageDiffEmptyFromFreeze") is not True:
        invalid.append("core_package_drift")

    preflight = evidence.get("preflight")
    if not isinstance(preflight, dict):
        invalid.append("preflight")
        preflight = {}
    if preflight.get("state") != "OBSERVED":
        failures.append("preflight_state")
    if preflight.get("missingAdapterCount") != 0:
        failures.append("preflight_missing_adapters")
    if preflight.get("unresolvedTargetCount") != 0:
        failures.append("preflight_unresolved_targets")
    if not _is_hex(preflight.get("receiptDigest"), SHA256_LEN):
        failures.append("preflight_receipt_digest")
    if preflight.get("authorityGranted") is not False:
        failures.append("preflight_authority_escalation")
    if preflight.get("verificationGranted") is not False:
        failures.append("preflight_verification_escalation")
    if preflight.get("scientificValidityGranted") is not False:
        failures.append("preflight_scientific_escalation")

    raw_preflight = _bind_preflight_raw(preflight, root, failures)

    sentinel = evidence.get("sentinelVerification")
    if not isinstance(sentinel, dict):
        invalid.append("sentinel_verification")
        sentinel = {}
    if sentinel.get("state") != "VERIFIED_OBSERVATIONAL_PREFLIGHT":
        failures.append("sentinel_state")
    if sentinel.get("valid") is not True:
        failures.append("sentinel_invalid")
    if sentinel.get("coverageComplete") is not True:
        failures.append("sentinel_incomplete")
    if sentinel.get("promotionAuthority") is not False:
        failures.append("sentinel_promotion_escalation")
    if sentinel.get("scientificValidityGranted") is not False:
        failures.append("sentinel_scientific_escalation")
    if not _is_hex(sentinel.get("verificationDigest"), SHA256_LEN):
        failures.append("sentinel_verification_digest")

    _bind_sentinel_raw(
        sentinel,
        root,
        preflight.get("receiptDigest"),
        failures,
    )

    suites = evidence.get("suites")
    if not isinstance(suites, list):
        invalid.append("suites")
        suites = []

    seen: set[str] = set()
    observed_suite_ids: set[str] = set()
    for index, suite in enumerate(suites):
        if not isinstance(suite, dict):
            failures.append(f"suite_record_not_object:{index}")
            continue
        suite_id = str(suite.get("id", ""))
        if not suite_id:
            failures.append(f"suite_missing_id:{index}")
            continue
        if suite_id in seen:
            failures.append(f"duplicate_suite:{suite_id}")
        seen.add(suite_id)
        observed_suite_ids.add(suite_id)

        if suite_id not in REQUIRED_SUITES:
            failures.append(f"unexpected_suite:{suite_id}")
        if suite.get("exitCode") != 0:
            failures.append(f"suite_failed:{suite_id}")

        expected_digest = suite.get("outputSha256")
        if not _is_hex(expected_digest, SHA256_LEN):
            failures.append(f"suite_output_digest_format:{suite_id}")
        path, path_error = _resolve_artifact(root, suite.get("outputPath"))
        if path_error:
            failures.append(f"suite_output:{suite_id}:{path_error}")
        else:
            actual_digest = _sha256_bytes(path.read_bytes())
            if actual_digest != str(expected_digest).lower():
                failures.append(f"suite_output_digest_mismatch:{suite_id}")

    if observed_suite_ids != REQUIRED_SUITES:
        failures.append("suite_set")

    if evidence.get("externalEffects") != 0:
        failures.append("external_effects")
    if evidence.get("realAssetMovement") is not False:
        failures.append("real_asset_movement")
    if evidence.get("liveMoneyMovement") is not False:
        failures.append("live_money_movement")
    if evidence.get("economicFinalityGranted") is not False:
        failures.append("economic_finality_escalation")
    if evidence.get("promotionAuthority") is not False:
        failures.append("promotion_authority")
    if evidence.get("scientificValidityGranted") is not False:
        failures.append("scientific_validity")

    # Once semantic evidence exists, a semantic failure always outranks malformed
    # metadata. This prevents a failed run from being reclassified as excludable.
    if failures:
        status = "FALSIFIED"
    elif invalid:
        status = "INVALID_RUN"
    else:
        status = "CONFIRMATORY_SYSTEM_PASS"

    base = {
        "schemaVersion": RESULT_SCHEMA,
        "studyId": "STUDY-ECO-001",
        "executionId": evidence.get("executionId"),
        "status": status,
        "primaryGateCount": 5,
        "primaryGatesPassed": status == "CONFIRMATORY_SYSTEM_PASS",
        "internalPreregisteredResult": status == "CONFIRMATORY_SYSTEM_PASS",
        "externalIndependentReproduction": False,
        "e5OrE6Claim": False,
        "scientificValidityGranted": False,
        "realMoneySettlementDemonstrated": False,
        "realAssetMovementDemonstrated": False,
        "rawPreflightBound": raw_preflight is not None,
        "invalidReasons": sorted(set(invalid)),
        "falsificationReasons": sorted(set(failures)),
    }
    base["resultDigest"] = _sha256_bytes(
        canonical_json(base).encode("utf-8")
    )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    evidence_path = Path(args.evidence).resolve()
    out_path = Path(args.out).resolve()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    result = analyze(evidence, evidence_path.parent)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "studyId": result["studyId"],
        "status": result["status"],
        "resultDigest": result["resultDigest"],
        "out": str(out_path),
    }, sort_keys=True))
    return 0 if result["status"] == "CONFIRMATORY_SYSTEM_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
