from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .benchmark import load_manifest, read_jsonl, run_manifest
from .live_holdout import LiveCampaignEvidenceBundle, SignedProviderExecution
from .paired_holdout import PairedCampaignExecution
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


def _canonical_hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _payload_hashes(manifest_path: str | Path) -> dict[str, str]:
    manifest = load_manifest(manifest_path)
    return {
        str(case["id"]): _canonical_hash(
            {
                "case_id": str(case["id"]),
                "task": str(case.get("task") or ""),
                "source": str(case.get("source") or ""),
                "verify": str(case.get("verify") or "python -m pytest -q"),
            }
        )
        for case in manifest["cases"]
    }


def _phase_by_pair(
    pair_keys: list[tuple[int, str]], *, shadow_pairs: int, experiment_pairs: int, holdout_pairs: int
) -> dict[tuple[int, str], str]:
    if min(shadow_pairs, experiment_pairs, holdout_pairs) < 0:
        raise ValueError("phase pair counts cannot be negative")
    expected = shadow_pairs + experiment_pairs + holdout_pairs
    if len(pair_keys) != expected:
        raise ValueError(f"phase schedule requires {expected} pairs; observed {len(pair_keys)}")
    phases = (["shadow"] * shadow_pairs) + (["experiment"] * experiment_pairs) + (["holdout"] * holdout_pairs)
    return dict(zip(sorted(pair_keys), phases, strict=True))


def _request_set_id(request_ids: Iterable[str]) -> str:
    ids = [str(x).strip() for x in request_ids if str(x).strip()]
    if not ids:
        raise ValueError("authenticated provider evidence requires at least one provider request id")
    return "request-set:sha256:" + _canonical_hash(ids)


