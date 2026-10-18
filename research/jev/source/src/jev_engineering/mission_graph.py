from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class NodeState(str, Enum):
    BLOCKED = "blocked"
    READY = "ready"
    SPECULATING = "speculating"
    VERIFIED = "verified"
    FAILED = "failed"
    COMMITTED = "committed"
    INVALIDATED = "invalidated"


@dataclass(slots=True)
class MissionNode:
    node_id: str
    dependencies: tuple[str, ...] = ()
    state: NodeState = NodeState.BLOCKED
    speculative_allowed: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


class MissionGraph:
    """Small dependency graph with proof-aware speculative scheduling semantics."""

    def __init__(self, nodes: Iterable[MissionNode]) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        if not self.nodes:
            raise ValueError("mission graph must contain nodes")
        for node in self.nodes.values():
            missing = [dep for dep in node.dependencies if dep not in self.nodes]
            if missing:
                raise ValueError(f"node {node.node_id} has unknown dependencies: {missing}")
        self._assert_acyclic()
        self.recompute()

    def _assert_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("mission graph contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dep in self.nodes[node_id].dependencies:
                visit(dep)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def recompute(self) -> None:
        for node in self.nodes.values():
            if node.state in {NodeState.VERIFIED, NodeState.FAILED, NodeState.COMMITTED, NodeState.INVALIDATED, NodeState.SPECULATING}:
                continue
            deps = [self.nodes[d] for d in node.dependencies]
            node.state = NodeState.READY if all(d.state in {NodeState.VERIFIED, NodeState.COMMITTED} for d in deps) else NodeState.BLOCKED

    def speculative_candidates(self) -> list[MissionNode]:
        rows: list[MissionNode] = []
        for node in self.nodes.values():
            if node.state is not NodeState.BLOCKED or not node.speculative_allowed:
                continue
            deps = [self.nodes[d] for d in node.dependencies]
            if deps and all(d.state not in {NodeState.FAILED, NodeState.INVALIDATED} for d in deps):
                rows.append(node)
        return rows

    def begin_speculation(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if node not in self.speculative_candidates():
            raise RuntimeError("node is not eligible for speculative execution")
        node.state = NodeState.SPECULATING

    def mark_verified(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if node.state not in {NodeState.READY, NodeState.SPECULATING}:
            raise RuntimeError("only ready/speculating nodes can become verified")
        if any(self.nodes[d].state not in {NodeState.VERIFIED, NodeState.COMMITTED} for d in node.dependencies):
            raise RuntimeError("cannot verify node before dependencies are verified")
        node.state = NodeState.VERIFIED
        self.recompute()

    def commit(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if node.state is not NodeState.VERIFIED:
            raise RuntimeError("only verified nodes may commit")
        node.state = NodeState.COMMITTED
        self.recompute()

    def fail(self, node_id: str) -> None:
        self.nodes[node_id].state = NodeState.FAILED
        self.invalidate_descendants(node_id)

    def invalidate_descendants(self, node_id: str) -> None:
        queue = [node_id]
        seen: set[str] = set()
        while queue:
            current = queue.pop(0)
            for child in self.nodes.values():
                if current in child.dependencies and child.node_id not in seen:
                    if child.state not in {NodeState.FAILED}:
                        child.state = NodeState.INVALIDATED
                    seen.add(child.node_id)
                    queue.append(child.node_id)
