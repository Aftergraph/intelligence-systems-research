from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .durable_state import SqliteLeaseStore
from .node_gateway import NodeCallContext, OperationRegistry


@dataclass(slots=True)
class LeaseControlService:
    leases: SqliteLeaseStore
    authorized_issuers: frozenset[str] = frozenset()
    allowed_capabilities: frozenset[str] = frozenset({"verify_candidate", "journal_poll", "lease_heartbeat", "lease_renew"})
    max_issue_ttl_s: int = 3600

    def issue(self, context: NodeCallContext) -> Mapping[str, Any]:
        if context.request.sender not in self.authorized_issuers:
            raise RuntimeError("lease issuer is not authorized")
        payload = context.request.payload
        node_id = str(payload.get("node_id") or "")
        authority_grant_id = str(payload.get("authority_grant_id") or "")
        ttl_s = int(payload.get("ttl_seconds") or 0)
        raw_capabilities = payload.get("capabilities") or []
        if not node_id or not authority_grant_id:
            raise ValueError("node_id and authority_grant_id are required")
        if ttl_s <= 0 or ttl_s > self.max_issue_ttl_s:
            raise ValueError(f"ttl_seconds must be in 1..{self.max_issue_ttl_s}")
        if not isinstance(raw_capabilities, list) or not raw_capabilities:
            raise ValueError("capabilities must be a non-empty list")
        capabilities = frozenset(str(v) for v in raw_capabilities if str(v).strip())
        if not capabilities or not capabilities.issubset(self.allowed_capabilities):
            raise RuntimeError("requested lease capabilities exceed node policy")
        now = datetime.now(timezone.utc)
        lease = self.leases.issue(
            node_id=node_id, worker_id=context.request.sender, authority_grant_id=authority_grant_id,
            capabilities=capabilities, ttl=timedelta(seconds=ttl_s), now=now,
        )
        return {
            "lease_id": lease.lease_id,
            "node_id": lease.node_id,
            "worker_id": lease.worker_id,
            "authority_grant_id": lease.authority_grant_id,
            "capabilities": sorted(lease.capabilities),
            "fencing_token": lease.fencing_token,
            "issued_at": lease.issued_at.isoformat(),
            "expires_at": lease.expires_at.isoformat(),
        }

    def heartbeat(self, context: NodeCallContext) -> Mapping[str, Any]:
        payload = context.request.payload
        lease_id = str(payload.get("lease_id") or "")
        token = int(payload.get("fencing_token") or 0)
        lease = self.leases.validate(lease_id, fencing_token=token, now=datetime.now(timezone.utc))
        if lease.worker_id != context.request.sender:
            raise RuntimeError("lease heartbeat sender mismatch")
        now = datetime.now(timezone.utc)
        self.leases.heartbeat(lease_id, fencing_token=token, now=now)
        current = self.leases.get(lease_id)
        return {
            "lease_id": lease_id,
            "fencing_token": token,
            "heartbeat_at": current.heartbeat_at.isoformat(),
            "expires_at": current.expires_at.isoformat(),
        }

    def renew(self, context: NodeCallContext) -> Mapping[str, Any]:
        payload = context.request.payload
        lease_id = str(payload.get("lease_id") or "")
        token = int(payload.get("fencing_token") or 0)
        ttl_s = int(payload.get("ttl_seconds") or 0)
        if ttl_s <= 0 or ttl_s > 3600:
            raise ValueError("ttl_seconds must be in 1..3600")
        now = datetime.now(timezone.utc)
        lease = self.leases.validate(lease_id, fencing_token=token, now=now)
        if lease.worker_id != context.request.sender:
            raise RuntimeError("lease renewal sender mismatch")
        updated = self.leases.renew(lease_id, fencing_token=token, ttl=timedelta(seconds=ttl_s), now=now)
        return {
            "lease_id": lease_id,
            "fencing_token": token,
            "expires_at": updated.expires_at.isoformat(),
        }

    def register(self, operations: OperationRegistry) -> None:
        if self.authorized_issuers:
            operations.register("lease_issue", self.issue)
        operations.register("lease_heartbeat", self.heartbeat)
        operations.register("lease_renew", self.renew)


