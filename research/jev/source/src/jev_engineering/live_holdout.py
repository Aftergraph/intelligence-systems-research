from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence

from .campaign_runtime import BenchmarkCostModel
from .evidence_campaign import EvidenceCampaignPolicy
from .paired_holdout import PairedCampaignExecution, PairedHoldoutCampaignRunner, PairedMission, PairedMissionInput
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt

_ALLOWED_ORIGINS = {"live-provider", "synthetic", "replay"}
_ALLOWED_TRANSPORTS = {"https", "mtls"}


def _canonical_hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProviderExecutionAttestation:
    provider: str
    model: str
    provider_request_id: str
    evidence_origin: str
    transport_security: str
    authenticated: bool

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip() or not self.provider_request_id.strip():
            raise ValueError("provider, model, and provider_request_id must be non-empty")
        if self.evidence_origin not in _ALLOWED_ORIGINS:
            raise ValueError("unsupported evidence_origin")
        if self.transport_security not in _ALLOWED_TRANSPORTS:
            raise ValueError("transport_security must be https or mtls")

    @property
    def qualifies_as_live(self) -> bool:
        return self.authenticated and self.evidence_origin == "live-provider"


@dataclass(frozen=True, slots=True)
class SignedProviderExecution:
    receipt: PublicSignedReceipt

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.receipt)


@dataclass(frozen=True, slots=True)
class LiveCampaignEvidenceBundle:
    execution: PairedCampaignExecution
    signed_executions: tuple[SignedProviderExecution, ...]
    signer_key_id: str
    campaign_sha256: str
    live_provider_measurement: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "execution": self.execution.to_dict(),
            "signed_executions": [item.to_dict() for item in self.signed_executions],
            "signer_key_id": self.signer_key_id,
            "campaign_sha256": self.campaign_sha256,
            "live_provider_measurement": self.live_provider_measurement,
            "truth_boundary": (
                "live_provider_measurement is true only when every paired execution is authenticated, "
                "declares evidence_origin=live-provider, and its Ed25519 receipt verifies; promotion "
                "still requires the reserved holdout evaluator"
            ),
        }

    def verify(self, verifier: Ed25519ReceiptVerifier) -> bool:
        if not self.signed_executions:
            return False
        if _canonical_hash(self.execution.to_dict()) != self.campaign_sha256:
            return False
        if len(self.signed_executions) != len(self.execution.records):
            return False
        if any(not verifier.verify(item.receipt) for item in self.signed_executions):
            return False
        by_identity = {
            (int(r["repeat"]), str(r["case_id"]), str(r["condition"])): r
            for r in self.execution.records
        }
        if len(by_identity) != len(self.execution.records):
            return False
        for item in self.signed_executions:
            p = item.receipt.payload
            if item.receipt.key_id != self.signer_key_id:
                return False
            if str(p.get("campaign_sha256") or "") != self.campaign_sha256:
                return False
            if str(p.get("signer_key_id") or "") != self.signer_key_id:
                return False
            identity = (int(p.get("repeat") or 0), str(p.get("case_id") or ""), str(p.get("condition") or ""))
            record = by_identity.get(identity)
            if record is None:
                return False
            if str(p.get("payload_sha256") or "") != str(record.get("payload_sha256") or ""):
                return False
            if int(p.get("pair_execution_order") or 0) != int(record.get("pair_execution_order") or 0):
                return False
            if str(p.get("status") or "") != str(record.get("status") or ""):
                return False
            if str(p.get("metrics_sha256") or "") != _canonical_hash(record.get("metrics") or {}):
                return False
            if int(p.get("receipt_version") or 1) >= 2:
                attestation = record.get("attestation") or {}
                if not isinstance(attestation, Mapping):
                    return False
                if str(p.get("provider") or "") != str(attestation.get("provider") or ""):
                    return False
                if str(p.get("model") or "") != str(attestation.get("model") or ""):
                    return False
                if str(p.get("provider_request_id") or "") != str(attestation.get("provider_request_id") or ""):
                    return False
                request_ids = [str(x) for x in (attestation.get("provider_request_ids") or [])]
                if int(p.get("provider_request_count") or 0) != len(request_ids):
                    return False
                if str(p.get("provider_request_ids_sha256") or "") != _canonical_hash(request_ids):
                    return False
                if str(p.get("evidence_origin") or "") != str(attestation.get("evidence_origin") or ""):
                    return False
                if str(p.get("transport_security") or "") != str(attestation.get("transport_security") or ""):
                    return False
                if bool(p.get("provider_authenticated", False)) != bool(attestation.get("authenticated", False)):
                    return False
                if int(p.get("receipt_version") or 1) >= 3:
                    decision_ids = [str(x) for x in (attestation.get("decision_request_ids") or [])]
                    if str(p.get("decision_provider") or "") != str(attestation.get("decision_provider") or ""):
                        return False
                    if str(p.get("decision_model") or "") != str(attestation.get("decision_model") or ""):
                        return False
                    if str(p.get("decision_request_id") or "") != str(attestation.get("decision_request_id") or ""):
                        return False
                    if int(p.get("decision_request_count") or 0) != len(decision_ids):
                        return False
                    if str(p.get("decision_request_ids_sha256") or "") != _canonical_hash(decision_ids):
                        return False
                    if str(p.get("decision_transport_security") or "") != str(attestation.get("decision_transport_security") or ""):
                        return False
                    if bool(p.get("decision_authenticated", False)) != bool(attestation.get("decision_authenticated", False)):
                        return False
                if self.live_provider_measurement and not (
                    bool(attestation.get("authenticated", False))
                    and str(attestation.get("evidence_origin") or "") == "live-provider"
                    and str(attestation.get("transport_security") or "") == "https"
                    and bool(request_ids)
                    and (
                        int(p.get("receipt_version") or 1) < 3
                        or (
                            bool(attestation.get("decision_authenticated", False))
                            and str(attestation.get("decision_transport_security") or "") == "https"
                            and bool(attestation.get("decision_request_ids") or [])
                        )
                    )
                ):
                    return False
        return True

    def evaluate_verified(
        self,
        *,
        verifier: Ed25519ReceiptVerifier,
        incumbent_condition: str,
        candidate_condition: str,
        cost_model: BenchmarkCostModel,
        policy: EvidenceCampaignPolicy | None = None,
    ) -> dict[str, Any]:
        if not self.live_provider_measurement:
            raise ValueError("campaign is not authenticated live-provider evidence")
        if not self.verify(verifier):
            raise ValueError("signed provider evidence failed verification")
        report = self.execution.evaluate(
            incumbent_condition=incumbent_condition,
            candidate_condition=candidate_condition,
            cost_model=cost_model,
            policy=policy,
        )
        report["authenticated_live_ab_executed"] = True
        report["evidence_bundle_sha256"] = self.campaign_sha256
        return report


