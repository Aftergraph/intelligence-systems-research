from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import traceback
import uuid


_TOOLRUSH_FLAGS = (
    "TOOLRUSH_FASTLANE",
    "TOOLRUSH_SEARCH",
    "TOOLRUSH_PERSIST",
)


def runtime_flags(mode: str) -> dict[str, str]:
    normalized = str(mode).strip().lower()
    if normalized == "stock":
        value = "0"
    elif normalized == "toolrush":
        value = "1"
    else:
        raise ValueError(f"unsupported runtime mode: {mode}")
    return {name: value for name in _TOOLRUSH_FLAGS}


def resolve_workspace_path(workspace: str | os.PathLike[str], value: str | os.PathLike[str]) -> Path:
    """Resolve a benchmark path while refusing access outside the isolated workspace."""
    root = Path(workspace).resolve()
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes controlled workspace: {value}") from exc
    return resolved


def read_kwargs(payload: dict, workspace: str | os.PathLike[str], *, task_id: str) -> dict:
    path = payload.get("path")
    if not path:
        raise ValueError("read operation requires path")
    start_line = int(payload.get("start_line", payload.get("offset", 1)))
    if start_line < 1:
        raise ValueError("read start line must be >= 1")
    end_value = payload.get("end_line")
    if end_value is not None:
        end_line = int(end_value)
        if end_line < start_line:
            raise ValueError("read end line must be >= start line")
        limit = end_line - start_line + 1
    else:
        limit = int(payload.get("limit", 2000))
        if limit < 1:
            raise ValueError("read line limit must be >= 1")
    return {
        "path": str(resolve_workspace_path(workspace, path)),
        "offset": start_line,
        "limit": limit,
        "task_id": str(task_id),
    }


def search_kwargs(payload: dict, workspace: str | os.PathLike[str], *, task_id: str) -> dict:
    pattern = payload.get("query", payload.get("pattern"))
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("search operation requires a non-empty query")
    path = resolve_workspace_path(workspace, payload.get("path", "."))
    kwargs: dict[str, object] = {
        "pattern": pattern,
        "path": str(path),
        "task_id": str(task_id),
    }
    for key in ("target", "file_glob", "context", "limit"):
        if key in payload:
            kwargs[key] = payload[key]
    return kwargs


def decode_tool_envelope(raw: str) -> dict:
    if not isinstance(raw, str):
        raise TypeError("Hermes tool result must be JSON text")
    text = raw.lstrip()
    value, end = json.JSONDecoder().raw_decode(text)
    if text[end:].strip():
        raise ValueError("Hermes tool result contains trailing non-JSON data")
    if not isinstance(value, dict):
        raise TypeError("Hermes tool result must decode to a mapping")
    return value


def dispatch_operation(
    operation: str,
    payload: dict,
    *,
    workspace: str | os.PathLike[str],
    file_tools,
    environment,
    task_id: str,
) -> dict:
    """Dispatch one benchmark operation through the installed Hermes surfaces."""
    if not isinstance(payload, dict):
        raise TypeError("operation payload must be a mapping")
    if operation == "read":
        result = decode_tool_envelope(
            file_tools.read_file_tool(**read_kwargs(payload, workspace, task_id=task_id))
        )
    elif operation == "search":
        result = decode_tool_envelope(
            file_tools.search_tool(**search_kwargs(payload, workspace, task_id=task_id))
        )
    elif operation == "shell":
        command = payload.get("command")
        if not isinstance(command, str) or not command:
            raise ValueError("shell operation requires a non-empty command")
        raw = environment.execute(
            command,
            cwd=str(Path(workspace).resolve()),
            bounded_capture=False,
        )
        if not isinstance(raw, dict):
            raise TypeError("Hermes shell result must be a mapping")
        result = {
            "output": str(raw.get("output", "")),
            "returncode": raw.get("returncode"),
        }
    else:
        raise ValueError(f"unsupported worker operation: {operation}")

    if "error" in result:
        raise RuntimeError(f"Hermes {operation} error: {result['error']}")
    return result


def _sha256_file(path: str | os.PathLike[str] | None) -> str | None:
    if not path:
        return None
    source = Path(path)
    if not source.is_file():
        return None
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _symbol_report(name: str, value) -> dict:
    try:
        signature = str(inspect.signature(value))
    except (TypeError, ValueError):
        signature = "<unavailable>"
    module = inspect.getmodule(value)
    module_file = getattr(module, "__file__", None)
    return {
        "status": "READY",
        "signature": signature,
        "module": getattr(module, "__name__", None),
        "module_file": str(module_file) if module_file else None,
        "module_sha256": _sha256_file(module_file),
    }


