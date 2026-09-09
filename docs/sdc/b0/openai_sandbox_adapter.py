"""Experimental OpenAI Sandbox Agents adapter for Aftergraph WorkerSandbox interface.

Evidence Class: Engineering experiment only (NOT STUDY-012 confirmatory)
SDK Version: main branch @ 2026-09-09 (commit TBD)
Issue: #59

This adapter wraps the OpenAI Agents SDK SandboxAgent primitives behind the
internal WorkerSandbox Protocol. It is EXPERIMENTAL and must not be used as
the sole canonical Aftergraph execution runtime.
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from agents.sandbox import SandboxSession, SnapshotBase
    from agents.sandbox.session import BaseSandboxClient


@runtime_checkable
class WorkerSandbox(Protocol):
    """Internal abstraction for isolated worker execution.

    Aftergraph orchestration MUST depend on this interface, NOT directly
    on unstable SDK details. All methods are async to support both local
    and remote backends uniformly.
    """

    async def create_session(self, config: SandboxConfig) -> SessionHandle: ...
    async def resume_session(self, session_id: str) -> SessionHandle: ...
    async def execute_command(
        self, session: SessionHandle, cmd: str, timeout: int = 300
    ) -> CommandResult: ...
    async def read_file(self, session: SessionHandle, path: str) -> bytes: ...
    async def write_file(
        self, session: SessionHandle, path: str, content: bytes
    ) -> None: ...
    async def snapshot(self, session: SessionHandle) -> SnapshotHandle: ...
    async def destroy(self, session: SessionHandle) -> None: ...


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for creating a new sandbox session."""

    repo_url: str
    base_sha: str
    branch: str
    task_id: str
    worker_id: str
    network_enabled: bool = False
    secrets_mount_path: str | None = None
    skills_mount_path: str | None = None
    unprivileged_user: str = "worker"


@dataclass(frozen=True)
class SessionHandle:
    """Opaque handle to an active sandbox session."""

    session_id: str
    backend: str
    created_at: float
    config: SandboxConfig


@dataclass(frozen=True)
class CommandResult:
    """Result of executing a command inside a sandbox."""

    exit_code: int
    stdout: bytes
    stderr: bytes
    duration_seconds: float
    timed_out: bool = False


@dataclass(frozen=True)
class SnapshotHandle:
    """Opaque handle to a sandbox snapshot for resume/recovery."""

    snapshot_id: str
    session_id: str
    created_at: float
    restorable: bool


class OpenAISandboxAgentAdapter:
    """Experimental adapter wrapping OpenAI Agents SDK SandboxAgent.

    This implementation maps WorkerSandbox operations to SDK primitives:
    - create_session → SandboxSession via BaseSandboxClient
    - execute_command → session shell capability
    - read/write_file → session filesystem capability
    - snapshot → SnapshotBase.persist()
    - resume_session → SnapshotBase.restore()

    LIMITATIONS (beta SDK):
    - API surface may change without notice
    - Docker backend required for full isolation
    - Network restriction depends on sandbox backend capabilities
    - Secret mounting requires careful mount-security review
    """

    def __init__(self, client: BaseSandboxClient) -> None:
        self._client = client
        self._sessions: dict[str, SandboxSession] = {}

    async def create_session(self, config: SandboxConfig) -> SessionHandle:
        """Create a new sandbox session with bounded permissions."""
        from agents.sandbox.manifest import Manifest
        from agents.sandbox.types import Permissions, User

        manifest = Manifest(
            name=f"aftergraph-worker-{config.worker_id}",
            workspace=PurePosixPath(f"/workspace/{config.task_id}"),
            user=User(name=config.unprivileged_user),
            network_enabled=config.network_enabled,
        )

        session = await self._client.create_session(manifest=manifest)
        handle = SessionHandle(
            session_id=session.id,
            backend="openai-sandbox-agents",
            created_at=asyncio.get_event_loop().time(),
            config=config,
        )
        self._sessions[handle.session_id] = session
        return handle

    async def resume_session(self, session_id: str) -> SessionHandle:
        """Resume a previously snapshotted session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
        else:
            session = await self._client.resume_session(session_id)
            self._sessions[session_id] = session

        return SessionHandle(
            session_id=session_id,
            backend="openai-sandbox-agents",
            created_at=asyncio.get_event_loop().time(),
            config=SandboxConfig(
                repo_url="", base_sha="", branch="", task_id="", worker_id=""
            ),
        )

    async def execute_command(
        self, session: SessionHandle, cmd: str, timeout: int = 300
    ) -> CommandResult:
        """Execute a shell command inside the sandbox."""
        sdk_session = self._sessions.get(session.session_id)
        if sdk_session is None:
            raise RuntimeError(f"Session {session.session_id} not found")

        import time

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                sdk_session.shell.run(cmd), timeout=timeout
            )
            duration = time.monotonic() - start
            return CommandResult(
                exit_code=result.exit_code,
                stdout=result.stdout.encode() if isinstance(result.stdout, str) else result.stdout,
                stderr=result.stderr.encode() if isinstance(result.stderr, str) else result.stderr,
                duration_seconds=duration,
                timed_out=False,
            )
        except asyncio.TimeoutError:
            duration = time.monotonic() - start
            return CommandResult(
                exit_code=-1,
                stdout=b"",
                stderr=f"Command timed out after {timeout}s".encode(),
                duration_seconds=duration,
                timed_out=True,
            )

    async def read_file(self, session: SessionHandle, path: str) -> bytes:
        """Read a file from the sandbox filesystem."""
        sdk_session = self._sessions.get(session.session_id)
        if sdk_session is None:
            raise RuntimeError(f"Session {session.session_id} not found")

        content = await sdk_session.files.read(PurePosixPath(path))
        return content if isinstance(content, bytes) else content.encode()

    async def write_file(
        self, session: SessionHandle, path: str, content: bytes
    ) -> None:
        """Write a file to the sandbox filesystem."""
        sdk_session = self._sessions.get(session.session_id)
        if sdk_session is None:
            raise RuntimeError(f"Session {session.session_id} not found")

        await sdk_session.files.write(
            PurePosixPath(path),
            content if isinstance(content, bytes) else content.encode(),
        )

    async def snapshot(self, session: SessionHandle) -> SnapshotHandle:
        """Create a restorable snapshot of the current session state."""
        sdk_session = self._sessions.get(session.session_id)
        if sdk_session is None:
            raise RuntimeError(f"Session {session.session_id} not found")

        from agents.sandbox.snapshot import LocalSnapshot

        snapshot_path = Path(f"/tmp/aftergraph-snapshots/{session.session_id}")
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        snapshot = LocalSnapshot(base_path=snapshot_path)
        buf = io.BytesIO()
        await snapshot.persist(buf)

        return SnapshotHandle(
            snapshot_id=str(snapshot_path),
            session_id=session.session_id,
            created_at=asyncio.get_event_loop().time(),
            restorable=await snapshot.restorable(),
        )

    async def destroy(self, session: SessionHandle) -> None:
        """Tear down a sandbox session and release resources."""
        sdk_session = self._sessions.pop(session.session_id, None)
        if sdk_session is not None:
            await sdk_session.close()
