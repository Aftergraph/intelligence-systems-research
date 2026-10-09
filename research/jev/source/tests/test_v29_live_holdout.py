from __future__ import annotations

import pytest

from jev_engineering.campaign_runtime import BenchmarkCostModel, TokenPrice
from jev_engineering.evidence_campaign import EvidenceCampaignPolicy
from jev_engineering.live_holdout import AuthenticatedLiveHoldoutRunner
from jev_engineering.paired_holdout import PairedMission
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


def _missions():
    return [
        PairedMission("a", 1, "shadow", {"prompt": "A"}),
        PairedMission("b", 1, "experiment", {"prompt": "B"}),
        PairedMission("c", 1, "holdout", {"prompt": "C"}),
        PairedMission("d", 1, "holdout", {"prompt": "D"}),
    ]


def _raw(inp, condition, *, origin="live-provider", authenticated=True):
    frontier = condition == "frontier"
    return {
        "status": "verified",
        "metrics": {
            "completion_claims": 1,
            "false_completion_claims": 0,
            "provider_input_tokens": 1000 if frontier else 100,
            "provider_output_tokens": 100 if frontier else 10,
            "decision_input_tokens": 100 if frontier else 10,
            "decision_output_tokens": 10 if frontier else 0,
            "wall_time_ms": 1000,
        },
        "attestation": {
            "provider": "provider-x",
            "model": "model-y",
            "provider_request_id": f"req-{inp.case_id}-{condition}",
            "evidence_origin": origin,
            "transport_security": "https",
            "authenticated": authenticated,
        },
    }


def _costs():
    return BenchmarkCostModel(
        generator=TokenPrice(4.0, 20.0, 0.4),
        decision_by_condition={
            "frontier": TokenPrice(4.0, 20.0, 0.4),
            "jev": TokenPrice(0.042, 0.0, 0.042),
        },
        frontier_decision_conditions=frozenset({"frontier"}),
    )


def test_live_campaign_requires_live_origin_and_authentication():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer, seed=1
    )
    bundle = runner.run(missions=_missions(), run_condition=_raw)
    verifier = Ed25519ReceiptVerifier({"jev-v29-test": signer.public_key_bytes()})
    assert bundle.live_provider_measurement is True
    assert bundle.execution.live_provider_measurement is True
    assert bundle.verify(verifier) is True
    assert len(bundle.signed_executions) == 8


def test_synthetic_signed_callback_cannot_claim_live_measurement():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(
        missions=_missions(),
        run_condition=lambda i, c: _raw(i, c, origin="synthetic", authenticated=True),
    )
    assert bundle.live_provider_measurement is False


def test_unauthenticated_callback_cannot_claim_live_measurement():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(
        missions=_missions(),
        run_condition=lambda i, c: _raw(i, c, authenticated=False),
    )
    assert bundle.live_provider_measurement is False


def test_missing_attestation_fails_closed():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    with pytest.raises(ValueError, match="attestation"):
        runner.run(
            missions=_missions(),
            run_condition=lambda i, c: {
                "status": "verified",
                "metrics": {
                    "completion_claims": 1,
                    "false_completion_claims": 0,
                    "provider_input_tokens": 1,
                    "provider_output_tokens": 1,
                    "decision_input_tokens": 1,
                    "decision_output_tokens": 1,
                    "wall_time_ms": 1,
                },
            },
        )


def test_tampered_receipt_fails_verification():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(missions=_missions(), run_condition=_raw)
    first = bundle.signed_executions[0].receipt
    bad = PublicSignedReceipt(
        payload={**first.payload, "status": "tampered"},
        key_id=first.key_id,
        algorithm=first.algorithm,
        payload_sha256=first.payload_sha256,
        signature_b64=first.signature_b64,
    )
    verifier = Ed25519ReceiptVerifier({"jev-v29-test": signer.public_key_bytes()})
    assert verifier.verify(bad) is False


def test_verified_evaluation_sets_authenticated_live_flag():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(missions=_missions(), run_condition=_raw)
    verifier = Ed25519ReceiptVerifier({"jev-v29-test": signer.public_key_bytes()})
    report = bundle.evaluate_verified(
        verifier=verifier,
        incumbent_condition="frontier",
        candidate_condition="jev",
        cost_model=_costs(),
        policy=EvidenceCampaignPolicy(
            min_holdout_pairs=2,
            noninferiority_margin=0.05,
            max_fcr=0.0,
            min_fie_ratio=1.0,
            target_fie_ratio=10.0,
            bootstrap_samples=100,
            bootstrap_seed=1,
        ),
    )
    assert report["authenticated_live_ab_executed"] is True
    assert report["evidence_bundle_sha256"] == bundle.campaign_sha256


def test_non_live_bundle_cannot_enter_verified_evaluator():
    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(
        missions=_missions(),
        run_condition=lambda i, c: _raw(i, c, origin="synthetic"),
    )
    verifier = Ed25519ReceiptVerifier({"jev-v29-test": signer.public_key_bytes()})
    with pytest.raises(ValueError, match="not authenticated live-provider evidence"):
        bundle.evaluate_verified(
            verifier=verifier,
            incumbent_condition="frontier",
            candidate_condition="jev",
            cost_model=_costs(),
        )


def test_tampered_execution_object_fails_bundle_verification():
    from jev_engineering.paired_holdout import PairedCampaignExecution
    from jev_engineering.live_holdout import LiveCampaignEvidenceBundle

    signer = Ed25519ReceiptSigner.generate(key_id="jev-v29-test")
    runner = AuthenticatedLiveHoldoutRunner(
        incumbent_condition="frontier", candidate_condition="jev", signer=signer
    )
    bundle = runner.run(missions=_missions(), run_condition=_raw)
    verifier = Ed25519ReceiptVerifier({"jev-v29-test": signer.public_key_bytes()})
    records = list(bundle.execution.records)
    records[0] = {**records[0], "status": "tampered"}
    tampered_execution = PairedCampaignExecution(
        records=tuple(records),
        pair_execution_order=bundle.execution.pair_execution_order,
        shadow_pairs=bundle.execution.shadow_pairs,
        experiment_pairs=bundle.execution.experiment_pairs,
        holdout_pairs=bundle.execution.holdout_pairs,
        seed=bundle.execution.seed,
        live_provider_measurement=bundle.execution.live_provider_measurement,
    )
    tampered = LiveCampaignEvidenceBundle(
        execution=tampered_execution,
        signed_executions=bundle.signed_executions,
        signer_key_id=bundle.signer_key_id,
        campaign_sha256=bundle.campaign_sha256,
        live_provider_measurement=bundle.live_provider_measurement,
    )
    assert tampered.verify(verifier) is False
