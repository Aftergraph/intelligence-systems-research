import datetime
import json
import os
import threading
import time
import uuid
import yaml
import jsonschema

# ponytail: Clean-Room Independent Reference Implementation of SPEC-001.
# Developed independently without referencing runtime/engine.py.
# Verifies that SPEC-001 is completely self-sufficient and implementable by third parties.

VALID_STATES = {
    "DRAFT", "READY", "AUTHORIZED", "RUNNING", "PAUSED",
    "NEEDS_INPUT", "VERIFYING", "VERIFIED", "RECOVERING",
    "FAILED", "CANCELLED", "REVOKED"
}

TIER_HIERARCHY = {
    "tier_0_self": 0,
    "tier_1_model": 1,
    "tier_2_deterministic": 2,
    "tier_3_attestation": 3
}

def _parse_ts(ts):
    if not ts:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))

def _parse_duration(val):
    if val is None:
        return float("inf")
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().lower()
    if s.startswith("pt"):
        s = s[2:]
        total = 0.0
        num = ""
        for char in s:
            if char.isdigit() or char == ".":
                num += char
            elif char == "h":
                total += float(num or 0) * 3600
                num = ""
            elif char == "m":
                total += float(num or 0) * 60
                num = ""
            elif char == "s":
                total += float(num or 0)
                num = ""
        return total
    if s.endswith("ms"):
        return float(s[:-2]) / 1000.0
    elif s.endswith("s"):
        return float(s[:-1])
    elif s.endswith("m"):
        return float(s[:-1]) * 60.0
    elif s.endswith("h"):
        return float(s[:-1]) * 3600.0
    elif s.endswith("d"):
        return float(s[:-1]) * 86400.0
    try:
        return float(s)
    except ValueError:
        return float("inf")

