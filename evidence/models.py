from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

# ponytail: Structured Data Models for Machine-Verifiable Evidence & Assurance Receipts.

@dataclass
class EvidenceItem:
    id: str
    mission_id: str
    criterion_ref: str
    tier: str  # tier_0_self, tier_1_model, tier_2_deterministic, tier_3_attestation
    verifier_type: str
    verifier_identifier: str
    result: str  # SATISFIED, FAILED, INDETERMINATE, SKIPPED
    evidence_data: Dict[str, Any] = field(default_factory=dict)
    verifier_version: str = "1.0.0"
    trust_class: str = "STANDARD"  # UNTRUSTED, PROVISIONAL, STANDARD, HIGH, HARDWARE_ATTESTED
    is_revoked: bool = False
    expires_at: Optional[str] = None
    signature: Optional[str] = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "criterion_ref": self.criterion_ref,
            "tier": self.tier,
            "verifier": {
                "type": self.verifier_type,
                "identifier": self.verifier_identifier,
                "version": self.verifier_version
            },
            "result": self.result,
            "trust_class": self.trust_class,
            "is_revoked": self.is_revoked,
            "expires_at": self.expires_at,
            "signature": self.signature,
            "evidence_data": self.evidence_data,
            "timestamp": self.timestamp
        }

@dataclass
class AssuranceReceipt:
    receipt_id: str
    mission_id: str
    run_id: str
    criterion_id: str
    claim: str
    artifact_hash: str
    verifier_id: str
    verifier_version: str
    environment: str
    verification_method: str
    result: str  # PASS, FAIL, REJECTED
    evidence_references: List[str]
    observed_at: str
    freshness_expiry: Optional[str] = None
    signature_anchor: Optional[str] = None
    policy_version: str = "SPEC-001-v0.1"

    def compute_hash(self) -> str:
        d = {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "criterion_id": self.criterion_id,
            "artifact_hash": self.artifact_hash,
            "verifier_id": self.verifier_id,
            "result": self.result,
            "evidence_references": self.evidence_references
        }
        b = json.dumps(d, sort_keys=True).encode("utf-8")
        return hashlib.sha256(b).hexdigest()

    def validate_completeness(self) -> tuple[bool, Optional[str]]:
        if not self.receipt_id or not self.mission_id or not self.criterion_id:
            return False, "Missing mandatory receipt identifiers"
        if not self.artifact_hash:
            return False, "Missing artifact hash binding"
        if not self.verifier_id or not self.verifier_version:
            return False, "Missing verifier provenance"
        if not self.evidence_references:
            return False, "Missing evidence references"
        return True, None
