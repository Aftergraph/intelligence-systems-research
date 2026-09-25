from experiments.study015.freeze_manifest import build_freeze_manifest


def test_freeze_manifest_binds_protocol_and_source_heads():
    manifest = build_freeze_manifest(status="DRAFT")
    assert manifest["study_id"] == "STUDY-015"
    assert len(manifest["protocol_sha256"]) == 64
    assert len(manifest["implementation_fingerprint"]) == 64
    assert "runtime" in manifest["source_heads"]
    assert "STUDY-015-PREREGISTRATION.md" in manifest["artifacts"]


def test_frozen_manifest_still_requires_owner_gate():
    manifest = build_freeze_manifest(status="FROZEN")
    assert manifest["status"] == "FROZEN"
    assert manifest["owner_gate_required"] is True