@dataclass(slots=True)
class PreconfiguredVerifierCapability:
    """Server-owned verifier command exposed as one bounded remote capability.

    The client cannot choose or mutate the command. The candidate must match the
    exact current workspace tree hash before the verifier is executed.
    """

    workspace: object
    command: tuple[str, ...]
    verifier_name: str
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        from pathlib import Path
        root = Path(self.workspace).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("verifier workspace must exist")
        self.workspace = root
        if not self.command or not all(str(v).strip() for v in self.command):
            raise ValueError("verifier command must be a non-empty fixed argv")
        if not self.verifier_name.strip() or self.timeout_s <= 0:
            raise ValueError("verifier_name and positive timeout are required")

    def handle(self, context: NodeCallContext) -> Mapping[str, Any]:
        import hashlib
        import subprocess
        from .execution_journal import ExecutionJournal
        from .proof_graph import workspace_tree_hash
        from .remote_execution import RemoteWorkOrder

        if context.request.operation != "verify_candidate":
            raise RuntimeError("unsupported verifier operation")
        payload = context.request.payload
        order = RemoteWorkOrder(**{k: payload[k] for k in (
            "mission_id", "node_id", "execution_context_id", "lease_id",
            "fencing_token", "authority_grant_id", "candidate_sha", "operation",
        )})
        observed_sha = "sha256:" + workspace_tree_hash(self.workspace)
        if order.candidate_sha != observed_sha:
            raise RuntimeError("candidate SHA does not match verifier workspace")

        journal = ExecutionJournal()
        journal.append("verification.started", {
            "candidate_sha": observed_sha,
            "verifier": self.verifier_name,
        })
        run = subprocess.run(
            list(self.command), cwd=self.workspace, capture_output=True, text=True,
            timeout=self.timeout_s, check=False,
        )
        output = (run.stdout or "") + (run.stderr or "")
        output_hash = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()
        verdict = "PASS" if run.returncode == 0 else "FAIL"
        journal.append("verification.completed", {
            "verdict": verdict,
            "exit_code": run.returncode,
            "output_sha256": output_hash,
        })
        return {
            "work_order_sha256": order.work_order_sha256,
            "node_id": order.node_id,
            "lease_id": order.lease_id,
            "fencing_token": order.fencing_token,
            "candidate_sha": order.candidate_sha,
            "verdict": verdict,
            "evidence": {
                "verifier": self.verifier_name,
                "mode": "preconfigured-subprocess",
                "exit_code": run.returncode,
                "output_sha256": output_hash,
                "output_tail": output[-2000:],
                "execution_events": journal.to_list(),
                "execution_journal_head_sha256": journal.head_sha256,
            },
        }

    def register(self, operations: OperationRegistry) -> None:
        operations.register("verify_candidate", self.handle)

@dataclass(slots=True)
class FencedPreconfiguredVerifierCapability:
    """v2.1 verifier capability that requires a live durable lease before execution.

    The remote caller still cannot choose the command. An optional journal stream
    registry exposes progress via the bounded ``journal_poll`` operation.
    """

    workspace: object
    command: tuple[str, ...]
    verifier_name: str
    leases: SqliteLeaseStore
    timeout_s: float = 30.0
    journal_streams: object | None = None

    def __post_init__(self) -> None:
        from pathlib import Path
        root = Path(self.workspace).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("verifier workspace must exist")
        self.workspace = root
        if not self.command or not all(str(v).strip() for v in self.command):
            raise ValueError("verifier command must be a non-empty fixed argv")
        if not self.verifier_name.strip() or self.timeout_s <= 0:
            raise ValueError("verifier_name and positive timeout are required")

    def handle(self, context: NodeCallContext) -> Mapping[str, Any]:
        import hashlib
        import subprocess
        from .execution_journal import ExecutionJournal
        from .proof_graph import workspace_tree_hash
        from .remote_execution import RemoteWorkOrder

        if context.request.operation != "verify_candidate":
            raise RuntimeError("unsupported verifier operation")
        payload = context.request.payload
        order = RemoteWorkOrder(**{k: payload[k] for k in (
            "mission_id", "node_id", "execution_context_id", "lease_id",
            "fencing_token", "authority_grant_id", "candidate_sha", "operation",
        )})
        now = datetime.now(timezone.utc)
        lease = self.leases.validate(order.lease_id, fencing_token=order.fencing_token, now=now)
        if lease.node_id != order.node_id:
            raise RuntimeError("work order node does not match fenced lease")
        if lease.authority_grant_id != order.authority_grant_id:
            raise RuntimeError("work order authority grant does not match fenced lease")
        if lease.worker_id != context.request.sender:
            raise RuntimeError("work order sender does not own fenced lease")
        if "verify_candidate" not in lease.capabilities:
            raise RuntimeError("fenced lease does not grant verify_candidate capability")

        observed_sha = "sha256:" + workspace_tree_hash(self.workspace)
        if order.candidate_sha != observed_sha:
            raise RuntimeError("candidate SHA does not match verifier workspace")

        stream_id = f"{order.mission_id}:{order.node_id}:{order.lease_id}"
        journal = ExecutionJournal()
        started = {"candidate_sha": observed_sha, "verifier": self.verifier_name, "stream_id": stream_id}
        started_event = journal.append("verification.started", started)
        if self.journal_streams is not None:
            self.journal_streams.append_existing(stream_id, started_event)
        run = subprocess.run(
            list(self.command), cwd=self.workspace, capture_output=True, text=True,
            timeout=self.timeout_s, check=False,
        )
        output = (run.stdout or "") + (run.stderr or "")
        output_hash = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()
        verdict = "PASS" if run.returncode == 0 else "FAIL"
        completed = {"verdict": verdict, "exit_code": run.returncode, "output_sha256": output_hash}
        completed_event = journal.append("verification.completed", completed)
        if self.journal_streams is not None:
            self.journal_streams.append_existing(stream_id, completed_event)
            self.journal_streams.complete(stream_id)
        return {
            "work_order_sha256": order.work_order_sha256,
            "node_id": order.node_id,
            "lease_id": order.lease_id,
            "fencing_token": order.fencing_token,
            "candidate_sha": order.candidate_sha,
            "verdict": verdict,
            "evidence": {
                "verifier": self.verifier_name,
                "mode": "fenced-preconfigured-subprocess",
                "stream_id": stream_id,
                "exit_code": run.returncode,
                "output_sha256": output_hash,
                "output_tail": output[-2000:],
                "execution_events": journal.to_list(),
                "execution_journal_head_sha256": journal.head_sha256,
            },
        }

    def register(self, operations: OperationRegistry) -> None:
        operations.register("verify_candidate", self.handle)
