from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from pathlib import Path
import shlex
import socket
from typing import Any, Mapping

from .durable_state import SqliteLeaseStore
from .node_gateway import NodeGateway, NodeGatewayServer, OperationRegistry, server_mtls_context
from .node_transport import NodeProtocol
from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
from .remote_control import FencedPreconfiguredVerifierCapability, LeaseControlService
from .streaming_journal import JournalStreamRegistry, JournalStreamService


@dataclass(frozen=True, slots=True)
class NodeAgentConfig:
    node_id: str
    host: str
    port: int
    ca_file: Path
    certificate_file: Path
    private_key_file: Path
    signing_key_file: Path
    signing_key_id: str
    peer_public_keys: dict[str, str]
    lease_db: Path
    verifier_workspace: Path
    verifier_command: tuple[str, ...]
    verifier_name: str
    verifier_timeout_s: float = 60.0
    peer_sender_key_ids: dict[str, str] | None = None
    lease_issuer_ids: tuple[str, ...] = ()
    lease_allowed_capabilities: tuple[str, ...] = (
        "verify_candidate",
        "journal_poll",
        "lease_heartbeat",
        "lease_renew",
    )
    lease_max_ttl_s: int = 3600

    @classmethod
    def load_json(cls, path: str | Path) -> "NodeAgentConfig":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("node config must be a JSON object")
        root = source.parent

        def p(name: str) -> Path:
            value = Path(str(data[name]))
            return value if value.is_absolute() else (root / value).resolve()

        command = data.get("verifier_command")
        if isinstance(command, str):
            command = tuple(shlex.split(command))
        elif isinstance(command, list):
            command = tuple(str(v) for v in command)
        else:
            raise ValueError("verifier_command must be a string or argv array")

        cfg = cls(
            node_id=str(data["node_id"]),
            host=str(data.get("host") or "127.0.0.1"),
            port=int(data.get("port") or 0),
            ca_file=p("ca_file"),
            certificate_file=p("certificate_file"),
            private_key_file=p("private_key_file"),
            signing_key_file=p("signing_key_file"),
            signing_key_id=str(data["signing_key_id"]),
            peer_public_keys={str(k): str(v) for k, v in dict(data.get("peer_public_keys") or {}).items()},
            lease_db=p("lease_db"),
            verifier_workspace=p("verifier_workspace"),
            verifier_command=command,
            verifier_name=str(data["verifier_name"]),
            verifier_timeout_s=float(data.get("verifier_timeout_s") or 60.0),
            peer_sender_key_ids=(
                {str(k): str(v) for k, v in dict(data.get("peer_sender_key_ids") or {}).items()}
                or None
            ),
            lease_issuer_ids=tuple(str(v) for v in (data.get("lease_issuer_ids") or [])),
            lease_allowed_capabilities=tuple(
                str(v)
                for v in (
                    data.get("lease_allowed_capabilities")
                    or ["verify_candidate", "journal_poll", "lease_heartbeat", "lease_renew"]
                )
            ),
            lease_max_ttl_s=int(data.get("lease_max_ttl_s") or 3600),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.node_id.strip() or not self.signing_key_id.strip() or not self.verifier_name.strip():
            raise ValueError("node_id, signing_key_id and verifier_name are required")
        if not (0 <= self.port <= 65535):
            raise ValueError("port must be in 0..65535")
        for path in (self.ca_file, self.certificate_file, self.private_key_file, self.signing_key_file):
            if not path.is_file():
                raise FileNotFoundError(path)
        if not self.verifier_workspace.is_dir():
            raise FileNotFoundError(self.verifier_workspace)
        if not self.verifier_command:
            raise ValueError("verifier_command must not be empty")
        if not self.peer_public_keys:
            raise ValueError("at least one peer public key is required")
        if self.verifier_timeout_s <= 0:
            raise ValueError("verifier_timeout_s must be positive")
        if self.lease_max_ttl_s <= 0 or self.lease_max_ttl_s > 86400:
            raise ValueError("lease_max_ttl_s must be in 1..86400")
        if self.peer_sender_key_ids:
            unknown = set(self.peer_sender_key_ids.values()) - set(self.peer_public_keys)
            if unknown:
                raise ValueError("peer_sender_key_ids references unknown signing key ids")
        if self.lease_issuer_ids and not self.peer_sender_key_ids:
            raise ValueError("remote lease issuance requires peer_sender_key_ids binding")
        if any(issuer not in (self.peer_sender_key_ids or {}) for issuer in self.lease_issuer_ids):
            raise ValueError("lease issuer must have an application sender-key binding")
        if not self.lease_allowed_capabilities:
            raise ValueError("lease_allowed_capabilities must not be empty")

    def public_summary(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "signing_key_id": self.signing_key_id,
            "peer_key_ids": sorted(self.peer_public_keys),
            "lease_db": str(self.lease_db),
            "verifier_workspace": str(self.verifier_workspace),
            "verifier_name": self.verifier_name,
            "verifier_command_argv0": self.verifier_command[0],
            "verifier_timeout_s": self.verifier_timeout_s,
            "lease_issuer_ids": sorted(self.lease_issuer_ids),
            "lease_allowed_capabilities": sorted(self.lease_allowed_capabilities),
            "application_sender_key_binding": bool(self.peer_sender_key_ids),
            "tls_required": True,
        }


def build_node_gateway(config: NodeAgentConfig) -> NodeGateway:
    """Build bounded node capabilities without opening an inbound socket."""
    signer = Ed25519ReceiptSigner.load_private_key(
        key_id=config.signing_key_id,
        path=config.signing_key_file,
    )
    peer_keys = {
        key_id: base64.b64decode(encoded)
        for key_id, encoded in config.peer_public_keys.items()
    }
    verifier = Ed25519ReceiptVerifier({config.signing_key_id: signer.public_key_bytes(), **peer_keys})
    protocol = NodeProtocol(signer=signer, verifier=verifier)
    leases = SqliteLeaseStore(config.lease_db)
    streams = JournalStreamRegistry()
    operations = OperationRegistry()
    LeaseControlService(
        leases,
        authorized_issuers=frozenset(config.lease_issuer_ids),
        allowed_capabilities=frozenset(config.lease_allowed_capabilities),
        max_issue_ttl_s=config.lease_max_ttl_s,
    ).register(operations)
    JournalStreamService(streams, leases=leases).register(operations)
    FencedPreconfiguredVerifierCapability(
        workspace=config.verifier_workspace,
        command=config.verifier_command,
        verifier_name=config.verifier_name,
        leases=leases,
        timeout_s=config.verifier_timeout_s,
        journal_streams=streams,
    ).register(operations)

    def describe(context) -> Mapping[str, Any]:
        capabilities = [
            "lease_heartbeat",
            "lease_renew",
            "verify_candidate",
            "journal_poll",
            "node_describe",
        ]
        if config.lease_issuer_ids:
            capabilities.insert(0, "lease_issue")
        return {
            "node_id": config.node_id,
            "hostname": socket.gethostname(),
            "capabilities": capabilities,
            "verifier": config.verifier_name,
            "tls": "mutual",
            "arbitrary_shell": False,
            "application_sender_key_binding": bool(config.peer_sender_key_ids),
        }

    operations.register("node_describe", describe)
    bindings = None
    if config.peer_sender_key_ids:
        bindings = {
            sender: frozenset({key_id})
            for sender, key_id in config.peer_sender_key_ids.items()
        }
    return NodeGateway(
        node_id=config.node_id,
        protocol=protocol,
        operations=operations,
        sender_key_bindings=bindings,
    )


class NodeAgent:
    """Deployable bounded Aftergraph node service with direct inbound mTLS transport."""

    def __init__(self, config: NodeAgentConfig) -> None:
        self.config = config
        gateway = build_node_gateway(config)
        tls = server_mtls_context(
            ca_file=str(config.ca_file),
            certificate_file=str(config.certificate_file),
            private_key_file=str(config.private_key_file),
        )
        self.server = NodeGatewayServer(
            gateway=gateway,
            host=config.host,
            port=config.port,
            ssl_context=tls,
        )

    @property
    def address(self) -> tuple[str, int]:
        return self.server.address

    def start(self) -> "NodeAgent":
        self.server.start()
        return self

    def close(self) -> None:
        self.server.close()

    def serve_forever(self) -> None:
        self.server._server.serve_forever()

    def __enter__(self) -> "NodeAgent":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def generate_node_config_template(*, node_id: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "host": "0.0.0.0",
        "port": 9443,
        "ca_file": "secrets/ca.crt.pem",
        "certificate_file": "secrets/node.crt.pem",
        "private_key_file": "secrets/node.key.pem",
        "signing_key_file": "secrets/node.ed25519.key",
        "signing_key_id": f"node:{node_id}",
        "peer_public_keys": {"coordinator": "BASE64_ED25519_PUBLIC_KEY"},
        "peer_sender_key_ids": {"coordinator": "coordinator"},
        "lease_issuer_ids": ["coordinator"],
        "lease_allowed_capabilities": [
            "verify_candidate",
            "journal_poll",
            "lease_heartbeat",
            "lease_renew",
        ],
        "lease_max_ttl_s": 3600,
        "lease_db": "state/leases.db",
        "verifier_workspace": "workspace",
        "verifier_command": ["python", "-m", "pytest", "-q"],
        "verifier_name": f"{node_id}-pytest",
        "verifier_timeout_s": 120,
    }
