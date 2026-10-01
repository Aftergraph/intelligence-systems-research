import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "experiments" / "economic_authority" / "study_eco_001.py"
spec = importlib.util.spec_from_file_location("study_eco_001", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def _seal(document, field):
    base = {key: value for key, value in document.items() if key != field}
    return {
        **base,
        field: hashlib.sha256(mod.canonical_json(base).encode("utf-8")).hexdigest(),
    }


def _valid(tmp_path: Path):
    preflight = _seal({
        "schemaVersion": "aftergraph.labs-preflight/v1",
        "generatedAt": "2026-10-01T02:30:00.000Z",
        "state": "OBSERVED",
        "requiredAdapterIds": ["core", "fihim-eval-lab", "runtime", "trust-gateway", "works"],
        "observedAdapterIds": ["core", "fihim-eval-lab", "runtime", "trust-gateway", "works"],
        "missingAdapterIds": [],
        "httpBundle": {"unresolvedTargets": []},
        "artifactObservations": [],
        "sutBinding": None,
        "authorityGranted": False,
        "verificationGranted": False,
        "scientificValidityGranted": False,
        "maximumClaim": "OBSERVED",
    }, "receiptDigest")
    (tmp_path / "labs-preflight.json").write_text(json.dumps(preflight), encoding="utf-8")

    verification = _seal({
        "schemaVersion": "aftergraph.sentinel-labs-preflight-verification/v1",
        "valid": True,
        "state": "VERIFIED_OBSERVATIONAL_PREFLIGHT",
        "sourceReceiptDigest": preflight["receiptDigest"],
        "sourceState": "OBSERVED",
        "coverageComplete": True,
        "exactSubjectCount": 5,
        "authorityGranted": False,
        "promotionAuthority": False,
        "scientificValidityGranted": False,
        "reasons": [],
    }, "verificationDigest")
    (tmp_path / "sentinel-verification.json").write_text(
        json.dumps(verification), encoding="utf-8"
    )

    suites = []
    for suite in sorted(mod.REQUIRED_SUITES):
        output_path = f"{suite}.log"
        payload = f"{suite}:PASS\n".encode()
        (tmp_path / output_path).write_bytes(payload)
        suites.append({
            "id": suite,
            "exitCode": 0,
            "outputPath": output_path,
            "outputSha256": hashlib.sha256(payload).hexdigest(),
        })

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
            "receiptPath": "labs-preflight.json",
            "receiptDigest": preflight["receiptDigest"],
            "authorityGranted": False,
            "verificationGranted": False,
            "scientificValidityGranted": False,
        },
        "sentinelVerification": {
            "state": "VERIFIED_OBSERVATIONAL_PREFLIGHT",
            "valid": True,
            "coverageComplete": True,
            "verificationPath": "sentinel-verification.json",
            "verificationDigest": verification["verificationDigest"],
            "promotionAuthority": False,
            "scientificValidityGranted": False,
        },
        "suites": suites,
        "externalEffects": 0,
        "realAssetMovement": False,
        "liveMoneyMovement": False,
        "economicFinalityGranted": False,
        "promotionAuthority": False,
        "scientificValidityGranted": False,
    }


def test_valid_frozen_execution_passes(tmp_path):
    out = mod.analyze(_valid(tmp_path), tmp_path)
    assert out["status"] == "CONFIRMATORY_SYSTEM_PASS"
    assert out["primaryGatesPassed"] is True
    assert out["rawPreflightBound"] is True
    assert out["e5OrE6Claim"] is False


def test_any_semantic_suite_failure_falsifies(tmp_path):
    ev = _valid(tmp_path)
    ev["suites"][0]["exitCode"] = 1
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert any(reason.startswith("suite_failed:") for reason in out["falsificationReasons"])


def test_package_drift_invalidates_before_semantic_failure(tmp_path):
    ev = _valid(tmp_path)
    ev["corePackageDiffEmptyFromFreeze"] = False
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "INVALID_RUN"
    assert "core_package_drift" in out["invalidReasons"]


def test_missing_coverage_cannot_be_promoted(tmp_path):
    ev = _valid(tmp_path)
    ev["preflight"]["state"] = "INCOMPLETE"
    ev["preflight"]["missingAdapterCount"] = 1
    ev["sentinelVerification"]["coverageComplete"] = False
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert "preflight_state" in out["falsificationReasons"]
    assert "sentinel_incomplete" in out["falsificationReasons"]


def test_external_effect_or_finality_claim_falsifies(tmp_path):
    ev = _valid(tmp_path)
    ev["externalEffects"] = 1
    ev["economicFinalityGranted"] = True
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert "external_effects" in out["falsificationReasons"]
    assert "economic_finality_escalation" in out["falsificationReasons"]


def test_wrong_frozen_subject_invalidates_run(tmp_path):
    ev = _valid(tmp_path)
    ev["sourceCommits"]["works_execution"] = "0" * 40
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "INVALID_RUN"
    assert "source_commit:works_execution" in out["invalidReasons"]


def test_arbitrary_summary_digest_cannot_pass(tmp_path):
    ev = _valid(tmp_path)
    ev["preflight"]["receiptDigest"] = "0" * 64
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert "preflight_summary:receipt_digest_mismatch" in out["falsificationReasons"]


def test_raw_preflight_tampering_is_falsification(tmp_path):
    ev = _valid(tmp_path)
    raw = json.loads((tmp_path / "labs-preflight.json").read_text())
    raw["state"] = "INCOMPLETE"
    (tmp_path / "labs-preflight.json").write_text(json.dumps(raw))
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert "preflight_raw:receipt_digest_mismatch" in out["falsificationReasons"]


def test_suite_output_tampering_is_falsification(tmp_path):
    ev = _valid(tmp_path)
    suite = ev["suites"][0]
    (tmp_path / suite["outputPath"]).write_text("tampered\n")
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert f"suite_output_digest_mismatch:{suite['id']}" in out["falsificationReasons"]


def test_duplicate_failed_suite_cannot_be_erased_by_later_pass(tmp_path):
    ev = _valid(tmp_path)
    failed = copy.deepcopy(ev["suites"][0])
    failed["exitCode"] = 1
    ev["suites"] = [failed, *ev["suites"]]
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert f"duplicate_suite:{failed['id']}" in out["falsificationReasons"]
    assert f"suite_failed:{failed['id']}" in out["falsificationReasons"]


def test_semantic_failure_outranks_malformed_metadata(tmp_path):
    ev = _valid(tmp_path)
    ev["sourceCommits"]["runtime"] = "bad"
    ev["suites"][0]["exitCode"] = 1
    ev["suites"][0]["outputSha256"] = "bad"
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert "source_commit:runtime" in out["invalidReasons"]
    assert any(reason.startswith("suite_failed:") for reason in out["falsificationReasons"])


def test_path_traversal_is_rejected(tmp_path):
    ev = _valid(tmp_path)
    outside = tmp_path.parent / "outside.log"
    outside.write_text("outside")
    ev["suites"][0]["outputPath"] = "../outside.log"
    out = mod.analyze(ev, tmp_path)
    assert out["status"] == "FALSIFIED"
    assert any(reason.endswith(":path_escape") for reason in out["falsificationReasons"])
