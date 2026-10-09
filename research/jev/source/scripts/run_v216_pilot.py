from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from jev_engineering.authenticated_benchmark import run_and_seal_authenticated_benchmark
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier


def main() -> int:
    encoded = os.environ.get("JEV_EVIDENCE_SIGNING_KEY_B64", "")
    if not encoded:
        raise RuntimeError("JEV_EVIDENCE_SIGNING_KEY_B64 is required")
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != 32:
        raise RuntimeError("evidence signing key must be 32 bytes")
    signer = Ed25519ReceiptSigner.from_private_key_bytes(key_id="aftergraph-jev-live-v216", raw=raw)
    out = Path(os.environ.get("JEV_V216_OUTPUT_DIR", "live-pilot-v216-results"))
    bundle = run_and_seal_authenticated_benchmark(
        manifest_path="benchmarks/hermes_qwen_control_plane_ablation.yaml",
        output_dir=out,
        signer=signer,
        incumbent_condition="qwen-frontier-control",
        candidate_condition="qwen-jev-control",
        repeats=1,
        shadow_pairs=1,
        experiment_pairs=1,
        holdout_pairs=3,
        seed=20260926,
    )
    verifier = Ed25519ReceiptVerifier({signer.key_id: signer.public_key_bytes()})
    verified = bundle.verify(verifier)
    records = list(bundle.execution.records)
    summary = {
        "schema": "aftergraph.v216-live-paired-pilot/1.0",
        "pairs": 5,
        "executions": len(records),
        "verified_executions": sum(1 for r in records if r.get("status") == "verified"),
        "campaign_sha256": bundle.campaign_sha256,
        "receipts_verify": verified,
        "receipt_versions": sorted({int(x.receipt.payload.get("receipt_version") or 1) for x in bundle.signed_executions}),
        "live_provider_measurement": bundle.live_provider_measurement,
        "authenticated_live_ab_executed": bundle.live_provider_measurement and verified,
        "decision_lineage_complete": all(bool((r.get("attestation") or {}).get("decision_request_ids")) for r in records),
        "generation_lineage_complete": all(bool((r.get("attestation") or {}).get("provider_request_ids")) for r in records),
        "powered_performance_claim": False,
        "truth_boundary": "five-pair pilot validates real paired execution and lineage only; it is not a powered performance campaign",
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())