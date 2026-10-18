from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from pathlib import Path
from typing import Any

import httpx

from .node_gateway import client_mtls_context
from .node_transport import HttpNodeTransport, NodeProtocol
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from .remote_worker import RemoteWorkerClient


@dataclass(frozen=True, slots=True)
class NodeClientConfig:
    sender_id: str
    worker_id: str
    endpoint_url: str
    ca_file: Path
    certificate_file: Path
    private_key_file: Path
    signing_key_file: Path
    signing_key_id: str
    worker_public_key_b64: str
    timeout_s: float = 15.0

    @classmethod
    def load_json(cls, path: str | Path) -> "NodeClientConfig":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("client config must be a JSON object")
        root = source.parent
        def p(name: str) -> Path:
            value = Path(str(data[name]))
            return value if value.is_absolute() else (root / value).resolve()
        cfg = cls(
            sender_id=str(data["sender_id"]), worker_id=str(data["worker_id"]),
            endpoint_url=str(data["endpoint_url"]), ca_file=p("ca_file"),
            certificate_file=p("certificate_file"), private_key_file=p("private_key_file"),
            signing_key_file=p("signing_key_file"), signing_key_id=str(data["signing_key_id"]),
            worker_public_key_b64=str(data["worker_public_key_b64"]),
            timeout_s=float(data.get("timeout_s") or 15.0),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not all(v.strip() for v in (self.sender_id, self.worker_id, self.endpoint_url, self.signing_key_id, self.worker_public_key_b64)):
            raise ValueError("client identity, endpoint and worker public key are required")
        for path in (self.ca_file, self.certificate_file, self.private_key_file, self.signing_key_file):
            if not path.is_file():
                raise FileNotFoundError(path)
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        HttpNodeTransport._validate_url(self.endpoint_url)


class NodeClientSession:
    def __init__(self, config: NodeClientConfig) -> None:
        self.config = config
        signer = Ed25519ReceiptSigner.load_private_key(key_id=config.signing_key_id, path=config.signing_key_file)
        worker_key = base64.b64decode(config.worker_public_key_b64)
        protocol = NodeProtocol(
            signer=signer,
            verifier=Ed25519ReceiptVerifier({config.signing_key_id: signer.public_key_bytes(), config.worker_id: worker_key}),
        )
        tls = client_mtls_context(
            ca_file=str(config.ca_file), certificate_file=str(config.certificate_file),
            private_key_file=str(config.private_key_file),
        )
        self.http = httpx.Client(verify=tls, timeout=config.timeout_s)
        transport = HttpNodeTransport(timeout_s=config.timeout_s, client=self.http)
        self.client = RemoteWorkerClient(
            sender_id=config.sender_id, worker_id=config.worker_id, protocol=protocol,
            send=lambda message: transport.post(config.endpoint_url, message),
        )

    def describe(self) -> dict[str, Any]:
        result = self.client.call("node_describe", {})
        if not result.ok:
            raise RuntimeError(str(result.payload))
        return dict(result.payload)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "NodeClientSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def generate_client_config_template(*, sender_id: str, worker_id: str, endpoint_url: str) -> dict[str, Any]:
    return {
        "sender_id": sender_id,
        "worker_id": worker_id,
        "endpoint_url": endpoint_url,
        "ca_file": "secrets/ca.crt.pem",
        "certificate_file": "secrets/coordinator.crt.pem",
        "private_key_file": "secrets/coordinator.key.pem",
        "signing_key_file": "secrets/coordinator.ed25519.key",
        "signing_key_id": sender_id,
        "worker_public_key_b64": "BASE64_ED25519_PUBLIC_KEY",
        "timeout_s": 15,
    }
