from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
from threading import Thread
from typing import Any, Callable, Mapping

from .node_transport import NodeProtocol, NodeRequest, NodeResponse, SignedNodeMessage


@dataclass(frozen=True, slots=True)
class NodeCallContext:
    request: NodeRequest
    peer_certificate: dict[str, Any] | None = None


class OperationRegistry:
    """Server-side capability registry.

    Remote callers choose only an operation name. They cannot supply a shell
    command or dynamically register code on the worker.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[NodeCallContext], Mapping[str, Any]]] = {}

    def register(self, operation: str, handler: Callable[[NodeCallContext], Mapping[str, Any]]) -> None:
        if not operation.strip() or operation.startswith("shell"):
            raise ValueError("operation must be a bounded non-shell name")
        if operation in self._handlers:
            raise ValueError(f"operation already registered: {operation}")
        self._handlers[operation] = handler

    def execute(self, context: NodeCallContext) -> dict[str, Any]:
        try:
            handler = self._handlers[context.request.operation]
        except KeyError as exc:
            raise RuntimeError("unsupported remote operation") from exc
        return dict(handler(context))


class NodeGateway:
    """Application-layer signed gateway for one Aftergraph worker node."""

    def __init__(
        self, *, node_id: str, protocol: NodeProtocol, operations: OperationRegistry,
        bind_peer_common_name: bool = True,
        sender_key_bindings: Mapping[str, frozenset[str]] | None = None,
    ) -> None:
        if not node_id.strip():
            raise ValueError("node_id must be non-empty")
        self.node_id = node_id
        self.protocol = protocol
        self.operations = operations
        self.bind_peer_common_name = bind_peer_common_name
        self.sender_key_bindings = {str(k): frozenset(str(v) for v in values) for k, values in (sender_key_bindings or {}).items()}
        self._seen_nonces: set[str] = set()

    @staticmethod
    def _peer_common_name(peer_certificate: dict[str, Any] | None) -> str | None:
        if not peer_certificate:
            return None
        for rdn in peer_certificate.get("subject", ()):
            for key, value in rdn:
                if key == "commonName":
                    return str(value)
        return None

    def handle(self, raw: Mapping[str, Any], *, peer_certificate: dict[str, Any] | None = None) -> dict[str, Any]:
        message = SignedNodeMessage.from_dict(raw)
        body = self.protocol.verify(message, expected_kind="aftergraph.node-request/v1")
        sender = str(body.get("sender") or "")
        if self.sender_key_bindings:
            allowed_keys = self.sender_key_bindings.get(sender)
            if not allowed_keys or message.receipt.key_id not in allowed_keys:
                raise RuntimeError("signed request sender is not bound to the application signing key")
        if body.get("recipient") != self.node_id:
            raise RuntimeError("node request recipient mismatch")
        nonce = str(body.get("nonce") or "")
        if not nonce or nonce in self._seen_nonces:
            raise RuntimeError("node request nonce missing or replayed")
        self._seen_nonces.add(nonce)
        request = NodeRequest(
            request_id=str(body["request_id"]), sender=str(body["sender"]),
            recipient=str(body["recipient"]), operation=str(body["operation"]),
            payload=dict(body.get("payload") or {}), sent_at=str(body["sent_at"]), nonce=nonce,
        )
        peer_cn = self._peer_common_name(peer_certificate)
        if self.bind_peer_common_name and peer_cn is not None and peer_cn != request.sender:
            raise RuntimeError("mTLS peer identity does not match signed request sender")
        try:
            payload = self.operations.execute(NodeCallContext(request, peer_certificate))
            ok = True
        except Exception as exc:
            payload = {"error": type(exc).__name__, "message": str(exc)}
            ok = False
        response = NodeResponse(
            request_id=request.request_id,
            responder=self.node_id,
            ok=ok,
            payload=payload,
            observed_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.protocol.sign_response(response).to_dict()


class NodeGatewayServer:
    """Actual HTTP(S) node server for the signed node protocol.

    mTLS is enabled by passing an SSLContext configured with CERT_REQUIRED.
    """

    def __init__(
        self,
        *,
        gateway: NodeGateway,
        host: str = "127.0.0.1",
        port: int = 0,
        ssl_context: ssl.SSLContext | None = None,
        max_body_bytes: int = 1_000_000,
    ) -> None:
        self.gateway = gateway
        self.max_body_bytes = max_body_bytes
        outer = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "AftergraphNode/2.0"
            def log_message(self, fmt: str, *args: object) -> None:
                return
            def _send(self, status: int, payload: Mapping[str, Any]) -> None:
                body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/healthz":
                    self._send(200, {"ok": True, "node_id": outer.gateway.node_id})
                else:
                    self._send(404, {"error": "not_found"})
            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/v1/node/call":
                    self._send(404, {"error": "not_found"}); return
                try:
                    length = int(self.headers.get("content-length", "0"))
                    if length <= 0 or length > outer.max_body_bytes:
                        raise ValueError("invalid request body size")
                    raw = json.loads(self.rfile.read(length))
                    if not isinstance(raw, dict):
                        raise TypeError("request body must be a JSON object")
                    peer = None
                    try:
                        peer = self.connection.getpeercert()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    result = outer.gateway.handle(raw, peer_certificate=peer)
                except Exception as exc:
                    self._send(400, {"error": type(exc).__name__, "message": str(exc)}); return
                self._send(200, result)

        self._server = ThreadingHTTPServer((host, port), Handler)
        if ssl_context is not None:
            self._server.socket = ssl_context.wrap_socket(self._server.socket, server_side=True)
        self._thread: Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def start(self) -> "NodeGatewayServer":
        if self._thread is not None:
            return self
        self._thread = Thread(target=self._server.serve_forever, name="aftergraph-node-gateway", daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> "NodeGatewayServer":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def server_mtls_context(*, ca_file: str, certificate_file: str, private_key_file: str) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certificate_file, private_key_file)
    context.load_verify_locations(cafile=ca_file)
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def client_mtls_context(*, ca_file: str, certificate_file: str, private_key_file: str) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    context.load_cert_chain(certificate_file, private_key_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context
