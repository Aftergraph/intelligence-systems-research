"""Behaviorally real local filesystem sandbox for STUDY-012B.

The sandbox is deliberately a mechanism boundary, not an outcome oracle. It
knows only an allowed filesystem root and the concrete target resolved by the
domain adapter. It never receives a scenario id, treatment label, expected
winner, or endpoint value.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class SandboxViolation(PermissionError):
    """Raised before a capability handler can cross the local sandbox root."""


class LocalFilesystemSandbox:
    """Constrain resolved filesystem targets to one concrete local root."""

    def __init__(self, allowed_root: Path | str) -> None:
        root = Path(allowed_root)
        root.mkdir(parents=True, exist_ok=True)
        self.allowed_root = root.resolve()

    def require_target(self, target: Path | str) -> Path:
        candidate = Path(target)
        if not candidate.is_absolute():
            candidate = self.allowed_root / candidate

        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise SandboxViolation(f"Sandbox boundary could not resolve target: {target}") from exc

        if resolved == self.allowed_root or self.allowed_root in resolved.parents:
            return resolved

        raise SandboxViolation(
            f"Sandbox boundary denied target outside allowed root: {resolved}"
        )


TargetResolver = Callable[[str, dict[str, Any]], Path | str | None]


class SandboxedCapabilityDispatcher:
    """Apply a target boundary before delegating to the real dispatcher."""

    def __init__(self, *, dispatcher: Any, sandbox: LocalFilesystemSandbox, target_resolver: TargetResolver) -> None:
        self._dispatcher = dispatcher
        self._sandbox = sandbox
        self._target_resolver = target_resolver

    def dispatch(
        self,
        capability_uri: str,
        payload: dict[str, Any] | None = None,
        delegation_token: Any = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        concrete_payload = dict(payload or {})
        target = self._target_resolver(capability_uri, concrete_payload)
        if target is not None:
            self._sandbox.require_target(target)

        return self._dispatcher.dispatch(
            capability_uri,
            concrete_payload,
            delegation_token,
            idempotency_key=idempotency_key,
        )
