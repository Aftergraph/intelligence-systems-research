"""AIE-backed topology boundary for STUDY-012B behavioral validation.

The wrapper does not decide benchmark outcomes. It delegates topology admission
to the real AIE ``AdmissionEngine.authorize_topology_mutation`` path before the
fixture capability handler can mutate local topology state.
"""
from __future__ import annotations

from typing import Any, Iterable

from aie_runtime.engine import AdmissionEngine
from aie_runtime.store import InMemoryState


class AIETopologyGuardedDispatcher:
    """Compose AIE topology admission ahead of an existing dispatcher."""

    def __init__(
        self,
        *,
        dispatcher: Any,
        topology_capabilities: Iterable[str],
        allowed_targets: Iterable[str] = (),
    ) -> None:
        self.dispatcher = dispatcher
        self.topology_capabilities = frozenset(topology_capabilities)
        self.allowed_targets = frozenset(allowed_targets)
        self.engine = AdmissionEngine(
            InMemoryState(),
            policy=self._policy,
        )

    def _policy(self, decision: dict[str, Any]) -> bool:
        """Allow only explicitly declared topology targets, fail closed otherwise."""
        if decision.get("type") != "topology":
            return False
        target = decision.get("target")
        return isinstance(target, str) and target in self.allowed_targets

    def dispatch(
        self,
        capability_uri: str,
        payload: dict[str, Any] | None = None,
        delegation_token: Any | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(payload or {})
        if capability_uri in self.topology_capabilities:
            actor = "study012b-actor"
            if isinstance(delegation_token, dict):
                delegate = delegation_token.get("delegate")
                if isinstance(delegate, str) and delegate:
                    actor = delegate
            mutation = str(payload.get("mutation", "join"))
            target = str(payload.get("child", payload.get("target", "")))
            if not target:
                # A malformed topology request is not allowed to bypass the
                # topology boundary by presenting an empty target.
                target = "<missing-target>"
            self.engine.authorize_topology_mutation(
                actor=actor,
                mutation=mutation,
                target=target,
            )

        return self.dispatcher.dispatch(
            capability_uri,
            payload,
            delegation_token,
            idempotency_key,
        )
