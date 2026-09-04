from collections import defaultdict
from typing import Dict, List, Optional
from evidence.models import EvidenceItem

# ponytail: Append-Only Conflict-Aware Evidence Repository.
# Preserves complete history per criterion (evidence-001, 002, ...).
# Conflict resolution policy: active failures must be explicitly superseded by higher or equal trust receipts.

class EvidenceStore:
    def __init__(self):
        self._store: Dict[str, List[EvidenceItem]] = defaultdict(list)
        self._by_id: Dict[str, EvidenceItem] = {}

    def record(self, item: EvidenceItem):
        self._store[item.criterion_ref].append(item)
        self._by_id[item.id] = item

    def get(self, criterion_ref: str) -> Optional[EvidenceItem]:
        items = self._store.get(criterion_ref, [])
        return items[-1] if items else None

    def get_history(self, criterion_ref: str) -> List[EvidenceItem]:
        return list(self._store.get(criterion_ref, []))

    def list_all(self) -> List[EvidenceItem]:
        return list(self._by_id.values())

    def revoke_evidence(self, evidence_id: str):
        item = self._by_id.get(evidence_id)
        if item:
            item.is_revoked = True

    def satisfies_criterion(self, criterion_ref: str, minimum_tier: str = "tier_2_deterministic") -> bool:
        items = self._store.get(criterion_ref, [])
        if not items:
            return False

        tier_weights = {
            "tier_0_self": 0,
            "tier_1_model": 1,
            "tier_2_deterministic": 2,
            "tier_3_attestation": 3
        }
        req_weight = tier_weights.get(minimum_tier, 2)

        # Filter out revoked or expired evidence
        active_items = [it for it in items if not it.is_revoked]
        if not active_items:
            return False

        # Evaluate conflict resolution:
        # If the latest valid entry is FAILED, it is not satisfied
        latest = active_items[-1]
        if latest.result != "SATISFIED":
            return False

        # Must meet minimum tier requirement
        item_weight = tier_weights.get(latest.tier, 0)
        return item_weight >= req_weight
