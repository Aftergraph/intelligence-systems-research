"""SDC-B0 Spike: OpenAI Sandbox Agents adapter behind canonical WorkerSandbox ABC.

Evidence Class: Engineering experiment only (NOT STUDY-012 confirmatory).
SDK Pin: openai-agents==0.22.2 (installed; openai==3.11.0 transitive)
Issue: #59
Branch: spike/sandbox-agents-eval

This adapter subclasses the canonical sync WorkerSandbox ABC from
src/sdc_b0/worker_sandbox.py and bridges it to the async OpenAI Agents SDK
SandboxAgent primitives via asyncio.run().

IMPORTANT: The OpenAI Agents SDK SandboxAgents surface is beta/experimental.
This adapter is a spike artifact — it is NOT the canonical B0 runtime.
"""
from __future__ import annotations

import asyncio
import io
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.sdc_b0.worker_sandbox import SandboxResult, WorkerSandbox

# ---------------------------------------------------------------------------
# SDK version pin (recorded at spike time)
# ---------------------------------------------------------------------------
SDK_PKG = "openai-agents"
SDK_VERSION = "0.22.2"
SDK_TRANSITIVE_OPENAI = "3.11.0"
SDKUNAVAILABLE = False  # set True if SDK cannot be imported

try:
    from agents.sandbox.manifest import Manifest
    from agents.sandbox.session import BaseSandboxClient
    from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient
    from agents.sandbox.snapshot import LocalSnapshot
    from agents.sandbox.types import User
except ImportError as exc:
    SDKUNAVAILABLE = True
    Manifest = None  # type: ignore[assignment]
    BaseSandboxClient = None  # type: ignore[assignment]
    UnixLocalSandboxClient = None  # type: ignore[assignment]
    LocalSnapshot = None  # type: ignore[assignment]
    User = None  # type: ignore[assignment]
    _SDK_IMPORT_ERROR = exc


# ---------------------------------------------------------------------------
# OpenAI adapter — subclasses canonical ABC
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OpenAIAdapterConfig:
    """Configuration for the OpenAI Sandbox Agents adapter.

    Mirrors the spike doc's SandboxConfig intent but is leaner — only fields
    the adapter actually consumes are kept. Network, secrets, skills, and
    unprivileged user are passed through to the SDK Manifest.
    """

    repo_url: str
    base_sha: str
    branch: str
    task_id: str
    worker_id: str
    network_enabled: bool = False
    unprivileged_user: str = "worker"


