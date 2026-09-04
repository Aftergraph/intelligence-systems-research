import copy
import datetime
import json
import os
import threading
import time
import uuid
import yaml
import jsonschema

# ponytail: Minimal, robust MissionEngine implementing SPEC-001.
# Enforces Invariant 1 (Complete != Verified) and Invariant 2 (Evidence-Gated Completion).
# No external frameworks, standard library + PyYAML and jsonschema.

STATES = {
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

def _parse_iso_time(ts):
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

class MissionEngine:
    def __init__(self, schemas_dir=None, storage=None, policy=None):
        self._lock = threading.RLock()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.schemas_dir = schemas_dir or os.path.abspath(os.path.join(base_dir, "..", "schemas"))
        self._load_schemas()
        self.storage = storage
        self.policy = policy
        self.manifest = None
        self.mission = None
        self._immutable_objective = None
        self._immutable_success = None
        self.delegation = None
        self.state = "DRAFT"
        self.trajectory = []
        self.evidence_store = {}
        self.budget_spent = {
            "tokens": 0,
            "usd": 0.0,
            "actions": 0,
            "human_interventions": 0,
            "wall_clock_seconds": 0.0
        }
        self.start_time = None
        self.control_plane_tokens = 0
        self.task_tokens = 0

    def _load_schemas(self):
        with open(os.path.join(self.schemas_dir, "intelligence-system.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.is_schema = json.load(f)
        with open(os.path.join(self.schemas_dir, "mission.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.mission_schema = json.load(f)
        with open(os.path.join(self.schemas_dir, "delegation.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.delegation_schema = json.load(f)
        with open(os.path.join(self.schemas_dir, "evidence.v0alpha1.json"), "r", encoding="utf-8") as f:
            self.evidence_schema = json.load(f)

    def _emit_event(self, event_type, details):
        event = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "state": self.state,
            "details": details
        }
        self.trajectory.append(event)
        if self.storage and self.mission:
            m_id = self.mission.get("metadata", {}).get("id", "default-mission")
            self.storage.append_event(m_id, event)
        return event

    def load_manifest(self, path):
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            jsonschema.validate(instance=data, schema=self.is_schema)
            self.manifest = data
            self._emit_event("MANIFEST_LOADED", {"name": data["metadata"]["name"]})
            return data

    def load_mission(self, data_or_path):
        with self._lock:
            if isinstance(data_or_path, str):
                with open(data_or_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            else:
                data = copy.deepcopy(data_or_path)

            jsonschema.validate(instance=data, schema=self.mission_schema)
            self.mission = data
            self._immutable_objective = copy.deepcopy(data.get("objective"))
            self._immutable_success = copy.deepcopy(data.get("success"))
            self.state = "READY"
            
            # Calculate schema tokens as initial control plane tax
            mission_str = yaml.dump(data)
            self.control_plane_tokens += int(len(mission_str) / 3.8)
            self._emit_event("MISSION_LOADED", {"id": data["metadata"]["id"]})
            return data

    def verify_integrity(self):
        """Verifies Invariant 5: Objective and acceptance criteria immutability."""
        if self.mission and self._immutable_objective is not None:
            if self.mission.get("objective") != self._immutable_objective or self.mission.get("success") != self._immutable_success:
                self._emit_event("OBJECTIVE_MUTATION_DETECTED", {
                    "original_objective": self._immutable_objective,
                    "mutated_objective": self.mission.get("objective")
                })
                self.state = "FAILED"
                raise PermissionError("Mission contract tampering detected: Invariant 5 violation")
        return True

    def authorize(self, delegation_data):
        with self._lock:
            assert self.state in ("READY", "DRAFT"), f"Cannot authorize in state {self.state}"
            jsonschema.validate(instance=delegation_data, schema=self.delegation_schema)
            
            # Verify purpose matches mission if mission is loaded
            if self.mission:
                mission_id = self.mission["metadata"]["id"]
                if mission_id not in delegation_data["purpose"]:
                    raise ValueError(
                        f"Delegation purpose '{delegation_data['purpose']}' does not bind to mission '{mission_id}'"
                    )

            self.delegation = copy.deepcopy(delegation_data)
            self.state = "AUTHORIZED"
            self._emit_event("AUTHORITY_GRANTED", {
                "delegation_id": delegation_data["id"],
                "principal": delegation_data["principal"],
                "delegate": delegation_data["delegate"]
            })
            return True

    def create_subdelegation(self, subagent_urn, purpose, allowed_capabilities, denied_capabilities=None, valid_seconds=None):
        """
        Invariant 3: Purpose-Bound Authority Attenuation.
        Creates an attenuated child delegation token bound by parent scope, depth, and validity.
        """
        with self._lock:
            if not self.delegation:
                raise PermissionError("No active parent delegation to sub-delegate from")
            
            if not self.delegation.get("allow_redelegation", True):
                raise PermissionError("Redelegation not permitted by parent delegation token")

            parent_depth = self.delegation.get("max_delegation_depth", 1)
            if parent_depth <= 0:
                raise PermissionError("Maximum delegation depth reached (depth=0)")

            parent_allowed = self.delegation["scope"].get("allowed_capabilities", [])
            parent_denied = self.delegation["scope"].get("denied_capabilities", [])

            # Check that every sub capability is within parent's allowed scope
            for cap in allowed_capabilities:
                matched = any(pa == "*" or pa == cap or (pa.endswith("*") and cap.startswith(pa[:-1])) for pa in parent_allowed)
                if not matched:
                    raise PermissionError(f"Subdelegation capability '{cap}' exceeds parent scope")

            # Denied capabilities must be union of parent denied and child denied
            effective_denied = list(set((denied_capabilities or []) + parent_denied))

            # Purpose must bind to mission
            if self.mission:
                mid = self.mission["metadata"]["id"]
                if mid not in purpose:
                    raise PermissionError(f"Subdelegation purpose '{purpose}' does not bind to mission '{mid}'")

            # Expiration must not exceed parent's expiration
            now = datetime.datetime.now(datetime.timezone.utc)
            parent_exp = _parse_iso_time(self.delegation.get("expires_at"))
            if valid_seconds:
                child_exp_dt = now + datetime.timedelta(seconds=valid_seconds)
                if parent_exp and child_exp_dt > parent_exp:
                    child_exp_dt = parent_exp
            else:
                child_exp_dt = parent_exp or (now + datetime.timedelta(hours=1))

            child_delegation = {
                "id": f"del-sub-{uuid.uuid4().hex[:8]}",
                "principal": self.delegation["delegate"],
                "delegate": subagent_urn,
                "purpose": purpose,
                "scope": {
                    "allowed_capabilities": allowed_capabilities,
                    "denied_capabilities": effective_denied
                },
                "valid_from": now.isoformat(),
                "expires_at": child_exp_dt.isoformat(),
                "allow_redelegation": parent_depth > 1,
                "max_delegation_depth": parent_depth - 1
            }
            self._emit_event("SUBDELEGATION_CREATED", {
                "subdelegation_id": child_delegation["id"],
                "delegate": subagent_urn,
                "depth": child_delegation["max_delegation_depth"]
            })
            return child_delegation

    def validate_subdelegation(self, child_delegation):
        """Validates that a child delegation satisfies Invariant 3 attenuation rules."""
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

    def start(self):
        with self._lock:
            assert self.state == "AUTHORIZED", f"Cannot start execution from state {self.state}"
            self.state = "RUNNING"
            self.start_time = time.time()
            self._emit_event("EXECUTION_STARTED", {"mission_id": self.mission["metadata"]["id"]})

    def pause(self, reason="Operator paused execution"):
        with self._lock:
            assert self.state == "RUNNING", f"Cannot pause execution from state {self.state}"
            self.state = "PAUSED"
            self._emit_event("HUMAN_PAUSE_TRIGGERED", {"reason": reason})
            return True

    def resume(self):
        with self._lock:
            assert self.state in ("PAUSED", "NEEDS_INPUT"), f"Cannot resume from state {self.state}"
            self.state = "RUNNING"
            self._emit_event("HUMAN_RESUME_TRIGGERED", {})
            return True

    def cancel(self, reason="Operator cancelled execution"):
        with self._lock:
            self.state = "CANCELLED"
            self._emit_event("HUMAN_CANCEL", {"reason": reason})
            return True

    def revoke(self, reason="Authority revoked"):
        with self._lock:
            self.state = "REVOKED"
            if self.delegation:
                self.delegation["revoked"] = True
            self._emit_event("AUTHORITY_REVOKED", {"reason": reason})
            return True

    def takeover(self, operator_id="operator", reason="Operator takeover"):
        with self._lock:
            self.state = "PAUSED"
            self.budget_spent["human_interventions"] += 1
            self._emit_event("HUMAN_TAKEOVER", {"operator_id": operator_id, "reason": reason})
            return True

    def execute_action(self, capability_uri, payload=None, tokens=50, cost_usd=0.001):
        """Executes a capability action after verifying authority, validity, and budget."""
        with self._lock:
            if self.state == "REVOKED":
                raise PermissionError("Authority has been revoked")
            if self.state == "PAUSED":
                raise RuntimeError("Execution is paused")
            assert self.state == "RUNNING", f"Cannot execute action when state is {self.state}"

            # Verify contract integrity (Invariant 5)
            self.verify_integrity()

            # 1. Authority Check (Purpose-Bound Attenuation & Temporal Validity)
            if self.delegation:
                if self.delegation.get("revoked", False):
                    self.state = "REVOKED"
                    raise PermissionError("Authority has been revoked")

                # Check expiration & valid_from
                now = datetime.datetime.now(datetime.timezone.utc)
                if "valid_from" in self.delegation:
                    vf = _parse_iso_time(self.delegation["valid_from"])
                    if vf and now < vf:
                        self._emit_event("ACTION_BLOCKED", {"uri": capability_uri, "reason": "Token not yet valid"})
                        raise PermissionError(f"Delegation token not yet valid (valid_from: {self.delegation['valid_from']})")

                if "expires_at" in self.delegation:
                    exp = _parse_iso_time(self.delegation["expires_at"])
                    if exp and now > exp:
                        self._emit_event("ACTION_BLOCKED", {"uri": capability_uri, "reason": "Token expired"})
                        raise PermissionError(f"Delegation token expired at {self.delegation['expires_at']}")

                allowed = self.delegation["scope"].get("allowed_capabilities", [])
                denied = self.delegation["scope"].get("denied_capabilities", [])
                
                # Check denied explicitly
                for d in denied:
                    if d.endswith("*") and capability_uri.startswith(d[:-1]):
                        self._emit_event("ACTION_BLOCKED", {"uri": capability_uri, "reason": "Explicitly denied pattern"})
                        raise PermissionError(f"Action {capability_uri} denied by pattern {d}")
                    elif d == capability_uri:
                        self._emit_event("ACTION_BLOCKED", {"uri": capability_uri, "reason": "Explicitly denied"})
                        raise PermissionError(f"Action {capability_uri} explicitly denied")

                # Check allowed
                matched = False
                for a in allowed:
                    if a == "*" or (a.endswith("*") and capability_uri.startswith(a[:-1])) or a == capability_uri:
                        matched = True
                        break
                if not matched:
                    self._emit_event("ACTION_BLOCKED", {"uri": capability_uri, "reason": "Not in allowed scope"})
                    raise PermissionError(f"Action {capability_uri} not authorized in delegation scope")

            # 1b. Policy Sandboxing Check (Filesystem & Command boundaries)
            if self.policy and payload:
                if isinstance(payload, dict):
                    if "cmd" in payload:
                        self.policy.validate_command(payload["cmd"])
                    if "path" in payload:
                        self.policy.validate_file_access(payload["path"], mode=payload.get("mode", "read"))
                elif isinstance(payload, str):
                    if "shell" in capability_uri or "bash" in capability_uri or "exec" in capability_uri:
                        self.policy.validate_command(payload)

            # 2. Budget Check
            new_tokens = self.budget_spent["tokens"] + tokens
            new_cost = self.budget_spent["usd"] + cost_usd
            new_actions = self.budget_spent["actions"] + 1
            
            budget_cfg = self.mission.get("budget", {}) if self.mission else {}
            if "tokens" in budget_cfg and new_tokens > budget_cfg["tokens"].get("max", float("inf")):
                self.state = "NEEDS_INPUT"
                self._emit_event("BUDGET_EXHAUSTED", {"type": "tokens", "spent": new_tokens})
                raise RuntimeError("Token budget exhausted")
            if "money" in budget_cfg and new_cost > budget_cfg["money"].get("max", float("inf")):
                self.state = "NEEDS_INPUT"
                self._emit_event("BUDGET_EXHAUSTED", {"type": "money", "spent": new_cost})
                raise RuntimeError("Money budget exhausted")

            # Check wall clock budget if specified
            if self.start_time:
                elapsed = time.time() - self.start_time
                self.budget_spent["wall_clock_seconds"] = elapsed
                wc_cfg = budget_cfg.get("wall_clock", {})
                if "max" in wc_cfg:
                    max_sec = _parse_duration(wc_cfg["max"])
                    if elapsed > max_sec:
                        self.state = "NEEDS_INPUT"
                        self._emit_event("BUDGET_EXHAUSTED", {"type": "wall_clock", "spent": elapsed})
                        raise RuntimeError(f"Wall clock budget exhausted ({elapsed:.1f}s > {max_sec}s)")

            # Record action
            self.budget_spent["tokens"] = new_tokens
            self.budget_spent["usd"] = new_cost
            self.budget_spent["actions"] = new_actions
            self.task_tokens += tokens

            self._emit_event("ACTION_EXECUTED", {
                "capability": capability_uri,
                "tokens": tokens,
                "cost_usd": cost_usd
            })
            return {"status": "SUCCESS", "capability": capability_uri}

    def finish_execution(self):
        """
        Agent declares task execution finished.
        Invariant 1: Complete != Verified.
        Transitions state to VERIFYING, NOT VERIFIED.
        """
        with self._lock:
            assert self.state == "RUNNING", f"Cannot finish execution from state {self.state}"
            self.state = "VERIFYING"
            self._emit_event("EXECUTION_FINISHED_AWAITING_VERIFICATION", {
                "mission_id": self.mission["metadata"]["id"],
                "required_criteria": self.mission.get("success", {}).get("all", [])
            })

    def record_evidence(self, evidence_item):
        """Validates and records an EvidenceItem."""
        with self._lock:
            jsonschema.validate(instance=evidence_item, schema=self.evidence_schema)
            crit = evidence_item["criterion_ref"]
            self.evidence_store[crit] = evidence_item
            
            # Track verification control plane tax
            self.control_plane_tokens += 120  # verification processing overhead
            self._emit_event("EVIDENCE_RECORDED", {
                "criterion": crit,
                "tier": evidence_item["tier"],
                "result": evidence_item["result"]
            })

    def evaluate_verification(self):
        """
        Invariant 2: Verified requires satisfied acceptance criteria backed by qualifying evidence.
        Enforces assurance minimum_tier and evaluates both 'all' and 'any' criteria.
        """
        with self._lock:
            assert self.state in ("VERIFYING", "RECOVERING"), f"Cannot evaluate verification from state {self.state}"
            
            # Check contract integrity before evaluating
            self.verify_integrity()

            required_all = self.mission.get("success", {}).get("all", [])
            required_any = self.mission.get("success", {}).get("any", [])

            assurance_cfg = self.mission.get("assurance", {}).get("verification", {})
            min_tier_name = assurance_cfg.get("minimum_tier", "tier_2_deterministic" if assurance_cfg.get("independence") == "required" else "tier_1_model")
            min_tier_val = TIER_HIERARCHY.get(min_tier_name, 1)

            missing_or_failed = []

            for crit in required_all:
                evidence = self.evidence_store.get(crit)
                if not evidence:
                    missing_or_failed.append((crit, "MISSING_EVIDENCE"))
                elif evidence["result"] != "SATISFIED":
                    missing_or_failed.append((crit, f"RESULT_{evidence['result']}"))
                else:
                    ev_tier_val = TIER_HIERARCHY.get(evidence.get("tier"), 0)
                    if ev_tier_val == 0:
                        missing_or_failed.append((crit, "TIER_0_UNACCEPTABLE"))
                    elif ev_tier_val < min_tier_val:
                        missing_or_failed.append((crit, f"TIER_INSUFFICIENT_{evidence.get('tier')}_REQUIRES_{min_tier_name}"))

            if required_any:
                any_passed = False
                for crit in required_any:
                    ev = self.evidence_store.get(crit)
                    if ev and ev["result"] == "SATISFIED":
                        ev_tier_val = TIER_HIERARCHY.get(ev.get("tier"), 0)
                        if ev_tier_val >= min_tier_val and ev_tier_val > 0:
                            any_passed = True
                            break
                if not any_passed:
                    missing_or_failed.append(("ANY_CRITERIA", "NO_ANY_CRITERIA_SATISFIED"))

            if not missing_or_failed:
                self.state = "VERIFIED"
                if self.start_time:
                    self.budget_spent["wall_clock_seconds"] = time.time() - self.start_time
                self._emit_event("MISSION_VERIFIED", {"satisfied_criteria": required_all + required_any})
                return True
            else:
                # Check recovery policy
                recovery = self.mission.get("recovery", {})
                retry_limit = recovery.get("retry_limit", 0)
                if retry_limit > 0:
                    self.state = "RECOVERING"
                    self._emit_event("VERIFICATION_FAILED_RECOVERING", {"reasons": missing_or_failed})
                else:
                    self.state = "FAILED"
                    self._emit_event("VERIFICATION_FAILED_TERMINAL", {"reasons": missing_or_failed})
                return False

    def get_control_plane_tax(self):
        """Calculates Control Plane Tax: control tokens / total tokens."""
        with self._lock:
            total = self.control_plane_tokens + self.task_tokens
            if total == 0:
                return 0.0
            return self.control_plane_tokens / total

    def get_metrics(self):
        with self._lock:
            return {
                "state": self.state,
                "is_verified": self.state == "VERIFIED",
                "is_false_completion_prevented": self.state in ("RECOVERING", "FAILED") and len(self.evidence_store) > 0,
                "budget_spent": dict(self.budget_spent),
                "control_plane_tokens": self.control_plane_tokens,
                "task_tokens": self.task_tokens,
                "control_plane_tax": self.get_control_plane_tax(),
                "trajectory_length": len(self.trajectory)
            }

