from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .types import ToolSpec


class ToolPolicyError(RuntimeError):
    pass


class ApprovalRequired(ToolPolicyError):
    pass


_HARD_DENY_PATTERNS = [
    re.compile(r"(^|[;&|]\s*)rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)"),
    re.compile(r"(^|\s)(mkfs|fdisk|parted)\b"),
    re.compile(r"\bdd\s+[^\n]*\bof=/dev/"),
    re.compile(r"\b(shutdown|reboot|poweroff)\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\s+-[^\n]*[fdx][^\n]*"),
    re.compile(r"\bDROP\s+(DATABASE|TABLE)\b", re.I),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"),
]

_MANDATORY_APPROVAL_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgh\s+pr\s+(?:merge|close)\b"),
    re.compile(r"\bnpm\s+publish\b"),
    re.compile(r"\bcargo\s+publish\b"),
    re.compile(r"\btwine\s+upload\b"),
    re.compile(r"\bdocker\s+push\b"),
    re.compile(r"\bkubectl\s+(?:apply|delete|replace|patch|scale)\b"),
    re.compile(r"\bhelm\s+(?:upgrade|install|uninstall)\b"),
    re.compile(r"\bterraform\s+(?:apply|destroy)\b"),
    re.compile(r"\bcurl\b[^\n]*\s-X\s*(?:POST|PUT|PATCH|DELETE)\b", re.I),
]

_VERIFY_ONLY_FORBIDDEN_SHELL = re.compile(r"(?:[;&|<>`]|\$\(|[\r\n])")

_VERIFY_PREFIXES = (
    "pytest", "python -m pytest", "python3 -m pytest", "python -m unittest", "python3 -m unittest",
    "python -m compileall", "python3 -m compileall",
    "ruff ", "python -m ruff", "mypy ", "pyright", "npm test", "npm run test", "npm run build",
    "npm run lint", "pnpm test", "pnpm run test", "pnpm run build", "pnpm run lint", "yarn test",
    "yarn build", "go test", "go vet", "cargo test", "cargo check", "cargo clippy", "dotnet test",
    "mvn test", "gradle test", "./gradlew test", "git status", "git diff", "git grep", "git ls-files",
    "git rev-parse", "ls", "find ", "grep ", "rg ",
)
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".jev", ".jev-one", "dist", "build"}


