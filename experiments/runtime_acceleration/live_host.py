from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Mapping, Sequence


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_SECRET_MARKERS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "PRIVATE_KEY",
    "AUTHORIZATION",
    "ACCESS_KEY",
    "SESSION_KEY",
)


class HostBridgeError(RuntimeError):
    """Base error for controlled-host bridge failures."""


class RevisionMismatch(HostBridgeError):
    """Raised when a configured treatment revision drifts from the frozen pin."""


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float


def sanitize_environment(env: Mapping[str, str]) -> dict[str, str]:
    """Return a diagnostics-safe environment snapshot with secret-like values redacted."""
    sanitized: dict[str, str] = {}
    for key, value in env.items():
        upper = key.upper()
        sanitized[str(key)] = (
            "<redacted>" if any(marker in upper for marker in _SECRET_MARKERS) else str(value)
        )
    return sanitized


def run_argv(
    argv: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 60.0,
) -> CommandResult:
    """Execute one explicit argv vector without a shell and record monotonic wall time."""
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence):
        raise TypeError("argv must be a sequence of strings, not a shell command string")
    normalized = tuple(str(part) for part in argv)
    if not normalized or not normalized[0]:
        raise ValueError("argv must contain an executable")

    effective_env = None
    if env is not None:
        effective_env = dict(os.environ)
        effective_env.update({str(key): str(value) for key, value in env.items()})

    started = perf_counter_ns()
    completed = subprocess.run(
        list(normalized),
        cwd=str(cwd) if cwd is not None else None,
        env=effective_env,
        capture_output=True,
        text=True,
        timeout=float(timeout_s),
        check=False,
        shell=False,
    )
    duration_ms = (perf_counter_ns() - started) / 1_000_000
    return CommandResult(
        argv=normalized,
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=duration_ms,
    )


def git_head(path: str | os.PathLike[str]) -> str:
    """Return the exact HEAD of a local git checkout or fail closed."""
    result = run_argv(["git", "rev-parse", "HEAD"], cwd=path, timeout_s=20)
    head = result.stdout.strip().lower()
    if result.returncode != 0 or not _HEX40.fullmatch(head):
        detail = result.stderr.strip() or result.stdout.strip() or "invalid git HEAD"
        raise HostBridgeError(f"unable to resolve git HEAD for {Path(path)}: {detail}")
    return head


def require_revision(path: str | os.PathLike[str], expected: str, label: str) -> str:
    """Require a checkout to match an exact preregistered 40-hex revision."""
    expected_normalized = str(expected).strip().lower()
    if not _HEX40.fullmatch(expected_normalized):
        raise ValueError(f"invalid expected revision for {label}: {expected!r}")
    actual = git_head(path)
    if actual != expected_normalized:
        raise RevisionMismatch(
            f"{label} revision mismatch: expected {expected_normalized}, got {actual}"
        )
    return actual


def build_obscura_serve_argv(
    executable: str | os.PathLike[str], *, port: int = 9222
) -> list[str]:
    """Build the loopback-only Obscura CDP server command used by the host bridge."""
    port_number = int(port)
    if not 1 <= port_number <= 65535:
        raise ValueError("port must be between 1 and 65535")
    return [
        str(executable).replace("\\", "/"),
        "serve",
        "--port",
        str(port_number),
        "--host",
        "127.0.0.1",
    ]
