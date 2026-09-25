from __future__ import annotations

from dataclasses import dataclass, field
import base64
import json
from pathlib import Path
import socket
import socketserver
import ssl
import struct
from threading import Event, Lock, Thread
import time
from typing import Any, Mapping

from .node_gateway import NodeGateway, client_mtls_context, server_mtls_context
from .node_transport import SignedNodeMessage

_MAX_FRAME_BYTES = 8_000_000


def _peer_common_name(peer_certificate: Mapping[str, Any] | None) -> str | None:
    if not peer_certificate:
        return None
    for rdn in peer_certificate.get("subject", ()):
        for key, value in rdn:
            if key == "commonName":
                return str(value)
    return None


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("relay connection closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _send_frame(sock: socket.socket, payload: Mapping[str, Any]) -> None:
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not raw or len(raw) > _MAX_FRAME_BYTES:
        raise ValueError("relay frame exceeds size limit")
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def _recv_frame(sock: socket.socket) -> dict[str, Any]:
    header = _recv_exact(sock, 4)
    size = struct.unpack("!I", header)[0]
    if size <= 0 or size > _MAX_FRAME_BYTES:
        raise ValueError("invalid relay frame size")
    data = json.loads(_recv_exact(sock, size))
    if not isinstance(data, dict):
        raise TypeError("relay frame must be a JSON object")
    return data


@dataclass(slots=True)
class _NodeSession:
    node_id: str
    generation: int
    sock: socket.socket
    lock: Lock = field(default_factory=Lock)
    closed: Event = field(default_factory=Event)

    def close(self) -> None:
        if self.closed.is_set():
            return
        self.closed.set()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class RelayHubServer:
    """mTLS relay for outbound-only Aftergraph worker nodes.

    Worker nodes establish the long-lived outbound connection. Coordinators use
    separate authenticated connections to forward an already-signed NodeRequest.
    The relay never grants shell authority and does not replace the end-to-end
    Ed25519 application signature verified by the worker NodeGateway.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        ca_file: str | Path,
        certificate_file: str | Path,
        private_key_file: str | Path,
        allowed_node_ids: set[str],
        allowed_coordinator_ids: set[str],
        call_timeout_s: float = 30.0,
        generation_store: Any | None = None,
    ) -> None:
        if not allowed_node_ids or not allowed_coordinator_ids:
            raise ValueError("relay requires explicit node and coordinator allowlists")
        if call_timeout_s <= 0:
            raise ValueError("call_timeout_s must be positive")
        self.allowed_node_ids = set(allowed_node_ids)
        self.allowed_coordinator_ids = set(allowed_coordinator_ids)
        self.call_timeout_s = float(call_timeout_s)
        self.generation_store = generation_store
        self._sessions: dict[str, _NodeSession] = {}
        self._generations: dict[str, int] = {}
        self._state_lock = Lock()
        outer = self

        class RelayTcpServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

            def get_request(self):  # type: ignore[override]
                raw, address = super().get_request()
                try:
                    wrapped = outer._tls.wrap_socket(raw, server_side=True)
                except Exception:
                    raw.close()
                    raise
                return wrapped, address

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                sock = self.request
                assert isinstance(sock, ssl.SSLSocket)
                peer_cn = _peer_common_name(sock.getpeercert())
                try:
                    hello = _recv_frame(sock)
                    kind = str(hello.get("kind") or "")
                    if kind == "register":
                        outer._handle_register(sock, peer_cn, hello)
                    elif kind == "call":
                        outer._handle_call(sock, peer_cn, hello)
                    else:
                        raise RuntimeError("unsupported relay frame kind")
                except Exception as exc:
                    try:
                        _send_frame(sock, {"kind": "error", "error": type(exc).__name__, "message": str(exc)})
                    except Exception:
                        pass

        self._tls = server_mtls_context(
            ca_file=str(ca_file), certificate_file=str(certificate_file), private_key_file=str(private_key_file),
        )
        self._server = RelayTcpServer((host, int(port)), Handler)
        self._thread: Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def _handle_register(self, sock: socket.socket, peer_cn: str | None, hello: Mapping[str, Any]) -> None:
        node_id = str(hello.get("node_id") or "")
        if node_id not in self.allowed_node_ids:
            raise RuntimeError("node identity is not allowlisted")
        if peer_cn != node_id:
            raise RuntimeError("mTLS common-name identity does not match node identity")
        with self._state_lock:
            if self.generation_store is not None:
                generation = int(self.generation_store.next_generation(node_id))
            else:
                generation = self._generations.get(node_id, 0) + 1
            self._generations[node_id] = generation
            previous = self._sessions.get(node_id)
            session = _NodeSession(node_id=node_id, generation=generation, sock=sock)
            self._sessions[node_id] = session
            if previous is not None:
                previous.close()
        _send_frame(sock, {"kind": "registered", "node_id": node_id, "generation": generation})
        # Keep this handler alive while coordinator threads synchronously use the
        # registered socket. No second reader is allowed on the worker stream.
        session.closed.wait()
        with self._state_lock:
            if self._sessions.get(node_id) is session:
                self._sessions.pop(node_id, None)

    def _handle_call(self, sock: socket.socket, peer_cn: str | None, hello: Mapping[str, Any]) -> None:
        if peer_cn not in self.allowed_coordinator_ids:
            raise RuntimeError("coordinator identity is not allowlisted")
        node_id = str(hello.get("node_id") or "")
        raw_message = hello.get("message")
        if not isinstance(raw_message, dict):
            raise TypeError("relay call requires a signed node message")
        with self._state_lock:
            session = self._sessions.get(node_id)
        if session is None or session.closed.is_set():
            raise RuntimeError(f"node not registered: {node_id}")
        with session.lock:
            old_timeout = session.sock.gettimeout()
            try:
                session.sock.settimeout(self.call_timeout_s)
                _send_frame(session.sock, {
                    "kind": "forward",
                    "generation": session.generation,
                    "message": raw_message,
                })
                response = _recv_frame(session.sock)
            except Exception:
                session.close()
                raise
            finally:
                try:
                    session.sock.settimeout(old_timeout)
                except OSError:
                    pass
        if response.get("kind") != "result":
            raise RuntimeError("worker returned invalid relay response")
        if int(response.get("generation") or 0) != session.generation:
            raise RuntimeError("worker relay session generation mismatch")
        message = response.get("message")
        if not isinstance(message, dict):
            raise RuntimeError("worker relay result missing signed response")
        _send_frame(sock, {"kind": "result", "node_id": node_id, "generation": session.generation, "message": message})

    def is_registered(self, node_id: str) -> bool:
        with self._state_lock:
            session = self._sessions.get(node_id)
            return bool(session is not None and not session.closed.is_set())

    def session_generation(self, node_id: str) -> int:
        with self._state_lock:
            in_memory = int(self._generations.get(node_id, 0))
        if self.generation_store is not None:
            return max(in_memory, int(self.generation_store.current_generation(node_id)))
        return in_memory

    def start(self) -> "RelayHubServer":
        if self._thread is None:
            self._thread = Thread(target=self._server.serve_forever, name="aftergraph-relay-hub", daemon=True)
            self._thread.start()
        return self

    def close(self) -> None:
        with self._state_lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            session.close()
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> "RelayHubServer":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class RelayNodeAgent:
    """Outbound-only node connector for NAT/firewall constrained workers."""

    def __init__(
        self,
        *,
        node_id: str,
        relay_host: str,
        relay_port: int,
        ca_file: str | Path,
        certificate_file: str | Path,
        private_key_file: str | Path,
        gateway: NodeGateway,
        reconnect: bool = True,
        reconnect_delay_s: float = 0.25,
        connect_timeout_s: float = 5.0,
        server_name: str | None = None,
    ) -> None:
        if not node_id.strip() or not relay_host.strip() or relay_port <= 0:
            raise ValueError("node_id and relay address are required")
        if reconnect_delay_s < 0 or connect_timeout_s <= 0:
            raise ValueError("relay timing values are invalid")
        self.node_id = node_id
        self.relay_host = relay_host
        self.relay_port = int(relay_port)
        self.gateway = gateway
        self.reconnect = bool(reconnect)
        self.reconnect_delay_s = float(reconnect_delay_s)
        self.connect_timeout_s = float(connect_timeout_s)
        self.server_name = server_name or relay_host
        self._tls = client_mtls_context(
            ca_file=str(ca_file), certificate_file=str(certificate_file), private_key_file=str(private_key_file),
        )
        self._stop = Event()
        self._registered = Event()
        self._disconnected = Event()
        self._thread: Thread | None = None
        self._sock: socket.socket | None = None
        self.session_generation = 0
        self.last_error: Exception | None = None

    @property
    def local_listen_port(self) -> None:
        return None

    @property
    def disconnected(self) -> bool:
        return self._disconnected.is_set()

    @property
    def registered(self) -> bool:
        return self._registered.is_set()

    def _connect_once(self) -> None:
        raw = socket.create_connection((self.relay_host, self.relay_port), timeout=self.connect_timeout_s)
        try:
            sock = self._tls.wrap_socket(raw, server_hostname=self.server_name)
        except Exception:
            raw.close()
            raise
        self._sock = sock
        _send_frame(sock, {"kind": "register", "node_id": self.node_id})
        ack = _recv_frame(sock)
        if ack.get("kind") == "error":
            raise RuntimeError(str(ack.get("message") or ack.get("error") or "relay registration failed"))
        if ack.get("kind") != "registered" or ack.get("node_id") != self.node_id:
            raise RuntimeError("relay registration acknowledgement mismatch")
        self.session_generation = int(ack.get("generation") or 0)
        if self.session_generation <= 0:
            raise RuntimeError("relay session generation missing")
        self._registered.set()
        self._disconnected.clear()
        while not self._stop.is_set():
            frame = _recv_frame(sock)
            if frame.get("kind") != "forward":
                raise RuntimeError("unexpected relay frame for node")
            generation = int(frame.get("generation") or 0)
            if generation != self.session_generation:
                raise RuntimeError("stale relay session generation")
            raw_message = frame.get("message")
            if not isinstance(raw_message, dict):
                raise TypeError("relay forward missing signed node message")
            # End-to-end Ed25519 validation happens inside NodeGateway. The mTLS
            # peer on this hop is the relay, so the original coordinator CN is
            # intentionally not substituted or fabricated here.
            result = self.gateway.handle(raw_message, peer_certificate=None)
            _send_frame(sock, {"kind": "result", "generation": generation, "message": result})

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.last_error = None
                self._connect_once()
            except Exception as exc:
                self.last_error = exc
            finally:
                self._registered.clear()
                self._disconnected.set()
                sock, self._sock = self._sock, None
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass
            if not self.reconnect or self._stop.is_set():
                return
            self._stop.wait(self.reconnect_delay_s)

    def start(self) -> "RelayNodeAgent":
        if self._thread is None:
            self._stop.clear()
            self._thread = Thread(target=self._run, name=f"aftergraph-relay-node:{self.node_id}", daemon=True)
            self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        sock = self._sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> "RelayNodeAgent":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class RelayCoordinatorClient:
    """Coordinator side of the outbound relay seam.

    The payload remains a signed NodeMessage. The relay only routes it to the
    currently registered, generation-fenced worker session.
    """

    def __init__(
        self,
        *,
        coordinator_id: str,
        relay_host: str,
        relay_port: int,
        ca_file: str | Path,
        certificate_file: str | Path,
        private_key_file: str | Path,
        timeout_s: float = 30.0,
        server_name: str | None = None,
    ) -> None:
        if not coordinator_id.strip() or not relay_host.strip() or relay_port <= 0:
            raise ValueError("coordinator identity and relay address are required")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.coordinator_id = coordinator_id
        self.relay_host = relay_host
        self.relay_port = int(relay_port)
        self.timeout_s = float(timeout_s)
        self.server_name = server_name or relay_host
        self._tls = client_mtls_context(
            ca_file=str(ca_file), certificate_file=str(certificate_file), private_key_file=str(private_key_file),
        )

    def send(self, message: SignedNodeMessage) -> SignedNodeMessage:
        payload = message.receipt.payload
        node_id = str(payload.get("recipient") or "")
        if not node_id:
            raise RuntimeError("signed node request has no recipient")
        raw = socket.create_connection((self.relay_host, self.relay_port), timeout=self.timeout_s)
        try:
            with self._tls.wrap_socket(raw, server_hostname=self.server_name) as sock:
                sock.settimeout(self.timeout_s)
                _send_frame(sock, {"kind": "call", "node_id": node_id, "message": message.to_dict()})
                response = _recv_frame(sock)
        except Exception:
            try:
                raw.close()
            except OSError:
                pass
            raise
        if response.get("kind") == "error":
            raise RuntimeError(str(response.get("message") or response.get("error") or "relay call failed"))
        if response.get("kind") != "result" or response.get("node_id") != node_id:
            raise RuntimeError("relay result binding mismatch")
        raw_message = response.get("message")
        if not isinstance(raw_message, dict):
            raise RuntimeError("relay result missing signed node response")
        return SignedNodeMessage.from_dict(raw_message)

@dataclass(frozen=True, slots=True)
class RelayHubConfig:
    host: str
    port: int
    ca_file: Path
    certificate_file: Path
    private_key_file: Path
    allowed_node_ids: tuple[str, ...]
    allowed_coordinator_ids: tuple[str, ...]
    call_timeout_s: float = 30.0
    generation_store_file: Path | None = None

    @classmethod
    def load_json(cls, path: str | Path) -> "RelayHubConfig":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("relay hub config must be a JSON object")
        root = source.parent

        def p(name: str) -> Path:
            value = Path(str(data[name]))
            return value if value.is_absolute() else (root / value).resolve()

        cfg = cls(
            host=str(data.get("host") or "0.0.0.0"),
            port=int(data.get("port") or 9444),
            ca_file=p("ca_file"),
            certificate_file=p("certificate_file"),
            private_key_file=p("private_key_file"),
            allowed_node_ids=tuple(str(v) for v in (data.get("allowed_node_ids") or [])),
            allowed_coordinator_ids=tuple(str(v) for v in (data.get("allowed_coordinator_ids") or [])),
            call_timeout_s=float(data.get("call_timeout_s") or 30.0),
            generation_store_file=(p("generation_store_file") if data.get("generation_store_file") else None),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.host.strip() or not (1 <= self.port <= 65535):
            raise ValueError("relay host and port are required")
        for path in (self.ca_file, self.certificate_file, self.private_key_file):
            if not path.is_file():
                raise FileNotFoundError(path)
        if not self.allowed_node_ids or not self.allowed_coordinator_ids:
            raise ValueError("relay allowlists must not be empty")
        if len(set(self.allowed_node_ids)) != len(self.allowed_node_ids):
            raise ValueError("duplicate allowed node id")
        if len(set(self.allowed_coordinator_ids)) != len(self.allowed_coordinator_ids):
            raise ValueError("duplicate allowed coordinator id")
        if self.call_timeout_s <= 0:
            raise ValueError("call_timeout_s must be positive")

    def public_summary(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "allowed_node_ids": sorted(self.allowed_node_ids),
            "allowed_coordinator_ids": sorted(self.allowed_coordinator_ids),
            "call_timeout_s": self.call_timeout_s,
            "durable_session_generation": self.generation_store_file is not None,
            "mutual_tls": True,
        }


@dataclass(frozen=True, slots=True)
class RelayNodeConfig:
    node_config_file: Path
    relay_host: str
    relay_port: int
    ca_file: Path
    certificate_file: Path
    private_key_file: Path
    server_name: str | None = None
    reconnect_delay_s: float = 0.5
    connect_timeout_s: float = 10.0

    @classmethod
    def load_json(cls, path: str | Path) -> "RelayNodeConfig":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("relay node config must be a JSON object")
        root = source.parent

        def p(name: str) -> Path:
            value = Path(str(data[name]))
            return value if value.is_absolute() else (root / value).resolve()

        cfg = cls(
            node_config_file=p("node_config_file"),
            relay_host=str(data["relay_host"]),
            relay_port=int(data["relay_port"]),
            ca_file=p("ca_file"),
            certificate_file=p("certificate_file"),
            private_key_file=p("private_key_file"),
            server_name=(str(data["server_name"]) if data.get("server_name") else None),
            reconnect_delay_s=float(data.get("reconnect_delay_s") or 0.5),
            connect_timeout_s=float(data.get("connect_timeout_s") or 10.0),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not self.node_config_file.is_file():
            raise FileNotFoundError(self.node_config_file)
        if not self.relay_host.strip() or not (1 <= self.relay_port <= 65535):
            raise ValueError("relay host and port are required")
        for path in (self.ca_file, self.certificate_file, self.private_key_file):
            if not path.is_file():
                raise FileNotFoundError(path)
        if self.reconnect_delay_s < 0 or self.connect_timeout_s <= 0:
            raise ValueError("relay reconnect/connect timing invalid")


@dataclass(frozen=True, slots=True)
class RelayClientConfig:
    sender_id: str
    worker_id: str
    relay_host: str
    relay_port: int
    ca_file: Path
    certificate_file: Path
    private_key_file: Path
    signing_key_file: Path
    signing_key_id: str
    worker_public_key_b64: str
    server_name: str | None = None
    timeout_s: float = 30.0

    @classmethod
    def load_json(cls, path: str | Path) -> "RelayClientConfig":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("relay client config must be a JSON object")
        root = source.parent

        def p(name: str) -> Path:
            value = Path(str(data[name]))
            return value if value.is_absolute() else (root / value).resolve()

        cfg = cls(
            sender_id=str(data["sender_id"]),
            worker_id=str(data["worker_id"]),
            relay_host=str(data["relay_host"]),
            relay_port=int(data["relay_port"]),
            ca_file=p("ca_file"),
            certificate_file=p("certificate_file"),
            private_key_file=p("private_key_file"),
            signing_key_file=p("signing_key_file"),
            signing_key_id=str(data["signing_key_id"]),
            worker_public_key_b64=str(data["worker_public_key_b64"]),
            server_name=(str(data["server_name"]) if data.get("server_name") else None),
            timeout_s=float(data.get("timeout_s") or 30.0),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        values = (self.sender_id, self.worker_id, self.relay_host, self.signing_key_id, self.worker_public_key_b64)
        if not all(v.strip() for v in values):
            raise ValueError("relay client identity and endpoint fields are required")
        if not (1 <= self.relay_port <= 65535):
            raise ValueError("relay_port must be in 1..65535")
        for path in (self.ca_file, self.certificate_file, self.private_key_file, self.signing_key_file):
            if not path.is_file():
                raise FileNotFoundError(path)
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        try:
            base64.b64decode(self.worker_public_key_b64, validate=True)
        except Exception as exc:
            raise ValueError("worker_public_key_b64 is invalid") from exc


class RelayNodeService:
    """Deploy a bounded node runtime using only an outbound relay connection."""

    def __init__(self, config: RelayNodeConfig) -> None:
        from .node_daemon import NodeAgentConfig, build_node_gateway

        self.config = config
        self.node_config = NodeAgentConfig.load_json(config.node_config_file)
        if not self.node_config.peer_sender_key_ids:
            raise ValueError("relay node requires application sender-key bindings")
        self.gateway = build_node_gateway(self.node_config)
        self.agent = RelayNodeAgent(
            node_id=self.node_config.node_id,
            relay_host=config.relay_host,
            relay_port=config.relay_port,
            ca_file=config.ca_file,
            certificate_file=config.certificate_file,
            private_key_file=config.private_key_file,
            gateway=self.gateway,
            reconnect=True,
            reconnect_delay_s=config.reconnect_delay_s,
            connect_timeout_s=config.connect_timeout_s,
            server_name=config.server_name,
        )

    def start(self) -> "RelayNodeService":
        self.agent.start()
        return self

    def close(self) -> None:
        self.agent.close()

    @property
    def registered(self) -> bool:
        return self.agent.registered

    @property
    def last_error(self) -> Exception | None:
        return self.agent.last_error

    def __enter__(self) -> "RelayNodeService":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class RelayNodeClientSession:
    """Authenticated coordinator session for a relay-connected node."""

    def __init__(self, config: RelayClientConfig) -> None:
        from .node_transport import NodeProtocol
        from .public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier
        from .remote_worker import RemoteWorkerClient

        self.config = config
        signer = Ed25519ReceiptSigner.load_private_key(
            key_id=config.signing_key_id,
            path=config.signing_key_file,
        )
        worker_key = base64.b64decode(config.worker_public_key_b64)
        protocol = NodeProtocol(
            signer=signer,
            verifier=Ed25519ReceiptVerifier({
                config.signing_key_id: signer.public_key_bytes(),
                config.worker_id: worker_key,
            }),
        )
        transport = RelayCoordinatorClient(
            coordinator_id=config.sender_id,
            relay_host=config.relay_host,
            relay_port=config.relay_port,
            ca_file=config.ca_file,
            certificate_file=config.certificate_file,
            private_key_file=config.private_key_file,
            timeout_s=config.timeout_s,
            server_name=config.server_name,
        )
        self.client = RemoteWorkerClient(
            sender_id=config.sender_id,
            worker_id=config.worker_id,
            protocol=protocol,
            send=transport.send,
        )

    def call(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        result = self.client.call(operation, dict(payload))
        if not result.ok:
            raise RuntimeError(str(result.payload))
        return dict(result.payload)

    def describe(self) -> dict[str, Any]:
        return self.call("node_describe", {})

    def issue_lease(
        self,
        *,
        node_id: str,
        authority_grant_id: str,
        capabilities: list[str],
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        return self.call("lease_issue", {
            "node_id": node_id,
            "authority_grant_id": authority_grant_id,
            "capabilities": list(capabilities),
            "ttl_seconds": int(ttl_seconds),
        })


def generate_relay_hub_config_template() -> dict[str, Any]:
    return {
        "host": "0.0.0.0",
        "port": 9444,
        "ca_file": "secrets/ca.crt.pem",
        "certificate_file": "secrets/relay.crt.pem",
        "private_key_file": "secrets/relay.key.pem",
        "allowed_node_ids": ["worker:jonas-lenovo", "worker:vds"],
        "allowed_coordinator_ids": ["coordinator"],
        "call_timeout_s": 60,
        "generation_store_file": "state/relay-generations.db",
    }


def generate_relay_node_config_template(*, node_config_file: str = "node.json") -> dict[str, Any]:
    return {
        "node_config_file": node_config_file,
        "relay_host": "relay.aftergraph.example",
        "relay_port": 9444,
        "server_name": "relay.aftergraph.example",
        "ca_file": "secrets/ca.crt.pem",
        "certificate_file": "secrets/node-client.crt.pem",
        "private_key_file": "secrets/node-client.key.pem",
        "reconnect_delay_s": 0.5,
        "connect_timeout_s": 10,
    }


def generate_relay_client_config_template(*, sender_id: str, worker_id: str) -> dict[str, Any]:
    return {
        "sender_id": sender_id,
        "worker_id": worker_id,
        "relay_host": "relay.aftergraph.example",
        "relay_port": 9444,
        "server_name": "relay.aftergraph.example",
        "ca_file": "secrets/ca.crt.pem",
        "certificate_file": "secrets/coordinator-client.crt.pem",
        "private_key_file": "secrets/coordinator-client.key.pem",
        "signing_key_file": "secrets/coordinator.ed25519.key",
        "signing_key_id": sender_id,
        "worker_public_key_b64": "BASE64_ED25519_PUBLIC_KEY",
        "timeout_s": 30,
    }
