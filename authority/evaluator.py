from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

def _parse_time(iso_str: str) -> Optional[datetime]:
    try:
        clean = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None

class AuthorityEvaluator:
    def __init__(self):
        pass

    def evaluate_access(self, delegation: Dict[str, Any], capability_uri: str) -> Tuple[bool, Optional[str]]:
        if delegation.get("revoked", False):
            return False, "Authority has been revoked"

        now = datetime.now(timezone.utc)
        if "valid_from" in delegation:
            vf = _parse_time(delegation["valid_from"])
            if vf and now < vf:
                return False, f"Delegation not yet valid (valid_from: {delegation['valid_from']})"

        if "expires_at" in delegation:
            exp = _parse_time(delegation["expires_at"])
            if exp and now > exp:
                return False, f"Delegation token expired at {delegation['expires_at']}"

        scope = delegation.get("scope", {})
        denied = scope.get("denied_capabilities", [])
        for d in denied:
            if d.endswith("*") and capability_uri.startswith(d[:-1]):
                return False, f"Capability {capability_uri} explicitly denied by pattern {d}"
            elif d == capability_uri:
                return False, f"Capability {capability_uri} explicitly denied"

        allowed = scope.get("allowed_capabilities", [])
        for a in allowed:
            if a == "*" or a == capability_uri or (a.endswith("*") and capability_uri.startswith(a[:-1])):
                return True, None

        return False, f"Capability {capability_uri} not granted by delegation scope"
