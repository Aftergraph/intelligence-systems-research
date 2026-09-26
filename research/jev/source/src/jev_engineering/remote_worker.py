from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import secrets
import uuid
from typing import Any, Callable

from .node_transport import InMemoryNodeEndpoint, NodeProtocol, NodeRequest, SignedNodeMessage


@dataclass(frozen=True, slots=True)
class RemoteExecutionResult:
    request_id: str
    worker_id: str
    ok: bool
    payload: dict[str, Any]


class RemoteWorkerClient:
    """Bounded client for dispatching typed operations to a verified worker endpoint."""

    def __init__(
        self,
        *,
        sender_id: str,
        worker_id: str,
        protocol: NodeProtocol,
        send: Callable[[SignedNodeMessage], SignedNodeMessage],
    ) -> None:
        self.sender_id = sender_id
        self.worker_id = worker_id
        self.protocol = protocol
        self.send = send

    def call(self, operation: str, payload: dict[str, Any]) -> RemoteExecutionResult:
        if not operation or operation.startswith("shell"):
            raise ValueError("operation must be a bounded non-shell protocol operation")
        request_id = uuid.uuid4().hex
        req = NodeRequest(
            request_id=request_id,
            sender=self.sender_id,
            recipient=self.worker_id,
            operation=operation,
            payload=dict(payload),
            sent_at=datetime.now(timezone.utc).isoformat(),
            nonce=secrets.token_hex(16),
        )
        response_msg = self.send(self.protocol.sign_request(req))
        body = self.protocol.verify(response_msg, expected_kind="aftergraph.node-response/v1")
        if body.get("request_id") != request_id:
            raise RuntimeError("node response request_id mismatch")
        if body.get("responder") != self.worker_id:
            raise RuntimeError("node response responder mismatch")
        return RemoteExecutionResult(
            request_id=request_id,
            worker_id=self.worker_id,
            ok=bool(body.get("ok")),
            payload=dict(body.get("payload") or {}),
        )
