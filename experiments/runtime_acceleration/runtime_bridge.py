from __future__ import annotations

from collections import deque
from ipaddress import ip_address
import json
from pathlib import Path
import queue
import subprocess
import threading
from typing import Callable
from urllib.parse import urlparse, urlunparse
import uuid

from .phase1_bindings import build_condition_adapter_factory


class RuntimeBridgeError(RuntimeError):
    """Raised when the real controlled-host runtime cannot be bound exactly."""


_REQUIRED_HERMES_SYMBOLS = (
    "tools.file_tools.read_file_tool",
    "tools.file_tools.search_tool",
    "tools.environments.local.LocalEnvironment",
    "tools.file_operations.ShellFileOperations",
)
_TOOLRUSH_FLAGS = (
    "TOOLRUSH_FASTLANE",
    "TOOLRUSH_SEARCH",
    "TOOLRUSH_PERSIST",
)
WORKER_OPERATIONS = frozenset({"read", "search", "shell", "rpc_batch"})
_PHASE1_HANDLER_OPERATIONS = ("read", "search", "shell")


def _mode(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in {"stock", "toolrush"}:
        raise RuntimeBridgeError(f"unsupported Hermes runtime mode: {value}")
    return normalized


def build_hermes_worker_argv(config: dict, mode: str) -> list[str]:
    """Build the exact argv for an isolated stock or ToolRush Hermes worker."""
    runtime_mode = _mode(mode)
    required = ("hermes_python", "hermes_root", "workspace")
    missing = [field for field in required if not config.get(field)]
    if missing:
        raise RuntimeBridgeError(f"missing worker config: {', '.join(missing)}")

    argv = [
        str(config["hermes_python"]),
        "-u",
        "-m",
        "experiments.runtime_acceleration.hermes_host_worker",
        "--hermes-root",
        str(config["hermes_root"]),
        "--workspace",
        str(config["workspace"]),
        "--mode",
        runtime_mode,
    ]
    if runtime_mode == "toolrush":
        plugin = config.get("toolrush_plugin")
        if not plugin:
            raise RuntimeBridgeError("ToolRush treatment requires toolrush_plugin")
        argv.extend(["--toolrush-plugin", str(plugin)])
    return argv


def validate_surface_report(report: dict, mode: str) -> dict:
    """Fail closed unless a worker proves the exact Hermes surfaces and lane state."""
    runtime_mode = _mode(mode)
    if not isinstance(report, dict):
        raise RuntimeBridgeError("Hermes surface report must be a mapping")
    if report.get("mode") != runtime_mode:
        raise RuntimeBridgeError(
            f"Hermes surface mode mismatch: expected {runtime_mode}, got {report.get('mode')}"
        )

    symbols = report.get("symbols")
    if not isinstance(symbols, dict):
        raise RuntimeBridgeError("Hermes surface report has no symbols mapping")
    for symbol in _REQUIRED_HERMES_SYMBOLS:
        entry = symbols.get(symbol)
        if not isinstance(entry, dict) or entry.get("status") != "READY":
            raise RuntimeBridgeError(f"required Hermes symbol is not READY: {symbol}")

    expected_flag = "1" if runtime_mode == "toolrush" else "0"
    flags = report.get("toolrush_flags")
    if not isinstance(flags, dict):
        raise RuntimeBridgeError("Hermes surface report has no ToolRush flags")
    for flag in _TOOLRUSH_FLAGS:
        actual = str(flags.get(flag, ""))
        if actual != expected_flag:
            raise RuntimeBridgeError(
                f"{flag} mismatch for {runtime_mode}: expected {expected_flag}, got {actual or '<missing>'}"
            )

    plugin_loaded = report.get("toolrush_plugin_loaded") is True
    if runtime_mode == "toolrush" and not plugin_loaded:
        raise RuntimeBridgeError("ToolRush treatment worker did not load the ToolRush plugin")
    if runtime_mode == "stock" and plugin_loaded:
        raise RuntimeBridgeError("stock worker unexpectedly loaded the ToolRush plugin")
    return dict(report)


class HermesWorkerClient:
    """Persistent JSONL client for one isolated real-Hermes runtime condition.

    Stock and ToolRush use identical IPC and live in different processes so imported
    plugin state, environment flags, warm shells, and module monkey-patches cannot
    leak across the experimental boundary. Phase-1 handlers remain restricted to
    read/search/shell; Phase-2 may explicitly invoke ``rpc_batch`` through execute().
    """

    def __init__(
        self,
        config: dict,
        mode: str,
        *,
        popen_factory=subprocess.Popen,
        id_factory: Callable[[], str] | None = None,
        startup_timeout_s: float = 30.0,
        request_timeout_s: float = 120.0,
        repo_root: str | Path | None = None,
    ):
        self.mode = _mode(mode)
        self.config = dict(config)
        self.startup_timeout_s = float(startup_timeout_s)
        self.request_timeout_s = float(request_timeout_s)
        if self.startup_timeout_s <= 0 or self.request_timeout_s <= 0:
            raise ValueError("worker timeouts must be positive")
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._lock = threading.Lock()
        self._messages: queue.Queue[object] = queue.Queue()
        self._eof = object()
        self._stderr_tail: deque[str] = deque(maxlen=64)
        self._closed = False

        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]
        self.repo_root = Path(repo_root).resolve()
        argv = build_hermes_worker_argv(self.config, self.mode)
        self.argv = tuple(argv)
        try:
            self.process = popen_factory(
                argv,
                cwd=str(self.repo_root),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                shell=False,
            )
        except Exception as exc:
            raise RuntimeBridgeError(
                f"unable to start {self.mode} Hermes worker: {type(exc).__name__}: {exc}"
            ) from exc

        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            self._abort()
            raise RuntimeBridgeError("Hermes worker was created without stdio pipes")

        self._stdout_thread = threading.Thread(
            target=self._pump_stdout,
            name=f"jar-exp-0013-{self.mode}-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._pump_stderr,
            name=f"jar-exp-0013-{self.mode}-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

        try:
            ready = self._next_message(self.startup_timeout_s)
            if ready.get("type") == "fatal":
                error = ready.get("error") or {}
                raise RuntimeBridgeError(
                    f"{self.mode} Hermes worker fatal during startup: "
                    f"{error.get('type', 'Error')}: {error.get('message', '')}"
                )
            if ready.get("type") != "ready":
                raise RuntimeBridgeError(
                    f"{self.mode} Hermes worker protocol expected ready, got {ready}"
                )
            self.surface = validate_surface_report(ready.get("surface"), self.mode)
        except Exception:
            self._abort()
            raise

    def _pump_stdout(self) -> None:
        try:
            for line in self.process.stdout:
                self._messages.put(line)
        finally:
            self._messages.put(self._eof)

    def _pump_stderr(self) -> None:
        try:
            for line in self.process.stderr:
                text = line.rstrip("\r\n")
                if text:
                    self._stderr_tail.append(text)
        except Exception as exc:
            self._stderr_tail.append(f"stderr-reader: {type(exc).__name__}: {exc}")

    def _diagnostic_suffix(self) -> str:
        if not self._stderr_tail:
            return ""
        return " | stderr: " + " || ".join(self._stderr_tail)

    def _next_message(self, timeout_s: float) -> dict:
        try:
            item = self._messages.get(timeout=float(timeout_s))
        except queue.Empty as exc:
            raise RuntimeBridgeError(
                f"timed out waiting for {self.mode} Hermes worker"
                + self._diagnostic_suffix()
            ) from exc
        if item is self._eof:
            raise RuntimeBridgeError(
                f"{self.mode} Hermes worker closed its protocol stream"
                + self._diagnostic_suffix()
            )
        try:
            message = json.loads(str(item).strip())
        except json.JSONDecodeError as exc:
            raise RuntimeBridgeError(
                f"invalid JSON from {self.mode} Hermes worker: {item!r}"
                + self._diagnostic_suffix()
            ) from exc
        if not isinstance(message, dict):
            raise RuntimeBridgeError(
                f"non-mapping protocol message from {self.mode} Hermes worker"
            )
        return message

    def _write_message(self, message: dict) -> None:
        if self.process.stdin is None:
            raise RuntimeBridgeError(f"{self.mode} Hermes worker stdin is unavailable")
        try:
            self.process.stdin.write(
                json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n"
            )
            self.process.stdin.flush()
        except Exception as exc:
            raise RuntimeBridgeError(
                f"unable to write to {self.mode} Hermes worker: {type(exc).__name__}: {exc}"
                + self._diagnostic_suffix()
            ) from exc

    def handlers(self) -> dict[str, Callable[[dict], dict]]:
        return {
            operation: (lambda payload, op=operation: self.execute(op, payload))
            for operation in _PHASE1_HANDLER_OPERATIONS
        }

    def execute(self, operation: str, payload: dict) -> dict:
        if self._closed:
            raise RuntimeBridgeError(f"{self.mode} Hermes worker client is closed")
        if operation not in WORKER_OPERATIONS:
            raise RuntimeBridgeError(f"unsupported Hermes worker operation: {operation}")
        if not isinstance(payload, dict):
            raise TypeError("Hermes worker payload must be a mapping")
        request_id = str(self._id_factory())
        if not request_id:
            raise RuntimeBridgeError("Hermes worker request id must be non-empty")

        with self._lock:
            if self.process.poll() is not None:
                raise RuntimeBridgeError(
                    f"{self.mode} Hermes worker exited before request"
                    + self._diagnostic_suffix()
                )
            self._write_message(
                {"id": request_id, "operation": operation, "payload": dict(payload)}
            )
            response = self._next_message(self.request_timeout_s)
            if response.get("type") == "fatal":
                error = response.get("error") or {}
                raise RuntimeBridgeError(
                    f"{self.mode} Hermes worker fatal: "
                    f"{error.get('type', 'Error')}: {error.get('message', '')}"
                )
            if response.get("id") != request_id:
                raise RuntimeBridgeError(
                    f"Hermes worker response id mismatch: expected {request_id}, "
                    f"got {response.get('id')}"
                )
            if response.get("ok") is not True:
                error = response.get("error")
                if not isinstance(error, dict):
                    raise RuntimeBridgeError(
                        f"{self.mode} Hermes worker failed without structured error"
                    )
                raise RuntimeBridgeError(
                    f"{error.get('type', 'Error')}: {error.get('message', '')}"
                )
            result = response.get("result")
            if not isinstance(result, dict):
                raise RuntimeBridgeError(
                    f"{self.mode} Hermes worker returned a non-mapping result"
                )
            return result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with self._lock:
            if self.process.poll() is None:
                try:
                    self._write_message({"type": "close"})
                    response = self._next_message(min(self.request_timeout_s, 2.0))
                    if response.get("type") != "closed":
                        raise RuntimeBridgeError(
                            f"{self.mode} Hermes worker protocol expected closed, got {response}"
                        )
                except RuntimeBridgeError:
                    pass
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1.0)

    def _abort(self) -> None:
        try:
            if getattr(self, "process", None) is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1.0)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _loopback_origin(base_url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(str(base_url))
    if parsed.scheme != "http" or not parsed.hostname:
        raise RuntimeBridgeError("fixture base URL must be loopback HTTP")
    host = parsed.hostname
    try:
        loopback = ip_address(host).is_loopback
    except ValueError:
        loopback = host.lower() == "localhost"
    if not loopback:
        raise RuntimeBridgeError("fixture base URL must be loopback HTTP")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise RuntimeBridgeError("fixture base URL must be an origin without path/query/fragment")
    return parsed.scheme, host, parsed.port


def resolve_fixture_url(url: str, fixture_base_url: str) -> str:
    """Resolve fixture:// URLs and reject navigation outside the local fixture origin."""
    _loopback_origin(fixture_base_url)
    base = urlparse(str(fixture_base_url))
    candidate = urlparse(str(url))

    if candidate.scheme == "fixture":
        route = candidate.netloc + candidate.path
        route = "/" + route.lstrip("/")
        return urlunparse(
            (base.scheme, base.netloc, route, "", candidate.query, candidate.fragment)
        )

    if candidate.scheme != base.scheme or candidate.netloc != base.netloc:
        raise RuntimeBridgeError("browser navigation is restricted to the loopback fixture origin")
    return str(url)


def _worker_handlers(worker) -> dict:
    factory = getattr(worker, "handlers", None)
    if not callable(factory):
        raise RuntimeBridgeError("Hermes worker does not expose handlers()")
    handlers = factory()
    if not isinstance(handlers, dict):
        raise RuntimeBridgeError("Hermes worker handlers() must return a mapping")
    missing = [operation for operation in _PHASE1_HANDLER_OPERATIONS if operation not in handlers]
    if missing:
        raise RuntimeBridgeError(f"Hermes worker is missing handlers: {', '.join(missing)}")
    return handlers


def build_runtime_adapter_factory(
    *,
    stock_worker,
    toolrush_worker,
    chromium_backend_factory: Callable[[], object],
    obscura_backend_factory: Callable[[], object],
    toolrush_revision: str,
    obscura_revision: str,
):
    """Compose real worker surfaces and fresh browser factories into frozen A/B/C/D."""
    if not callable(chromium_backend_factory) or not callable(obscura_backend_factory):
        raise RuntimeBridgeError("browser backend factories must be callable")
    return build_condition_adapter_factory(
        stock_handlers=_worker_handlers(stock_worker),
        toolrush_handlers=_worker_handlers(toolrush_worker),
        toolrush_enabled=True,
        toolrush_revision=str(toolrush_revision),
        chromium_backend=chromium_backend_factory,
        obscura_backend=obscura_backend_factory,
        obscura_revision=str(obscura_revision),
    )
