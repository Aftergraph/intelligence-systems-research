#!/usr/bin/env python3
"""Frozen analysis for STUDY-ECO-001.

This module intentionally uses only the Python standard library. It validates
one captured execution against the preregistered deterministic gates. It does
not perform payment, custody, settlement, or network actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "aftergraph.study-eco-001-evidence/v1"
RESULT_SCHEMA = "aftergraph.study-eco-001-result/v1"
SHA1_LEN = 40
SHA256_LEN = 64

FROZEN_SUBJECTS = {
    "core_labs_fabric": "688e120dbca382e2329679378649ea5adca9220d",
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


def analyze(evidence: dict[str, Any]) -> dict[str, Any]:
    invalid: list[str] = []
    failures: list[str] = []

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
        observed = subjects.get(key)
        if observed != expected:
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
        invalid.append("preflight_receipt_digest")
    if preflight.get("authorityGranted") is not False:
        failures.append("preflight_authority_escalation")
    if preflight.get("verificationGranted") is not False:
        failures.append("preflight_verification_escalation")
    if preflight.get("scientificValidityGranted") is not False:
        failures.append("preflight_scientific_escalation")

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
        invalid.append("sentinel_verification_digest")

    suites = evidence.get("suites")
    if not isinstance(suites, list):
        invalid.append("suites")
        suites = []
    suite_by_id = {str(item.get("id")): item for item in suites if isinstance(item, dict)}
    if set(suite_by_id) != REQUIRED_SUITES:
        invalid.append("suite_set")
    for suite_id in sorted(REQUIRED_SUITES):
        suite = suite_by_id.get(suite_id, {})
        if suite.get("exitCode") != 0:
            failures.append(f"suite_failed:{suite_id}")
        if not _is_hex(suite.get("outputSha256"), SHA256_LEN):
            invalid.append(f"suite_output_digest:{suite_id}")

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

    if invalid:
        status = "INVALID_RUN"
    elif failures:
        status = "FALSIFIED"
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
        "invalidReasons": sorted(set(invalid)),
        "falsificationReasons": sorted(set(failures)),
    }
    base["resultDigest"] = _sha256_bytes(
        json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    evidence_path = Path(args.evidence)
    out_path = Path(args.out)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    result = analyze(evidence)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "studyId": result["studyId"],
        "status": result["status"],
        "resultDigest": result["resultDigest"],
        "out": str(out_path),
    }, sort_keys=True))
    return 0 if result["status"] == "CONFIRMATORY_SYSTEM_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
