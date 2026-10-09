from __future__ import annotations

from pathlib import Path

from jev_engineering.authenticated_benchmark import seal_authenticated_benchmark
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def _manifest(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.yaml"
    p.write_text(
        """version: 1
name: v216-lineage
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
""",
        encoding="utf-8",
    )
    return p


def _rows(*, drop_decision: bool = False):
    out = []
    for index, condition in enumerate(("frontier", "jev")):
        decision_provider = "dialagram" if condition == "frontier" else "typesafe"
        row = {
            "condition": condition,
            "case_id": "a",
            "repeat": 1,
            "randomized_order_index": index,
            "status": "verified",
            "model": "qwen-3.8-max-thinking",
            "provider": "dialagram",
            "provider_request_ids": [f"gen-{condition}"],
            "provider_authenticated": True,
            "transport_security": "https",
            "decision_backend": "openai_compatible" if condition == "frontier" else "typesafe",
            "decision_provider": decision_provider,
            "decision_model": "qwen-3.8-max-thinking" if condition == "frontier" else "jev-1.13.0",
            "decision_request_ids": [] if (drop_decision and condition == "jev") else [f"decision-{condition}"],
            "decision_authenticated": True,
            "decision_transport_security": "https",
            "metrics": {
                "completion_claims": 1,
                "false_completion_claims": 0,
                "provider_input_tokens": 100,
                "provider_output_tokens": 10,
                "decision_input_tokens": 10,
                "decision_output_tokens": 1,
                "wall_time_ms": 1000,
            },
        }
        out.append(row)
    return out


def test_receipt_v3_binds_generation_and_decision_lineage(tmp_path: Path):
    signer = Ed25519ReceiptSigner.generate(key_id="v216")
    bundle = seal_authenticated_benchmark(
        manifest_path=_manifest(tmp_path),
        records=_rows(),
        signer=signer,
        incumbent_condition="frontier",
        candidate_condition="jev",
        shadow_pairs=0,
        experiment_pairs=0,
        holdout_pairs=1,
        seed=16,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    assert bundle.live_provider_measurement is True
    assert bundle.verify(verifier) is True
    payload = bundle.signed_executions[0].receipt.payload
    assert payload["receipt_version"] == 3
    assert payload["provider_request_count"] == 1
    assert payload["decision_request_count"] == 1
    assert payload["decision_request_id"].startswith("request-set:sha256:")


def test_missing_candidate_decision_lineage_fails_live_measurement(tmp_path: Path):
    signer = Ed25519ReceiptSigner.generate(key_id="v216")
    bundle = seal_authenticated_benchmark(
        manifest_path=_manifest(tmp_path),
        records=_rows(drop_decision=True),
        signer=signer,
        incumbent_condition="frontier",
        candidate_condition="jev",
        shadow_pairs=0,
        experiment_pairs=0,
        holdout_pairs=1,
        seed=16,
    )
    assert bundle.live_provider_measurement is False