class AuthenticatedLiveHoldoutRunner:
    """Execute paired conditions and seal each provider observation as public-key evidence.

    The callback is responsible for performing the provider request and returning telemetry plus
    an ``attestation`` mapping. This runner does not infer liveness from a signature: synthetic or
    replayed callbacks remain non-live even when their receipts are validly signed.
    """

    def __init__(
        self,
        *,
        incumbent_condition: str,
        candidate_condition: str,
        signer: Ed25519ReceiptSigner,
        seed: int = 20260925,
    ) -> None:
        self._runner = PairedHoldoutCampaignRunner(
            incumbent_condition=incumbent_condition,
            candidate_condition=candidate_condition,
            seed=seed,
        )
        self.signer = signer

    @staticmethod
    def _attestation(raw: Mapping[str, Any]) -> ProviderExecutionAttestation:
        value = raw.get("attestation")
        if not isinstance(value, Mapping):
            raise ValueError("provider callback must return attestation mapping")
        return ProviderExecutionAttestation(
            provider=str(value.get("provider") or ""),
            model=str(value.get("model") or ""),
            provider_request_id=str(value.get("provider_request_id") or ""),
            evidence_origin=str(value.get("evidence_origin") or ""),
            transport_security=str(value.get("transport_security") or ""),
            authenticated=bool(value.get("authenticated", False)),
        )

    def run(
        self,
        *,
        missions: Sequence[PairedMission],
        run_condition: Callable[[PairedMissionInput, str], Mapping[str, Any]],
    ) -> LiveCampaignEvidenceBundle:
        attestations: list[ProviderExecutionAttestation] = []
        raw_by_identity: dict[tuple[int, str, str], Mapping[str, Any]] = {}

        def instrumented(inp: PairedMissionInput, condition: str) -> Mapping[str, Any]:
            raw = dict(run_condition(inp, condition))
            attestation = self._attestation(raw)
            attestations.append(attestation)
            raw_by_identity[(inp.repeat, inp.case_id, condition)] = raw
            return raw

        preliminary = self._runner.run(
            missions=missions,
            run_condition=instrumented,
            live_provider_measurement=False,
        )
        live = bool(attestations) and all(a.qualifies_as_live for a in attestations)
        execution = PairedCampaignExecution(
            records=preliminary.records,
            pair_execution_order=preliminary.pair_execution_order,
            shadow_pairs=preliminary.shadow_pairs,
            experiment_pairs=preliminary.experiment_pairs,
            holdout_pairs=preliminary.holdout_pairs,
            seed=preliminary.seed,
            live_provider_measurement=live,
        )
        campaign_core = execution.to_dict()
        campaign_sha256 = _canonical_hash(campaign_core)
        signed: list[SignedProviderExecution] = []
        for record in execution.records:
            identity = (int(record["repeat"]), str(record["case_id"]), str(record["condition"]))
            raw = raw_by_identity[identity]
            attestation = self._attestation(raw)
            receipt_payload = {
                "receipt_version": 1,
                "campaign_sha256": campaign_sha256,
                "signer_key_id": self.signer.key_id,
                "case_id": record["case_id"],
                "repeat": record["repeat"],
                "condition": record["condition"],
                "payload_sha256": record["payload_sha256"],
                "pair_execution_order": record["pair_execution_order"],
                "status": record["status"],
                "metrics_sha256": _canonical_hash(record["metrics"]),
                "provider": attestation.provider,
                "model": attestation.model,
                "provider_request_id": attestation.provider_request_id,
                "evidence_origin": attestation.evidence_origin,
                "transport_security": attestation.transport_security,
                "provider_authenticated": attestation.authenticated,
            }
            signed.append(SignedProviderExecution(self.signer.sign(receipt_payload)))
        return LiveCampaignEvidenceBundle(
            execution=execution,
            signed_executions=tuple(signed),
            signer_key_id=self.signer.key_id,
            campaign_sha256=campaign_sha256,
            live_provider_measurement=live,
        )