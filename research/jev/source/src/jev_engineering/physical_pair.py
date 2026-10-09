from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PhysicalNodeSpec:
    node_id: str
    trust_domain: str
    relay_node_config: Path
    relay_client_config: Path

    def validate(self) -> None:
        if not self.node_id.strip() or not self.trust_domain.strip():
            raise ValueError("node_id and trust_domain are required")
        if not self.node_id.startswith("worker:"):
            raise ValueError("physical node_id must use worker: namespace")
        for path in (self.relay_node_config, self.relay_client_config):
            if not path.is_file():
                raise FileNotFoundError(path)


@dataclass(frozen=True, slots=True)
class PhysicalPairManifest:
    relay_hub_config: Path
    nodes: tuple[PhysicalNodeSpec, PhysicalNodeSpec]

    @classmethod
    def load_json(cls, path: str | Path) -> "PhysicalPairManifest":
        source = Path(path).resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("physical pair manifest must be a JSON object")
        root = source.parent

        def resolve(value: Any) -> Path:
            p = Path(str(value))
            return p if p.is_absolute() else (root / p).resolve()

        raw_nodes = data.get("nodes")
        if not isinstance(raw_nodes, list) or len(raw_nodes) != 2:
            raise ValueError("physical pair manifest requires exactly two nodes")
        nodes = tuple(
            PhysicalNodeSpec(
                node_id=str(item["node_id"]),
                trust_domain=str(item["trust_domain"]),
                relay_node_config=resolve(item["relay_node_config"]),
                relay_client_config=resolve(item["relay_client_config"]),
            )
            for item in raw_nodes
        )
        manifest = cls(relay_hub_config=resolve(data["relay_hub_config"]), nodes=nodes)  # type: ignore[arg-type]
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.relay_hub_config.is_file():
            raise FileNotFoundError(self.relay_hub_config)
        for node in self.nodes:
            node.validate()
        if self.nodes[0].node_id == self.nodes[1].node_id:
            raise ValueError("physical pair nodes must have distinct worker identities")
        if self.nodes[0].trust_domain == self.nodes[1].trust_domain:
            raise ValueError("physical pair requires distinct verifier trust domains")

    def doctor(self) -> dict[str, Any]:
        from .relay_fabric import RelayClientConfig, RelayHubConfig, RelayNodeConfig

        hub = RelayHubConfig.load_json(self.relay_hub_config)
        rows: list[dict[str, Any]] = []
        for node in self.nodes:
            node_cfg = RelayNodeConfig.load_json(node.relay_node_config)
            client_cfg = RelayClientConfig.load_json(node.relay_client_config)
            from .node_daemon import NodeAgentConfig

            daemon_cfg = NodeAgentConfig.load_json(node_cfg.node_config_file)
            if daemon_cfg.node_id != node.node_id:
                raise RuntimeError("physical pair node_id does not match node-agent config")
            if client_cfg.worker_id != node.node_id:
                raise RuntimeError("physical pair node_id does not match coordinator client config")
            if node.node_id not in hub.allowed_node_ids:
                raise RuntimeError("physical pair node is not allowlisted by relay hub")
            if (node_cfg.relay_host, node_cfg.relay_port) != (client_cfg.relay_host, client_cfg.relay_port):
                raise RuntimeError("node and coordinator configs disagree on relay endpoint")
            rows.append({
                "node_id": node.node_id,
                "trust_domain": node.trust_domain,
                "relay_host": node_cfg.relay_host,
                "relay_port": node_cfg.relay_port,
                "outbound_only": True,
                "arbitrary_shell": False,
            })
        return {
            "status": "READY",
            "nodes": rows,
            "distinct_worker_identities": True,
            "distinct_trust_domains": True,
            "relay_nodes_allowlisted": True,
            "truth_boundary": "configuration readiness only; does not prove physical network reachability",
        }


def generate_physical_pair_template() -> dict[str, Any]:
    return {
        "version": 1,
        "relay_hub_config": "relay-hub.json",
        "nodes": [
            {
                "node_id": "worker:jonas-lenovo",
                "trust_domain": "aftergraph.local/lenovo",
                "relay_node_config": "jonas-lenovo/relay-node.json",
                "relay_client_config": "jonas-lenovo/relay-client.json",
            },
            {
                "node_id": "worker:vds",
                "trust_domain": "aftergraph.local/vds",
                "relay_node_config": "vds/relay-node.json",
                "relay_client_config": "vds/relay-client.json",
            },
        ],
    }
