import copy
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# ponytail: Hardened Delegation Manager enforcing Monotonic Attenuation (Invariant 3).
# Enforces A_child ⊆ A_parent, delegation depth decrementing, budget conservation, and cascade revocation.

class DelegationManager:
    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._child_map: Dict[str, List[str]] = {}

    def register_delegation(self, token: Dict[str, Any]):
        t_id = token["id"]
        self._tokens[t_id] = copy.deepcopy(token)
        if t_id not in self._child_map:
            self._child_map[t_id] = []

    def get_delegation(self, token_id: str) -> Optional[Dict[str, Any]]:
        return self._tokens.get(token_id)

    def issue_subdelegation(
        self,
        parent_id: str,
        child_id: str,
        delegate_uri: str,
        purpose: str,
        allowed_capabilities: List[str],
        denied_capabilities: Optional[List[str]] = None,
        budget_limit: Optional[Dict[str, Any]] = None,
        valid_from: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enforces Invariant 3: Monotonic Authority Attenuation and Bounded Budget."""
        parent = self._tokens.get(parent_id)
        if not parent:
            raise KeyError(f"Parent delegation {parent_id} not found")
        if parent.get("revoked", False):
            raise PermissionError("Parent delegation is revoked")

        parent_depth = parent.get("scope", {}).get("max_delegation_depth", 1)
        if parent_depth <= 0:
            raise PermissionError("Parent delegation has reached maximum delegation depth (depth=0)")

        # Verify monotonicity: child capabilities MUST be subset of parent
        parent_allowed = parent.get("scope", {}).get("allowed_capabilities", [])
        for c in allowed_capabilities:
            matched = any(
                c == pa or (pa.endswith("*") and c.startswith(pa[:-1])) or pa == "*"
                for pa in parent_allowed
            )
            if not matched:
                raise PermissionError(f"Scope widening detected: '{c}' is not granted to parent delegation")

        # Child denied must include all parent denied
        merged_denied = list(set(parent.get("scope", {}).get("denied_capabilities", []) + (denied_capabilities or [])))

        # Budget bounding
        parent_budget = parent.get("budget", {})
        child_budget = budget_limit or {}
        if parent_budget.get("tokens") and child_budget.get("tokens"):
            if child_budget["tokens"] > parent_budget["tokens"]:
                raise PermissionError(f"Child budget tokens ({child_budget['tokens']}) exceeds parent ceiling ({parent_budget['tokens']})")

        child_token = {
            "id": child_id,
            "principal": parent["delegate"],
            "delegate": delegate_uri,
            "purpose": purpose,
            "scope": {
                "allowed_capabilities": allowed_capabilities,
                "denied_capabilities": merged_denied,
                "max_delegation_depth": parent_depth - 1
            },
            "budget": child_budget,
            "valid_from": valid_from or parent.get("valid_from", "2026-09-01T00:00:00Z"),
            "expires_at": expires_at or parent.get("expires_at", "2026-09-30T00:00:00Z"),
            "parent_id": parent_id,
            "revoked": False
        }

        self.register_delegation(child_token)
        self._child_map[parent_id].append(child_id)
        return child_token

    def get_delegation_chain(self, token_id: str) -> List[str]:
        chain = []
        curr = token_id
        while curr:
            chain.append(curr)
            curr_token = self._tokens.get(curr)
            curr = curr_token.get("parent_id") if curr_token else None
        return chain

    def revoke_subtree(self, root_token_id: str):
        """Cascades revocation to all descendant delegations in O(k) time."""
        to_revoke = [root_token_id]
        while to_revoke:
            curr = to_revoke.pop()
            if curr in self._tokens:
                self._tokens[curr]["revoked"] = True
            children = self._child_map.get(curr, [])
            to_revoke.extend(children)