def seal_authenticated_benchmark(
    *,
    manifest_path: str | Path,
    records: Iterable[Mapping[str, Any]],
    signer: Ed25519ReceiptSigner,
    incumbent_condition: str,
    candidate_condition: str,
    shadow_pairs: int,
    experiment_pairs: int,
    holdout_pairs: int,
    seed: int,
) -> LiveCampaignEvidenceBundle:
    """Convert a completed provider-backed coding benchmark into signed paired evidence.

    This function does not infer liveness from a signature. Every execution must already carry
    provider-issued request ids, authenticated credential state, HTTPS transport, and deterministic
    verifier output from ``run_manifest``. Missing provenance fails closed.
    """
    rows = [dict(r) for r in records]
    if not rows:
        raise ValueError("benchmark records are empty")
    allowed = {incumbent_condition, candidate_condition}
    rows = [r for r in rows if str(r.get("condition") or "") in allowed]
    pair_keys = sorted({(int(r.get("repeat") or 0), str(r.get("case_id") or "")) for r in rows})
    if any(repeat <= 0 or not case for repeat, case in pair_keys):
        raise ValueError("benchmark records require positive repeat and case_id")
    phase_map = _phase_by_pair(
        pair_keys,
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout_pairs,
    )
    payload_hashes = _payload_hashes(manifest_path)

    keyed: dict[tuple[int, str, str], dict[str, Any]] = {}
    orders: dict[tuple[int, str], list[tuple[int, str]]] = {}
    normalized: list[dict[str, Any]] = []
    attestations: dict[tuple[int, str, str], dict[str, Any]] = {}
    all_live = True
    decision_lineage_present = any("decision_provider" in r for r in rows)

    required_metrics = (
        "completion_claims", "false_completion_claims", "provider_input_tokens",
        "provider_output_tokens", "decision_input_tokens", "decision_output_tokens", "wall_time_ms",
    )
    for row in rows:
        repeat = int(row.get("repeat") or 0)
        case_id = str(row.get("case_id") or "")
        condition = str(row.get("condition") or "")
        identity = (repeat, case_id, condition)
        if identity in keyed:
            raise ValueError(f"duplicate benchmark execution: {identity}")
        keyed[identity] = row
        if case_id not in payload_hashes:
            raise ValueError(f"case {case_id!r} is absent from benchmark manifest")
        metrics = dict(row.get("metrics") or {})
        missing = [name for name in required_metrics if name not in metrics]
        if missing:
            raise ValueError(f"benchmark execution missing metrics: {', '.join(missing)}")
        request_ids = [str(x) for x in (row.get("provider_request_ids") or []) if str(x).strip()]
        provider = str(row.get("provider") or "")
        model = str(row.get("model") or "")
        authenticated = bool(row.get("provider_authenticated", False))
        transport = str(row.get("transport_security") or "")
        if not provider or not model or not request_ids:
            all_live = False
        if not authenticated or transport != "https":
            all_live = False
        decision_provider = str(row.get("decision_provider") or "")
        decision_model = str(row.get("decision_model") or "")
        decision_request_ids = [str(x) for x in (row.get("decision_request_ids") or []) if str(x).strip()]
        decision_authenticated = bool(row.get("decision_authenticated", False))
        decision_transport = str(row.get("decision_transport_security") or "")
        decision_live = (
            bool(decision_provider)
            and bool(decision_model)
            and bool(decision_request_ids)
            and decision_authenticated
            and decision_transport == "https"
        )
        if decision_lineage_present and not decision_live:
            all_live = False
        attestation = {
            "provider": provider,
            "model": model,
            "provider_request_id": _request_set_id(request_ids) if request_ids else "missing",
            "provider_request_ids": request_ids,
            "evidence_origin": "live-provider" if authenticated and transport == "https" and request_ids else "replay",
            "transport_security": transport,
            "authenticated": authenticated and transport == "https" and bool(request_ids),
            "decision_provider": decision_provider,
            "decision_model": decision_model,
            "decision_request_id": _request_set_id(decision_request_ids) if decision_request_ids else "missing",
            "decision_request_ids": decision_request_ids,
            "decision_transport_security": decision_transport,
            "decision_authenticated": decision_live,
        }
        attestations[identity] = attestation
        order_index = int(row.get("randomized_order_index") or 0)
        orders.setdefault((repeat, case_id), []).append((order_index, condition))
        normalized.append(
            {
                **row,
                "phase": phase_map[(repeat, case_id)],
                "payload_sha256": payload_hashes[case_id],
                "pair_execution_order": order_index + 1,
                "attestation": attestation,
            }
        )

    expected_identities = {
        (repeat, case_id, condition)
        for repeat, case_id in pair_keys
        for condition in (incumbent_condition, candidate_condition)
    }
    if set(keyed) != expected_identities:
        missing = sorted(expected_identities - set(keyed))
        raise ValueError(f"paired benchmark is incomplete; missing {missing}")

    pair_execution_order: list[tuple[str, str]] = []
    for key in sorted(pair_keys):
        ordered = tuple(condition for _, condition in sorted(orders[key]))
        if len(ordered) != 2 or set(ordered) != allowed:
            raise ValueError(f"invalid pair execution order for {key}")
        pair_execution_order.append(ordered)

    execution = PairedCampaignExecution(
        records=tuple(sorted(normalized, key=lambda r: (int(r["repeat"]), str(r["case_id"]), int(r["pair_execution_order"])))),
        pair_execution_order=tuple(pair_execution_order),
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout_pairs,
        seed=seed,
        live_provider_measurement=all_live,
    )
    campaign_sha256 = _canonical_hash(execution.to_dict())
    signed: list[SignedProviderExecution] = []
    for record in execution.records:
        identity = (int(record["repeat"]), str(record["case_id"]), str(record["condition"]))
        attestation = attestations[identity]
        request_ids = list(attestation["provider_request_ids"])
        payload = {
            "receipt_version": 3 if decision_lineage_present else 2,
            "campaign_sha256": campaign_sha256,
            "signer_key_id": signer.key_id,
            "case_id": record["case_id"],
            "repeat": record["repeat"],
            "condition": record["condition"],
            "payload_sha256": record["payload_sha256"],
            "pair_execution_order": record["pair_execution_order"],
            "status": record["status"],
            "metrics_sha256": _canonical_hash(record["metrics"]),
            "provider": attestation["provider"],
            "model": attestation["model"],
            "provider_request_id": attestation["provider_request_id"],
            "provider_request_count": len(request_ids),
            "provider_request_ids_sha256": _canonical_hash(request_ids),
            "evidence_origin": attestation["evidence_origin"],
            "transport_security": attestation["transport_security"],
            "provider_authenticated": attestation["authenticated"],
        }
        if decision_lineage_present:
            decision_ids = list(attestation["decision_request_ids"])
            payload.update({
                "decision_provider": attestation["decision_provider"],
                "decision_model": attestation["decision_model"],
                "decision_request_id": attestation["decision_request_id"],
                "decision_request_count": len(decision_ids),
                "decision_request_ids_sha256": _canonical_hash(decision_ids),
                "decision_transport_security": attestation["decision_transport_security"],
                "decision_authenticated": attestation["decision_authenticated"],
            })
        signed.append(SignedProviderExecution(signer.sign(payload)))
    return LiveCampaignEvidenceBundle(
        execution=execution,
        signed_executions=tuple(signed),
        signer_key_id=signer.key_id,
        campaign_sha256=campaign_sha256,
        live_provider_measurement=all_live,
    )


