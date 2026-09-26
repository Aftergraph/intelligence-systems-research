from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import base64
import hashlib
import json
from typing import Any, Callable, Mapping

import httpx

from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier, PublicSignedReceipt


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class NodeRequest:
    request_id: str
    sender: str
    recipient: str
    operation: str
    payload: dict[str, Any]
    sent_at: str
    nonce: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NodeResponse:
    request_id: str
    responder: str
    ok: bool
    payload: dict[str, Any]
    observed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SignedNodeMessage:
    receipt: PublicSignedReceipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload": self.receipt.payload,
            "key_id": self.receipt.key_id,
            "algorithm": self.receipt.algorithm,
            "payload_sha256": self.receipt.payload_sha256,
            "signature_b64": self.receipt.signature_b64,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SignedNodeMessage":
        return cls(PublicSignedReceipt(
            payload=dict(data["payload"]),
            key_id=str(data["key_id"]),
            algorithm=str(data["algorithm"]),
            payload_sha256=str(data["payload_sha256"]),
            signature_b64=str(data["signature_b64"]),
        ))


class NodeProtocol:
    """Signed request/response protocol for Aftergraph node transports.

    The protocol authenticates application messages independently of the wire
    transport. TLS is still mandatory for HTTP outside loopback tests.
    """

    def __init__(self, *, signer: Ed25519ReceiptSigner, verifier: Ed25519ReceiptVerifier) -> None:
        self.signer = signer
        self.verifier = verifier

    def sign_request(self, request: NodeRequest) -> SignedNodeMessage:
        return SignedNodeMessage(self.signer.sign({"kind": "aftergraph.node-request/v1", **request.to_dict()}))

    def sign_response(self, response: NodeResponse) -> SignedNodeMessage:
        return SignedNodeMessage(self.signer.sign({"kind": "aftergraph.node-response/v1", **response.to_dict()}))

    def verify(self, message: SignedNodeMessage, *, expected_kind: str) -> dict[str, Any]:
        if not self.verifier.verify(message.receipt):
            raise RuntimeError("node message signature verification failed")
        payload = dict(message.receipt.payload)
        if payload.get("kind") != expected_kind:
            raise RuntimeError("node message kind mismatch")
        return payload


class HttpNodeTransport:
    """Minimal signed JSON transport for Aftergraph nodes.

    Only loopback HTTP is allowed without TLS. Remote endpoints must use HTTPS.
    This class transports bounded protocol payloads; it does not expose shell
    execution or arbitrary host access.
    """

    def __init__(self, *, timeout_s: float = 15.0, client: httpx.Client | None = None) -> None:
        self.timeout_s = timeout_s
        self._client = client

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = httpx.URL(url)
        host = (parsed.host or "").lower()
        loopback = host in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("remote node transport requires HTTPS")

    def post(self, url: str, message: SignedNodeMessage) -> SignedNodeMessage:
        self._validate_url(url)
        client = self._client or httpx.Client(timeout=self.timeout_s)
        owns = self._client is None
        try:
            response = client.post(url, json=message.to_dict(), headers={"content-type": "application/json"})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError("node transport returned non-object JSON")
            return SignedNodeMessage.from_dict(data)
        finally:
            if owns:
                client.close()


class InMemoryNodeEndpoint:
    """Deterministic transport endpoint used for protocol verification and tests."""

    def __init__(
        self,
        *,
        node_id: str,
        protocol: NodeProtocol,
        handler: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.node_id = node_id
        self.protocol = protocol
        self.handler = handler
        self._seen_nonces: set[str] = set()

    def handle(self, message: SignedNodeMessage, *, now: datetime | None = None) -> SignedNodeMessage:
        body = self.protocol.verify(message, expected_kind="aftergraph.node-request/v1")
        if body.get("recipient") != self.node_id:
            raise RuntimeError("node request recipient mismatch")
        nonce = str(body.get("nonce", ""))
        if not nonce or nonce in self._seen_nonces:
            raise RuntimeError("node request nonce missing or replayed")
        self._seen_nonces.add(nonce)
        result = self.handler(str(body["operation"]), dict(body.get("payload") or {}))
        observed = (now or datetime.now(timezone.utc)).isoformat()
        response = NodeResponse(
            request_id=str(body["request_id"]),
            responder=self.node_id,
            ok=True,
            payload=result,
            observed_at=observed,
        )
        return self.protocol.sign_response(response)
