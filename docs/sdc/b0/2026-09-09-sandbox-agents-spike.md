# OpenAI Sandbox Agents Execution-Backend Spike

**Status:** IN PROGRESS
**Date:** 2026-09-09
**Parent Track:** #54
**Issue:** #59
**Evidence Class:** Engineering experiment only (NOT STUDY-012 confirmatory)

## Objective

Evaluate whether OpenAI Agents SDK Sandbox Agents can provide a better worker-isolation primitive for Aftergraph/Hermes workers. This is an EXPERIMENTAL adapter behind an internal interface.

## Internal Interface: WorkerSandbox

Aftergraph orchestration MUST depend on this interface, NOT directly on unstable SDK details.

```python
class WorkerSandbox(Protocol):
    """Internal abstraction for isolated worker execution."""
    
    async def create_session(self, config: SandboxConfig) -> SessionHandle: ...
    async def resume_session(self, session_id: str) -> SessionHandle: ...
    async def execute_command(self, session: SessionHandle, cmd: str, timeout: int) -> CommandResult: ...
    async def read_file(self, session: SessionHandle, path: str) -> bytes: ...
    async def write_file(self, session: SessionHandle, path: str, content: bytes) -> None: ...
    async def snapshot(self, session: SessionHandle) -> SnapshotHandle: ...
    async def destroy(self, session: SessionHandle) -> None: ...
```

## Candidate Implementations

1. **HermesWorktreeSandbox** — baseline using git worktrees + unprivileged user (B0 canonical)
2. **OpenAISandboxAgentAdapter** — experimental adapter wrapping OpenAI SDK
3. **DockerWorkerSandbox** — Docker-based isolation (if safely available)

## Evaluation Criteria

- [ ] Can each worker receive only its intended repository/task material?
- [ ] Can shell/filesystem permissions be bounded?
- [ ] Can we run under an unprivileged sandbox user?
- [ ] Can a later run safely resume an earlier sandbox session?
- [ ] Can snapshots provide deterministic worker restart/recovery?
- [ ] Can Hermes capture all commands/tool events externally?
- [ ] Can skills be mounted/lazily supplied without exposing unrelated host state?
- [ ] Can network access be absent/restricted by default?
- [ ] Can secrets stay outside model-visible workspace?
- [ ] Can Sandbox Agents be swapped out without changing Aftergraph's higher-level task contract?

## Pinned SDK Version

TBD — will record exact commit/tag after prototype.

## Findings

(to be filled as spike progresses)
