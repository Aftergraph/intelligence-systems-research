import copy
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "economic_authority" / "study_eco_001.py"
spec = importlib.util.spec_from_file_location("study_eco_001", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def _valid():
    return {
        "schemaVersion": "aftergraph.study-eco-001-evidence/v1",
        "studyId": "STUDY-ECO-001",
        "executionId": "eco-confirmatory-001",
        "executedAt": "2026-10-01T02:30:00Z",
        "runner": "self-hosted/linux/x64/aftergraph-ci",
        "sourceCommits": {
            **mod.FROZEN_SUBJECTS,
            "core_workflow": "f" * 40,
        },
        "corePackageDiffEmptyFromFreeze": True,
        "preflight": {
            "state": "OBSERVED",
            "missingAdapterCount": 0,
            "unresolvedTargetCount": 0,
            "receiptDigest": "a" * 64,
            "authorityGranted": False,
            "verificationGranted": False,
            "scientificValidityGranted": False,
        },
        "sentinelVerification": {
            "state": "VERIFIED_OBSERVATIONAL_PREFLIGHT",
            "valid": True,
            "coverageComplete": True,
            "promotionAuthority": False,
            "scientificValidityGranted": False,
            "verificationDigest": "b" * 64,
        },
        "suites": [
            {"id": suite, "exitCode": 0, "outputSha256": hashlib.sha256(suite.encode()).hexdigest()}
            for suite in sorted(mod.REQUIRED_SUITES)
        ],
        "externalEffects": 0,
        "realAssetMovement": False,
        "liveMoneyMovement": False,
        "economicFinalityGranted": False,
        "promotionAuthority": False,
        "scientificValidityGranted": False,
    }


def test_valid_frozen_execution_passes():
    out = mod.analyze(_valid())
    assert out["status"] == "CONFIRMATORY_SYSTEM_PASS"
    assert out["primaryGatesPassed"] is True
    assert out["e5OrE6Claim"] is False
    assert out["scientificValidityGranted"] is False


def test_any_semantic_suite_failure_falsifies():
    ev = _valid()
    ev["suites"][0]["exitCode"] = 1
    out = mod.analyze(ev)
    assert out["status"] == "FALSIFIED"
    assert any(reason.startswith("suite_failed:") for reason in out["falsificationReasons"])


def test_package_drift_invalidates_instead_of_being_posthoc_failure():
    ev = _valid()
    ev["corePackageDiffEmptyFromFreeze"] = False
    out = mod.analyze(ev)
    assert out["status"] == "INVALID_RUN"
    assert "core_package_drift" in out["invalidReasons"]


def test_missing_coverage_cannot_be_promoted():
    ev = _valid()
    ev["preflight"]["state"] = "INCOMPLETE"
    ev["preflight"]["missingAdapterCount"] = 1
    ev["sentinelVerification"]["coverageComplete"] = False
    out = mod.analyze(ev)
    assert out["status"] == "FALSIFIED"
    assert "preflight_state" in out["falsificationReasons"]
    assert "sentinel_incomplete" in out["falsificationReasons"]


def test_external_effect_or_finality_claim_falsifies():
    ev = _valid()
    ev["externalEffects"] = 1
    ev["economicFinalityGranted"] = True
    out = mod.analyze(ev)
    assert out["status"] == "FALSIFIED"
    assert "external_effects" in out["falsificationReasons"]
    assert "economic_finality_escalation" in out["falsificationReasons"]


def test_wrong_frozen_subject_invalidates_run():
    ev = _valid()
    ev["sourceCommits"]["works_execution"] = "0" * 40
    out = mod.analyze(ev)
    assert out["status"] == "INVALID_RUN"
    assert "source_commit:works_execution" in out["invalidReasons"]