class IndependentMissionRuntime:
    """
    Clean-room implementation of SPEC-001 Intelligence System Contract.
    Strictly implements the 8-tuple: <M, S, C, A, B, T, E, V> and Invariants 1-5.
    """
    def __init__(self, schemas_path=None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.schemas_path = schemas_path or os.path.abspath(os.path.join(base, "..", "schemas"))
        self._load_schemas()
        
        self._lock = threading.RLock()
        self.state = "DRAFT"
        self.mission = None
        self.delegation = None
        self.trajectory = []
        self.evidence_store = {}
        self.budget_tracker = {"tokens": 0, "cost_usd": 0.0, "time_sec": 0.0, "actions": 0}
        self.start_timestamp = None

    def _load_schemas(self):
        with open(os.path.join(self.schemas_path, "mission.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.mission_schema = json.load(f)
        with open(os.path.join(self.schemas_path, "delegation.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.delegation_schema = json.load(f)
        with open(os.path.join(self.schemas_path, "evidence.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.evidence_schema = json.load(f)

    def append_event(self, event_type, payload):
        """Invariant 5: State Mutation Traceability via append-only log."""
        event = {
            "id": f"evt-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "state": self.state,
            "payload": payload
        }
        self.trajectory.append(event)
        return event

    def load_mission(self, mission_data):
        with self._lock:
            if isinstance(mission_data, str):
                with open(mission_data, "r", encoding="utf-8") as f:
                    mission_data = yaml.safe_load(f)
            jsonschema.validate(instance=mission_data, schema=self.mission_schema)
            self.mission = mission_data
            self.state = "READY"
            self.append_event("MISSION_INITIALIZED", {"mission_id": mission_data["metadata"]["id"]})
            return self.mission

    def grant_delegation(self, delegation_data):
        with self._lock:
            assert self.state in ("READY", "DRAFT"), f"Invalid state for authorization: {self.state}"
            jsonschema.validate(instance=delegation_data, schema=self.delegation_schema)
            
            # Purpose-bound check (SPEC-001 Section 5)
            if self.mission:
                mid = self.mission["metadata"]["id"]
                if mid not in delegation_data.get("purpose", ""):
                    raise ValueError(f"Delegation purpose does not bind to mission ID {mid}")

            self.delegation = delegation_data
            self.state = "AUTHORIZED"
            self.append_event("DELEGATION_GRANTED", {"delegation_id": delegation_data["id"]})
            return True

    def validate_subdelegation(self, child_delegation):
        """Validates subdelegation attenuation against active delegation (Invariant 3)."""
        with self._lock:
            if not self.delegation:
                return False
            jsonschema.validate(instance=child_delegation, schema=self.delegation_schema)
            parent_allowed = self.delegation["scope"].get("allowed_capabilities", [])
            for cap in child_delegation["scope"].get("allowed_capabilities", []):
                matched = any(pa == "*" or pa == cap or (pa.endswith("*") and cap.startswith(pa[:-1])) for pa in parent_allowed)
                if not matched:
                    return False
            return True

    def start_execution(self):
        with self._lock:
            assert self.state == "AUTHORIZED", f"Must be AUTHORIZED to start, currently {self.state}"
            self.state = "RUNNING"
            self.start_timestamp = time.time()
            self.append_event("EXECUTION_COMMENCED", {})

    def pause(self, reason="Operator pause"):
        with self._lock:
            assert self.state == "RUNNING", f"Cannot pause from {self.state}"
            self.state = "PAUSED"
            self.append_event("EXECUTION_PAUSED", {"reason": reason})
            return True

    def resume(self):
        with self._lock:
            assert self.state in ("PAUSED", "NEEDS_INPUT"), f"Cannot resume from {self.state}"
            self.state = "RUNNING"
            self.append_event("EXECUTION_RESUMED", {})
            return True

    def cancel(self, reason="Operator cancel"):
        with self._lock:
            self.state = "CANCELLED"
            self.append_event("EXECUTION_CANCELLED", {"reason": reason})
            return True

    def revoke(self, reason="Authority revoked"):
        with self._lock:
            self.state = "REVOKED"
            if self.delegation:
                self.delegation["revoked"] = True
            self.append_event("AUTHORITY_REVOKED", {"reason": reason})
            return True

    def takeover(self, reason="Operator takeover"):
        with self._lock:
            self.state = "PAUSED"
            self.append_event("OPERATOR_TAKEOVER", {"reason": reason})
            return True

    def invoke_capability(self, capability_uri, tokens_used=50, cost_usd=0.001):
        """
        Invariant 3 (Purpose-Bound Attenuation) & Invariant 4 (Budget Non-Exceedance).
        """
        with self._lock:
            if self.state == "REVOKED":
                raise PermissionError("Authority has been revoked")
            if self.state == "PAUSED":
                raise RuntimeError("Runtime is currently paused")
            assert self.state == "RUNNING", f"Cannot invoke capabilities in state {self.state}"

            # 1. Authority Check & Temporal Validation
            if self.delegation:
                if self.delegation.get("revoked", False):
                    self.state = "REVOKED"
                    raise PermissionError("Authority has been revoked")

                now = datetime.datetime.now(datetime.timezone.utc)
                if "valid_from" in self.delegation:
                    vf = _parse_ts(self.delegation["valid_from"])
                    if vf and now < vf:
                        self.append_event("CAPABILITY_BLOCKED", {"uri": capability_uri, "reason": "not_yet_valid"})
                        raise PermissionError(f"Delegation token not yet valid (valid_from: {self.delegation['valid_from']})")

                if "expires_at" in self.delegation:
                    exp = _parse_ts(self.delegation["expires_at"])
                    if exp and now > exp:
                        self.append_event("CAPABILITY_BLOCKED", {"uri": capability_uri, "reason": "expired"})
                        raise PermissionError(f"Delegation token expired at {self.delegation['expires_at']}")

                allowed = self.delegation["scope"].get("allowed_capabilities", [])
                denied = self.delegation["scope"].get("denied_capabilities", [])

                for d in denied:
                    if d == capability_uri or (d.endswith("*") and capability_uri.startswith(d[:-1])):
                        self.append_event("CAPABILITY_BLOCKED", {"uri": capability_uri, "reason": "denied"})
                        raise PermissionError(f"Capability {capability_uri} denied by policy rule {d}")

                matched = False
                for a in allowed:
                    if a == "*" or a == capability_uri or (a.endswith("*") and capability_uri.startswith(a[:-1])):
                        matched = True
                        break
                if not matched:
                    self.append_event("CAPABILITY_BLOCKED", {"uri": capability_uri, "reason": "unauthorized"})
                    raise PermissionError(f"Capability {capability_uri} not authorized in scope")

            # 2. Budget Check
            budget = self.mission.get("budget", {}) if self.mission else {}
            max_tokens = budget.get("tokens", {}).get("max", float("inf"))
            max_cost = budget.get("money", {}).get("max", float("inf"))

            if (self.budget_tracker["tokens"] + tokens_used) > max_tokens:
                self.state = "NEEDS_INPUT"
                self.append_event("BUDGET_CEILING_HIT", {"type": "tokens"})
                raise RuntimeError("Token budget ceiling exceeded")

            if (self.budget_tracker["cost_usd"] + cost_usd) > max_cost:
                self.state = "NEEDS_INPUT"
                self.append_event("BUDGET_CEILING_HIT", {"type": "money"})
                raise RuntimeError("Financial budget ceiling exceeded")

            if self.start_timestamp:
                elapsed = time.time() - self.start_timestamp
                self.budget_tracker["time_sec"] = elapsed
                wc_max = budget.get("wall_clock", {}) if isinstance(budget.get("wall_clock"), dict) else {}
                max_val = wc_max.get("max")
                if max_val:
                    max_s = _parse_duration(max_val)
                    if elapsed > max_s:
                        self.state = "NEEDS_INPUT"
                        self.append_event("BUDGET_CEILING_HIT", {"type": "wall_clock"})
                        raise RuntimeError(f"Wall clock budget exceeded ({elapsed:.1f}s > {max_s}s)")

            self.budget_tracker["tokens"] += tokens_used
            self.budget_tracker["cost_usd"] += cost_usd
            self.budget_tracker["actions"] += 1
            self.append_event("CAPABILITY_INVOKED", {"uri": capability_uri, "tokens": tokens_used})
            return {"status": "SUCCESS", "uri": capability_uri}

    def declare_complete(self):
        """
        Invariant 1: Complete != Verified.
        Transitions to VERIFYING, strictly never to VERIFIED.
        """
        with self._lock:
            assert self.state == "RUNNING", f"Cannot complete from {self.state}"
            self.state = "VERIFYING"
            self.append_event("AGENT_DECLARED_COMPLETE", {})

    def submit_evidence(self, evidence_item):
        with self._lock:
            jsonschema.validate(instance=evidence_item, schema=self.evidence_schema)
            crit = evidence_item["criterion_ref"]
            self.evidence_store[crit] = evidence_item
            self.append_event("EVIDENCE_SUBMITTED", {"criterion": crit, "tier": evidence_item["tier"]})

    def run_verification_gate(self):
        """
        Invariant 2: Evidence-Gated Completion.
        Evaluates evidence store against all required criteria, taking into account minimum_tier and any criteria.
        """
        with self._lock:
            assert self.state in ("VERIFYING", "RECOVERING"), f"Invalid state for verification: {self.state}"
            required = self.mission.get("success", {}).get("all", []) if self.mission else []
            required_any = self.mission.get("success", {}).get("any", []) if self.mission else []
            
            assurance_cfg = self.mission.get("assurance", {}).get("verification", {}) if self.mission else {}
            min_tier_name = assurance_cfg.get("minimum_tier", "tier_2_deterministic" if assurance_cfg.get("independence") == "required" else "tier_1_model")
            min_tier_val = TIER_HIERARCHY.get(min_tier_name, 1)

            unmet = []
            for crit in required:
                ev = self.evidence_store.get(crit)
                if not ev:
                    unmet.append((crit, "MISSING"))
                elif ev["result"] != "SATISFIED":
                    unmet.append((crit, f"FAILED_{ev['result']}"))
                else:
                    ev_tier_val = TIER_HIERARCHY.get(ev.get("tier"), 0)
                    if ev_tier_val == 0:
                        unmet.append((crit, "TIER_0_DISALLOWED"))
                    elif ev_tier_val < min_tier_val:
                        unmet.append((crit, f"TIER_INSUFFICIENT_{ev.get('tier')}"))

            if required_any:
                any_ok = False
                for crit in required_any:
                    ev = self.evidence_store.get(crit)
                    if ev and ev["result"] == "SATISFIED":
                        ev_tier_val = TIER_HIERARCHY.get(ev.get("tier"), 0)
                        if ev_tier_val >= min_tier_val and ev_tier_val > 0:
                            any_ok = True
                            break
                if not any_ok:
                    unmet.append(("ANY_CRITERIA", "NONE_SATISFIED"))

            if not unmet:
                self.state = "VERIFIED"
                if self.start_timestamp:
                    self.budget_tracker["time_sec"] = time.time() - self.start_timestamp
                self.append_event("MISSION_VERIFIED", {"criteria": required + required_any})
                return True
            else:
                retry_limit = self.mission.get("recovery", {}).get("retry_limit", 0) if self.mission else 0
                if retry_limit > 0:
                    self.state = "RECOVERING"
                    self.append_event("VERIFICATION_FAILED_RECOVERY_TRIGGERED", {"unmet": unmet})
                else:
                    self.state = "FAILED"
                    self.append_event("VERIFICATION_FAILED_TERMINAL", {"unmet": unmet})
                return False
