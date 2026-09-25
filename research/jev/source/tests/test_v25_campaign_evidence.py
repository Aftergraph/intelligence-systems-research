from __future__ import annotations

import json

from jev_engineering.campaign_evidence import CampaignEvidenceBundle


def test_campaign_evidence_bundle_detects_tampering(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    pricing = tmp_path / "pricing.json"
    results = tmp_path / "results.jsonl"
    report = tmp_path / "report.json"
    for path, text in [
        (manifest, "name: demo\n"),
        (pricing, '{"price":1}\n'),
        (results, '{"case":"a"}\n'),
        (report, '{"state":"rejected"}\n'),
    ]:
        path.write_text(text, encoding="utf-8")
    target = tmp_path / "evidence.json"
    bundle = CampaignEvidenceBundle.create(
        manifest=manifest,
        pricing=pricing,
        results=results,
        report=report,
        output=target,
        package_version="2.5.0",
    )
    assert bundle.verify(base_dir=tmp_path)["valid"] is True
    payload = json.loads(target.read_text())
    assert payload["files"]["results"]["sha256"]

    results.write_text('{"case":"tampered"}\n', encoding="utf-8")
    checked = CampaignEvidenceBundle.load(target).verify(base_dir=tmp_path)
    assert checked["valid"] is False
    assert "results" in checked["mismatches"]
