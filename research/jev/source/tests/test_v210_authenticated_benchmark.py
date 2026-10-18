from __future__ import annotations

import json
from pathlib import Path

import pytest

from jev_engineering.authenticated_benchmark import bundle_from_dict, seal_authenticated_benchmark
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def _manifest(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.yaml"
    p.write_text(
        """version: 1
name: v210-test
conditions:
  - id: frontier
    config: unused-a.yaml
  - id: jev
    config: unused-b.yaml
cases:
  - id: a
    source: case-a
    task: repair a
    verify: python -m pytest -q
  - id: b
    source: case-b
    task: repair b
    verify: python -m pytest -q
""",
        encoding="utf-8",
    )
    return p


def _rows(live: bool = True):
    rows = []
    for repeat, case, order in [(1, "a", ("jev", "frontier")), (1, "b", ("frontier", "jev"))]:
        for index, condition in enumerate(order):
            rows.append({
                "condition": condition,
                "case_id": case,
                "repeat": repeat,
                "randomized_order_index": index,
                "status": "verified",
                "model": "provider-model",
                "provider": "provider-x",
                "provider_request_ids": [f"req-{case}-{condition}-1", f"req-{case}-{condition}-2"],
                "provider_authenticated": live,
                "transport_security": "https" if live else "local-or-plaintext",
                "metrics": {
                    "completion_claims": 1,
                    "false_completion_claims": 0,
                    "provider_input_tokens": 100,
                    "provider_output_tokens": 10,
                    "decision_input_tokens": 10,
                    "decision_output_tokens": 1,
                    "wall_time_ms": 1000,
                },
            })
    return rows


def test_seals_real_request_lineage_and_roundtrips(tmp_path):
    signer = Ed25519ReceiptSigner.generate(key_id="v210-test")
    bundle = seal_authenticated_benchmark(
        manifest_path=_manifest(tmp_path), records=_rows(), signer=signer,
        incumbent_condition="frontier", candidate_condition="jev",
        shadow_pairs=0, experiment_pairs=0, holdout_pairs=2, seed=7,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    assert bundle.live_provider_measurement is True
    assert bundle.verify(verifier) is True
    assert len(bundle.signed_executions) == 4
    first = bundle.signed_executions[0].receipt.payload
    assert first["receipt_version"] == 2
    assert first["provider_request_count"] == 2
    assert first["provider_request_id"].startswith("request-set:sha256:")
    restored = bundle_from_dict(json.loads(json.dumps(bundle.to_dict())))
    assert restored.verify(verifier) is True


def test_missing_request_lineage_fails_live_claim(tmp_path):
    rows = _rows()
    rows[0]["provider_request_ids"] = []
    signer = Ed25519ReceiptSigner.generate(key_id="v210-test")
    bundle = seal_authenticated_benchmark(
        manifest_path=_manifest(tmp_path), records=rows, signer=signer,
        incumbent_condition="frontier", candidate_condition="jev",
        shadow_pairs=0, experiment_pairs=0, holdout_pairs=2, seed=7,
    )
    assert bundle.live_provider_measurement is False


def test_tampered_request_lineage_fails_bundle_verification(tmp_path):
    signer = Ed25519ReceiptSigner.generate(key_id="v210-test")
    bundle = seal_authenticated_benchmark(
        manifest_path=_manifest(tmp_path), records=_rows(), signer=signer,
        incumbent_condition="frontier", candidate_condition="jev",
        shadow_pairs=0, experiment_pairs=0, holdout_pairs=2, seed=7,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    payload = bundle.to_dict()
    payload["execution"]["records"][0]["attestation"]["provider_request_ids"][0] = "tampered"
    restored = bundle_from_dict(payload)
    assert restored.verify(verifier) is False


def test_pair_count_schedule_fails_closed(tmp_path):
    signer = Ed25519ReceiptSigner.generate(key_id="v210-test")
    with pytest.raises(ValueError, match="phase schedule"):
        seal_authenticated_benchmark(
            manifest_path=_manifest(tmp_path), records=_rows(), signer=signer,
            incumbent_condition="frontier", candidate_condition="jev",
            shadow_pairs=1, experiment_pairs=1, holdout_pairs=1, seed=7,
        )