class OpenAISandboxAdapter(WorkerSandbox):
    """Experimental adapter: OpenAI Agents SDK SandboxAgents behind WorkerSandbox ABC.

    Bridges the sync canonical ABC to the async SDK using asyncio.run() per
    call. Each ABC method becomes one or more SDK calls wrapped in a fresh
    event loop.

    State tracked locally (not persisted to SDK snapshots):
    - _sessions: task_id → (session_id, sdk_session)
    - _workspace_paths: task_id → Path (synthetic workspace path from manifest)

    Limitations surfaced in the spike report:
    - create() returns a synthetic Path; the real workspace lives inside the
      SDK sandbox container, not on the host filesystem.
    - SandboxResult.worktree_path is populated with that synthetic path.
    - Teardown calls session.aclose() (persist+shutdown) but does NOT delete
      any backend container — that requires the client's delete() which is
      backend-specific.
    - Snapshot/resume is NOT exposed through the ABC (the ABC has no snapshot
      method); the spike doc's resume/snapshot questions are answered in the
      report as "not available through this ABC surface".
    """

    def __init__(self, client: BaseSandboxClient, config: OpenAIAdapterConfig | None = None) -> None:
        if SDKUNAVAILABLE:
            raise RuntimeError(
                f"{SDK_PKG}=={SDK_VERSION} import failed: {_SDK_IMPORT_ERROR}"
            ) from _SDK_IMPORT_ERROR
        self._client = client
        self._config = config or OpenAIAdapterConfig(
            repo_url="", base_sha="", branch="", task_id="", worker_id=""
        )
        self._sessions: dict[str, tuple[str, Any]] = {}  # task_id → (session_id, sdk_session)
        self._workspace_paths: dict[str, Path] = {}

    # ------------------------------------------------------------------
    # WorkerSandbox ABC implementation
    # ------------------------------------------------------------------

    def create(self, task_id: str, base_sha: str) -> Path:
        """Create a sandbox session via the SDK and return the workspace root path.

        The SDK Manifest uses ``root`` (str), ``users``, and
        ``network_enabled``. The UnixLocalSandboxClient creates an isolated
        temp directory as the workspace root. We return that path so callers
        can use it as a handle (though real file ops happen inside the session).

        The base_sha is accepted by the ABC signature but the SDK sandbox is
        not a git repo — base_sha is recorded in env for test purposes.
        """
        if task_id in self._sessions:
            raise ValueError(f"Task '{task_id}' already has an active sandbox")

        cfg = self._config
        manifest = Manifest(
            users=[User(name=cfg.unprivileged_user)],
            network_enabled=cfg.network_enabled,
        )

        loop = asyncio.new_event_loop()
        try:
            sdk_session = loop.run_until_complete(
                self._client.create(manifest=manifest)
            )
        finally:
            loop.close()

        session_id = str(getattr(sdk_session.state, "session_id", f"sdk-session-{task_id}"))
        self._sessions[task_id] = (session_id, sdk_session)
        ws_path = Path(getattr(sdk_session.state, "manifest", None) and getattr(sdk_session.state.manifest, "root", f"/workspace/{task_id}") or f"/workspace/{task_id}")
        self._workspace_paths[task_id] = ws_path

        # Record git SHAs in env for test compatibility (SDK sandbox is not a git repo)
        os.environ[f"SDC_SANDBOX_BASE_SHA_{task_id}"] = base_sha
        os.environ[f"SDC_SANDBOX_HEAD_SHA_{task_id}"] = session_id[:8]

        return ws_path

    def execute(
        self,
        task_id: str,
        command: str,
        *,
        timeout_seconds: float = 300.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute a shell command inside the SDK sandbox session.

        Bridges the sync ABC to the async SDK.exec() via asyncio.run().
        """
        if task_id not in self._sessions:
            raise KeyError(f"No active sandbox for task '{task_id}'")

        _session_id, sdk_session = self._sessions[task_id]
        start = time.monotonic()
        try:
            exec_result = asyncio.run(
                sdk_session.exec(
                    command,
                    shell=True,
                    timeout=timeout_seconds,
                )
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_ms=duration_ms,
                worktree_path=self._workspace_paths.get(task_id, Path("")),
                base_sha="",
                head_sha="",
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        # exec_result.stdout/stderr are bytes in SDK 0.22.2
        stdout = exec_result.stdout if isinstance(exec_result.stdout, str) else (
            exec_result.stdout.decode("utf-8", errors="replace") if isinstance(exec_result.stdout, bytes) else ""
        )
        stderr = exec_result.stderr if isinstance(exec_result.stderr, str) else (
            exec_result.stderr.decode("utf-8", errors="replace") if isinstance(exec_result.stderr, bytes) else ""
        )

        # Derive base_sha/head_sha from env recorded at create() time — SDK sandbox is not a git repo
        base_sha = os.environ.get(f"SDC_SANDBOX_BASE_SHA_{task_id}", "")
        head_sha = os.environ.get(f"SDC_SANDBOX_HEAD_SHA_{task_id}", "")

        return SandboxResult(
            exit_code=exec_result.exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            worktree_path=self._workspace_paths.get(task_id, Path("")),
            base_sha=base_sha,
            head_sha=head_sha,
        )

    def teardown(self, task_id: str) -> None:
        """Close the SDK session (persist + shutdown). Idempotent."""
        entry = self._sessions.pop(task_id, None)
        self._workspace_paths.pop(task_id, None)
        if entry is None:
            return
        _session_id, sdk_session = entry
        try:
            asyncio.run(sdk_session.aclose())
        except Exception:
            pass  # teardown is best-effort

    def list_active(self) -> list[str]:
        """Return task_ids with live SDK sessions."""
        return list(self._sessions.keys())