def run_and_seal_authenticated_benchmark(
    *,
    manifest_path: str | Path,
    output_dir: str | Path,
    signer: Ed25519ReceiptSigner,
    incumbent_condition: str,
    candidate_condition: str,
    repeats: int,
    shadow_pairs: int,
    experiment_pairs: int,
    holdout_pairs: int,
    seed: int = 20260925,
) -> LiveCampaignEvidenceBundle:
    out = Path(output_dir)
    run_manifest(manifest_path, output_dir=out, repeats=repeats, seed=seed)
    records = read_jsonl(out / "results.jsonl")
    bundle = seal_authenticated_benchmark(
        manifest_path=manifest_path,
        records=records,
        signer=signer,
        incumbent_condition=incumbent_condition,
        candidate_condition=candidate_condition,
        shadow_pairs=shadow_pairs,
        experiment_pairs=experiment_pairs,
        holdout_pairs=holdout_pairs,
        seed=seed,
    )
    (out / "authenticated-live-evidence.v1.json").write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "evidence-public-key.raw").write_bytes(signer.public_key_bytes())
    return bundle


def bundle_from_dict(payload: Mapping[str, Any]) -> LiveCampaignEvidenceBundle:
    execution_raw = dict(payload.get("execution") or {})
    allocation = dict(execution_raw.get("phase_allocation") or {})
    execution = PairedCampaignExecution(
        records=tuple(dict(x) for x in execution_raw.get("records") or []),
        pair_execution_order=tuple(tuple(x) for x in execution_raw.get("pair_execution_order") or []),
        shadow_pairs=int(allocation.get("shadow") or 0),
        experiment_pairs=int(allocation.get("experiment") or 0),
        holdout_pairs=int(allocation.get("holdout") or 0),
        seed=int(execution_raw.get("seed") or 0),
        live_provider_measurement=bool(execution_raw.get("live_provider_measurement", False)),
    )
    signed = tuple(
        SignedProviderExecution(
            PublicSignedReceipt(
                payload=dict(item["receipt"]["payload"]) if "receipt" in item else dict(item["payload"]),
                key_id=str((item.get("receipt") or item).get("key_id") or ""),
                algorithm=str((item.get("receipt") or item).get("algorithm") or ""),
                payload_sha256=str((item.get("receipt") or item).get("payload_sha256") or ""),
                signature_b64=str((item.get("receipt") or item).get("signature_b64") or ""),
            )
        )
        for item in payload.get("signed_executions") or []
    )
    return LiveCampaignEvidenceBundle(
        execution=execution,
        signed_executions=signed,
        signer_key_id=str(payload.get("signer_key_id") or ""),
        campaign_sha256=str(payload.get("campaign_sha256") or ""),
        live_provider_measurement=bool(payload.get("live_provider_measurement", False)),
    )


def verify_bundle_file(*, bundle_path: str | Path, public_key_path: str | Path) -> bool:
    bundle = bundle_from_dict(json.loads(Path(bundle_path).read_text(encoding="utf-8")))
    verifier = Ed25519ReceiptVerifier({bundle.signer_key_id: Path(public_key_path).read_bytes()})
    return bundle.verify(verifier)