class RepoTools:
    def __init__(self, root: str | Path, *, command_mode: str = "verify_only", command_timeout: float = 120.0) -> None:
        self.root = Path(root).resolve()
        self.command_mode = command_mode
        self.command_timeout = command_timeout

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec("read_file", "Read a UTF-8 text file inside the repository.", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}),
            ToolSpec("search_text", "Search repository text files for a literal or regex pattern.", {"type": "object", "properties": {"pattern": {"type": "string"}, "regex": {"type": "boolean"}}, "required": ["pattern"], "additionalProperties": False}),
            ToolSpec("list_files", "List repository files under an optional relative directory.", {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False}),
            ToolSpec("write_file", "Write a complete UTF-8 file inside the repository.", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}),
            ToolSpec("replace_text", "Replace exact text in a workspace file.", {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}, "count": {"type": "integer"}}, "required": ["path", "old", "new"], "additionalProperties": False}),
            ToolSpec("run_command", "Run a repository-scoped command. Deterministic policy and typed safety gate apply.", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"], "additionalProperties": False}),
            ToolSpec("git_diff", "Return the current git diff when the repository is a git worktree.", {"type": "object", "properties": {}, "additionalProperties": False}),
        ]

    def _resolve(self, relative: str) -> Path:
        raw = Path(relative)
        if raw.is_absolute():
            raise ToolPolicyError(f"Absolute path is outside repository authority: {relative!r}")
        candidate = (self.root / raw).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ToolPolicyError(f"Path escapes repository root: {relative!r}") from exc
        return candidate

    def read_file(self, path: str) -> dict[str, Any]:
        p = self._resolve(path)
        if not p.is_file():
            raise FileNotFoundError(path)
        if p.stat().st_size > 2_000_000:
            raise ToolPolicyError(f"File exceeds 2 MB read ceiling: {path}")
        data = p.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": data, "bytes": len(data.encode("utf-8"))}

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": path, "bytes": len(content.encode("utf-8")), "written": True}

    def replace_text(self, path: str, old: str, new: str, count: int = 1) -> dict[str, Any]:
        p = self._resolve(path)
        text = p.read_text(encoding="utf-8")
        occurrences = text.count(old)
        if occurrences < count:
            raise ToolPolicyError(f"Expected {count} occurrence(s), found {occurrences} in {path}")
        p.write_text(text.replace(old, new, count), encoding="utf-8")
        return {"path": path, "replacements": count}

    def list_files(self, path: str = "") -> dict[str, Any]:
        base = self._resolve(path or ".")
        items: list[str] = []
        if base.is_file():
            items = [str(base.relative_to(self.root))]
        elif base.exists():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(self.root)
                    if any(part in _SKIP_DIRS for part in rel.parts):
                        continue
                    items.append(str(rel))
                    if len(items) >= 1000:
                        break
        return {"files": items}

    def search_text(self, pattern: str, regex: bool = False) -> dict[str, Any]:
        compiled = re.compile(pattern) if regex else None
        matches: list[dict[str, Any]] = []
        for rel in self.list_files()["files"]:
            p = self._resolve(rel)
            if p.stat().st_size > 1_000_000:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                hit = bool(compiled.search(line)) if compiled else pattern.casefold() in line.casefold()
                if hit:
                    matches.append({"path": rel, "line": lineno, "text": line[:500]})
                    if len(matches) >= 200:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def _command_policy(self, command: str) -> str:
        raw = command.strip()
        normalized = " ".join(raw.split())
        if not normalized:
            raise ToolPolicyError("Empty command")
        if any(pattern.search(normalized) for pattern in _HARD_DENY_PATTERNS):
            raise ToolPolicyError("Command matches deterministic hard-deny policy")
        if self.command_mode == "verify_only":
            # The verify-only mode is intentionally a *single-command* surface.
            # Shell chaining/substitution/redirection would turn an allowlisted
            # prefix into an arbitrary shell escape (e.g. `pytest; curl ...`).
            if _VERIFY_ONLY_FORBIDDEN_SHELL.search(raw):
                raise ToolPolicyError("Shell control operators are not allowed in verify_only mode")
            try:
                tokens = shlex.split(raw)
            except ValueError as exc:
                raise ToolPolicyError(f"Invalid shell quoting in verify_only command: {exc}") from exc
            for token in tokens[1:]:
                pathish = Path(token)
                if pathish.is_absolute() or ".." in pathish.parts:
                    raise ToolPolicyError(
                        f"Absolute/parent path argument is outside verify_only authority: {token!r}"
                    )
            if not normalized.startswith(_VERIFY_PREFIXES):
                raise ToolPolicyError(f"Command is outside verify_only allowlist: {normalized!r}")
        if self.command_mode not in {"verify_only", "full"}:
            raise ToolPolicyError(f"Unknown command mode {self.command_mode!r}")
        if any(pattern.search(normalized) for pattern in _MANDATORY_APPROVAL_PATTERNS):
            return "confirm"
        return "allow"

    def preflight(self, name: str, arguments: dict[str, Any]) -> str:
        """Deterministic authority gate that runs before Jev."""
        if name in {"read_file", "write_file", "replace_text"} and "path" in arguments:
            self._resolve(str(arguments["path"]))
        if name == "run_command":
            return self._command_policy(str(arguments.get("command", "")))
        return "allow"

    @staticmethod
    def _safe_subprocess_env() -> dict[str, str]:
        safe_names = {
            "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL",
            "LC_CTYPE", "TERM", "CI", "PYTHONPATH", "VIRTUAL_ENV", "SYSTEMROOT", "COMSPEC", "PATHEXT",
        }
        env = {name: value for name, value in os.environ.items() if name in safe_names}
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def run_command(self, command: str, *, safety_action: str = "allow") -> dict[str, Any]:
        deterministic = self._command_policy(command)
        if deterministic == "confirm" and safety_action != "approved":
            raise ApprovalRequired("Command requires explicit human approval")
        if safety_action not in {"allow", "approved"}:
            raise ToolPolicyError(f"Typed safety gate did not allow command: {safety_action}")
        try:
            # verify_only is deliberately shell-free. This is both safer and portable:
            # the v2.16 Windows live proof showed that routing an allowlisted verifier
            # through Git Bash can turn a valid `python -m pytest` command into exit 127.
            if self.command_mode == "verify_only":
                argv = shlex.split(command, posix=True)
            elif os.name == "nt":
                argv = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
            else:
                argv = ["bash", "-lc", command]
            completed = subprocess.run(
                argv,
                cwd=self.root,
                env=self._safe_subprocess_env(),
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
                check=False,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            return {
                "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                "exit_code": completed.returncode,
                "output": output[-50_000:],
            }
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + ((exc.stderr or "") if isinstance(exc.stderr, str) else "")
            return {
                "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                "exit_code": 124,
                "output": (output + "\ncommand timed out")[-50_000:],
            }

    def git_diff(self) -> dict[str, Any]:
        try:
            result = self.run_command("git diff --no-ext-diff --", safety_action="allow")
        except ToolPolicyError:
            return {"diff": "", "available": False}
        return {"diff": result.get("output", ""), "available": result.get("exit_code") == 0}

    def execute(self, name: str, arguments: dict[str, Any], *, safety_action: str = "allow") -> dict[str, Any]:
        if name == "read_file":
            return self.read_file(str(arguments["path"]))
        if name == "search_text":
            return self.search_text(str(arguments["pattern"]), bool(arguments.get("regex", False)))
        if name == "list_files":
            return self.list_files(str(arguments.get("path", "")))
        if name == "write_file":
            return self.write_file(str(arguments["path"]), str(arguments["content"]))
        if name == "replace_text":
            return self.replace_text(str(arguments["path"]), str(arguments["old"]), str(arguments["new"]), int(arguments.get("count", 1)))
        if name == "run_command":
            return self.run_command(str(arguments["command"]), safety_action=safety_action)
        if name == "git_diff":
            return self.git_diff()
        raise ToolPolicyError(f"Unknown tool: {name}")