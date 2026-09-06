from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, urlunparse

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
    missing = [operation for operation in ("read", "search", "shell") if operation not in handlers]
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