def _load_toolrush_plugin(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"ToolRush plugin not found: {path}")
    spec = importlib.util.spec_from_file_location("jar_exp_0013_toolrush_plugin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load ToolRush plugin spec: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    register = getattr(module, "register", None)
    if not callable(register):
        raise RuntimeError("ToolRush plugin does not expose register()")
    status = register(None)
    if not isinstance(status, dict):
        raise RuntimeError("ToolRush plugin did not return a compatibility status")
    snapshot_status = status.get("snapshot", {})
    if not isinstance(snapshot_status, dict) or snapshot_status.get("status") != "ready":
        raise RuntimeError(f"ToolRush warm-shell compatibility is not ready: {snapshot_status}")
    return module, status


def bootstrap_runtime(
    *,
    hermes_root: str | os.PathLike[str],
    workspace: str | os.PathLike[str],
    mode: str,
    toolrush_plugin: str | os.PathLike[str] | None = None,
):
    """Import and bind the real installed Hermes runtime inside this dedicated worker."""
    normalized = str(mode).strip().lower()
    flags = runtime_flags(normalized)
    os.environ.update(flags)

    root = Path(hermes_root).resolve()
    work = Path(workspace).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Hermes root not found: {root}")
    if not work.is_dir():
        raise FileNotFoundError(f"controlled workspace not found: {work}")
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    os.environ["TERMINAL_CWD"] = str(work)
    os.chdir(work)

    from tools import file_tools
    from tools.environments.local import LocalEnvironment
    from tools.file_operations import ShellFileOperations

    plugin_loaded = False
    plugin_status = None
    plugin_path = None
    if normalized == "toolrush":
        if not toolrush_plugin:
            raise RuntimeError("ToolRush treatment requires --toolrush-plugin")
        plugin_path = Path(toolrush_plugin).resolve()
        _, plugin_status = _load_toolrush_plugin(plugin_path)
        plugin_loaded = True
    elif toolrush_plugin:
        raise RuntimeError("stock worker must not receive a ToolRush plugin")

    environment = LocalEnvironment(cwd=str(work))
    operations = ShellFileOperations(environment)
    original_get_file_ops = file_tools._get_file_ops
    file_tools._get_file_ops = lambda task_id="default": operations

    surface = {
        "mode": normalized,
        "symbols": {
            "tools.file_tools.read_file_tool": _symbol_report(
                "tools.file_tools.read_file_tool", file_tools.read_file_tool
            ),
            "tools.file_tools.search_tool": _symbol_report(
                "tools.file_tools.search_tool", file_tools.search_tool
            ),
            "tools.environments.local.LocalEnvironment": _symbol_report(
                "tools.environments.local.LocalEnvironment", LocalEnvironment
            ),
            "tools.file_operations.ShellFileOperations": _symbol_report(
                "tools.file_operations.ShellFileOperations", ShellFileOperations
            ),
        },
        "toolrush_plugin_loaded": plugin_loaded,
        "toolrush_plugin_path": str(plugin_path) if plugin_path else None,
        "toolrush_plugin_sha256": _sha256_file(plugin_path),
        "toolrush_register_status": plugin_status,
        "toolrush_flags": dict(flags),
        "hermes_root": str(root),
        "workspace": str(work),
        "python": sys.executable,
    }

    def cleanup():
        file_tools._get_file_ops = original_get_file_ops
        environment.cleanup()

    return file_tools, environment, surface, cleanup


def _write_protocol(stream, payload: dict) -> None:
    stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JAR-EXP-0013 real Hermes host worker")
    parser.add_argument("--hermes-root", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--mode", choices=("stock", "toolrush"), required=True)
    parser.add_argument("--toolrush-plugin")
    args = parser.parse_args(argv)

    protocol_out = sys.stdout
    cleanup = None
    try:
        # Keep third-party/import diagnostics off the JSONL control channel.
        with redirect_stdout(sys.stderr):
            file_tools, environment, surface, cleanup = bootstrap_runtime(
                hermes_root=args.hermes_root,
                workspace=args.workspace,
                mode=args.mode,
                toolrush_plugin=args.toolrush_plugin,
            )
        _write_protocol(protocol_out, {"type": "ready", "surface": surface})

        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            request = json.loads(line)
            if request.get("type") == "close":
                _write_protocol(protocol_out, {"type": "closed"})
                break
            request_id = request.get("id")
            operation = request.get("operation")
            payload = request.get("payload", {})
            if not isinstance(request_id, str) or not request_id:
                raise ValueError("worker request requires id")
            try:
                with redirect_stdout(sys.stderr):
                    result = dispatch_operation(
                        str(operation),
                        payload,
                        workspace=args.workspace,
                        file_tools=file_tools,
                        environment=environment,
                        task_id=f"jar-exp-0013-{uuid.uuid4().hex}",
                    )
                _write_protocol(
                    protocol_out,
                    {"id": request_id, "ok": True, "result": result},
                )
            except Exception as exc:
                _write_protocol(
                    protocol_out,
                    {
                        "id": request_id,
                        "ok": False,
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    },
                )
        return 0
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        try:
            _write_protocol(
                protocol_out,
                {
                    "type": "fatal",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            )
        except Exception:
            pass
        return 2
    finally:
        if cleanup is not None:
            try:
                with redirect_stdout(sys.stderr):
                    cleanup()
            except Exception:
                traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
