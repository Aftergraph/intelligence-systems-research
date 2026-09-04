import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from state.lifecycle import MissionLifecycle
from evidence.store import EvidenceStore
from evidence.models import EvidenceItem, AssuranceReceipt
from assurance.principals import Principal, AgentPrincipal, AssurancePrincipal

# ponytail: Logical Assurance Boundary Engine.
# Strictly separates AgentPrincipal from AssurancePrincipal.
# AgentPrincipal is mathematically barred from issuing verification decisions or transitioning to VERIFIED.

class AssuranceEngine:
    def __init__(self, lifecycle: MissionLifecycle, evidence_store: EvidenceStore, trajectory_recorder=None):
        self.lifecycle = lifecycle
        self.evidence_store = evidence_store
        self.trajectory_recorder = trajectory_recorder
        self.recovery_allowance = 3

    def intercept_candidate_completion(
        self,
        mission_id: str,
        candidate_notes: str = "",
        caller: Optional[Principal] = None
    ) -> str:
        """Agent emits completion. Engine traps transition and shifts to VERIFYING."""
        if self.lifecycle.current_state != "RUNNING":
            raise RuntimeError(f"Cannot submit candidate completion from state: {self.lifecycle.current_state}")

        self.lifecycle.transition_to("VERIFYING", reason="Candidate completion intercepted")
        if self.trajectory_recorder:
            self.trajectory_recorder.emit_event("CANDIDATE_COMPLETION_INTERCEPTED", {
                "mission_id": mission_id,
                "notes": candidate_notes,
                "caller": caller.name if caller else "AgentPrincipal"
            })
        return self.lifecycle.current_state

    def evaluate_mission_criteria(
        self,
        mission_id: str,
        required_criteria: List[str],
        minimum_tier: str = "tier_2_deterministic",
        caller: Optional[Principal] = None,
        run_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Evaluates whether all declared criteria are backed by qualifying evidence."""
        # Principal check: AgentPrincipal CANNOT evaluate or transition to VERIFIED!
        # Q-005 hardening: use object identity (`is`) against the singleton,
        # not string equality. A hostile process can construct a fresh
        # Principal(name="AgentPrincipal") and bypass a name check; only
        # object identity against the frozen singleton is secure.
        if caller is AgentPrincipal or (caller is not None and caller.name == "AgentPrincipal"):
            raise PermissionError("AgentPrincipal is barred from executing verification transitions (Logical Assurance Boundary)")

        if self.lifecycle.current_state not in ("VERIFYING", "RECOVERING"):
            raise RuntimeError(f"Cannot evaluate assurance in state: {self.lifecycle.current_state}")

        active_run_id = run_id or f"run-{mission_id[:8]}"
        failures = []
        receipts = []

        for crit in required_criteria:
            is_satisfied = self.evidence_store.satisfies_criterion(crit, minimum_tier=minimum_tier)
            ev = self.evidence_store.get(crit)
            ev_refs = [ev.id] if ev else []
            art_hash = hashlib.sha256(f"{mission_id}:{crit}".encode("utf-8")).hexdigest()

            receipt = AssuranceReceipt(
                receipt_id=f"rcpt-{uuid.uuid4().hex[:12]}",
                mission_id=mission_id,
                run_id=active_run_id,
                criterion_id=crit,
                claim=f"Criterion {crit} evaluated against evidence",
                artifact_hash=art_hash,
                verifier_id=ev.verifier_identifier if ev else "unknown_verifier",
                verifier_version=ev.verifier_version if ev else "1.0.0",
                environment="test_runtime_logical_boundary",
                verification_method=ev.verifier_type if ev else "none",
                result="PASS" if is_satisfied else "FAIL",
                evidence_references=ev_refs,
                observed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                signature_anchor=art_hash[:16]
            )
            receipts.append(receipt)

            if not is_satisfied:
                failures.append(crit)

        if not failures:
            # All criteria passed! Transition to VERIFIED
            self.lifecycle.transition_to("VERIFIED", reason="All criteria satisfied with qualifying evidence")
            if self.trajectory_recorder:
                self.trajectory_recorder.emit_event("ASSURANCE_VERIFIED", {
                    "mission_id": mission_id,
                    "criteria": required_criteria,
                    "receipt_count": len(receipts)
                })
            return True, {
                "status": "VERIFIED",
                "satisfied_criteria": required_criteria,
                "receipts": [r.__dict__ for r in receipts]
            }
        else:
            # Failure detected! Invariant: Do NOT let system falsely succeed
            if self.recovery_allowance > 0:
                self.recovery_allowance -= 1
                self.lifecycle.transition_to("RECOVERING", reason=f"Criteria failed: {failures}")
                diag_payload = {
                    "status": "RECOVERING",
                    "failed_criteria": failures,
                    "remaining_recovery_attempts": self.recovery_allowance,
                    "diagnostic_message": f"Assurance failed for criteria: {', '.join(failures)}. Remediation required.",
                    "receipts": [r.__dict__ for r in receipts]
                }
                if self.trajectory_recorder:
                    self.trajectory_recorder.emit_event("ASSURANCE_FAILED_ENTER_RECOVERY", diag_payload)
                return False, diag_payload
            else:
                self.lifecycle.transition_to("FAILED", reason="Recovery allowance exhausted")
                return False, {
                    "status": "FAILED",
                    "reason": "Recovery allowance exhausted",
                    "failed_criteria": failures,
                    "receipts": [r.__dict__ for r in receipts]
                }
