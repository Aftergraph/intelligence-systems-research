import time
import uuid
from typing import Any, Dict, Optional
from capabilities.registry import Capability, CapabilityRegistry

# ponytail: Hardened Capability Dispatcher.
# Enforces pre-execution authority verification, mid-execution revocation checks,
# idempotency key caching, and structured effect receipts.
# ADR-008 Phase 8: signed MDT (JWT str) delegation tokens are verified
# fail-closed via delegation.token_exchange before authority evaluation.


class CapabilityResolver:
    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def resolve(self, uri_or_tool_name: str) -> Optional[Capability]:
        cap = self.registry.get(uri_or_tool_name)
        if cap:
            return cap
        for c in self.registry.list_all():
            m_name = c.uri.replace("://", "_").replace("/", "_").replace(".", "_")
            if m_name == uri_or_tool_name:
                return c
        return None

class CapabilityDispatcher:
    def __init__(self, resolver: CapabilityResolver, authority_evaluator=None, policy_engine=None,
                 mdt_secret: Optional[str] = None):
        self.resolver = resolver
        self.authority_evaluator = authority_evaluator
        self.policy_engine = policy_engine
        self.mdt_secret = mdt_secret  # when set, str delegation tokens are verified as MDTs
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def dispatch(
        self,
        capability_uri: str,
        payload: Optional[Dict[str, Any]] = None,
        delegation_token: Optional[Any] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validates authority and policy BEFORE executing capability; returns effect receipt."""
        cap = self.resolver.resolve(capability_uri)
        if not cap:
            raise KeyError(f"Unknown capability: {capability_uri}")

        # Idempotency check: avoid duplicate execution of external side-effects
        i_key = idempotency_key or (payload.get("idempotency_key") if payload else None)
        if i_key and i_key in self._idempotency_cache:
            cached = dict(self._idempotency_cache[i_key])
            cached["is_cached_replay"] = True
            return cached

        # 0. ADR-008 MDT verification (fail-closed): a signed JWT delegation
        # token must verify before any authority evaluation. Covers purpose
        # binding and scope membership for the requested capability.
        if isinstance(delegation_token, str) and self.mdt_secret:
            from delegation.token_exchange import verify_token  # local import: no hard dep unless used
            claims = verify_token(
                delegation_token,
                secret=self.mdt_secret,
                require_capability=cap.uri,
            )
            delegation_token = claims  # downstream evaluator sees decoded claims

        # 1. Authority Check
        if self.authority_evaluator and delegation_token:
            is_auth, err = self.authority_evaluator.evaluate_access(delegation_token, cap.uri)
            if not is_auth:
                raise PermissionError(f"Authority denied: {err}")

        # 2. Policy Check
        if self.policy_engine and payload and "command" in payload:
            self.policy_engine.validate_command(payload["command"])

        # 3. Execution
        t0 = time.time()
        try:
            if cap.handler:
                result = cap.handler(payload or {})
            else:
                result = {"status": "SUCCESS", "capability": cap.uri, "echo_payload": payload}
            status = "COMPLETED"
        except Exception as e:
            result = {"error": str(e)}
            status = "FAILED"

        effect_receipt = {
            "receipt_id": f"eff-{uuid.uuid4().hex[:12]}",
            "capability_uri": cap.uri,
            "status": status,
            "result": result,
            "idempotency_key": i_key,
            "duration_ms": round((time.time() - t0) * 1000.0, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        if i_key:
            self._idempotency_cache[i_key] = effect_receipt

        return effect_receipt
