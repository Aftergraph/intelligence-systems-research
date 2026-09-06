from __future__ import annotations

from pathlib import Path
from time import perf_counter_ns
from typing import Callable

FROZEN_TOOL_OPERATIONS = (
    "bounded_read",
    "paginated_read",
    "exact_search",
    "repository_search",
    "context_search",
    "no_match_search",
    "file_discovery",
    "shell_builtin",
    "python_process",
    "git_process",
    "sequential_read_rpc",
    "parallel_read_rpc",
    "mixed_read_search_rpc",
)

_SOURCE_A = "\n".join(
    [
        "# JAR-EXP-0013 deterministic Phase-2 fixture",
        "def benchmark_value(index):",
        "    return f'benchmark-{index:03d}'",
        "",
    ]
    + [
        (
            "deterministic_marker_042 = 'deterministic-marker-042'"
            if index == 42
            else (
                "context_target = 'context-target'"
                if index == 120
                else f"fixture_value_{index:03d} = {index}"
            )
        )
        for index in range(1, 261)
    ]
) + "\n"

_SOURCE_B = "\n".join(
    [
        "# JAR-EXP-0013 deterministic pagination fixture",
        "def secondary_benchmark_value(index):",
        "    return index * 2",
        "",
    ]
    + [f"secondary_value_{index:03d} = {index * 2}" for index in range(1, 281)]
) + "\n"

_SOURCE_C = """# JAR-EXP-0013 deterministic discovery fixture\ndef discovery_benchmark_value():\n    return 'deterministic-file-discovery-marker'\n"""

_FIXTURE_FILES = {
    "source_a.py": _SOURCE_A,
    "source_b.py": _SOURCE_B,
    "source_c.py": _SOURCE_C,
}


def prepare_tool_microbench_workspace(workspace: str | Path) -> dict:
    """Create only the deterministic fixture files, refusing to overwrite foreign content."""
    root = Path(workspace)
    fixture = root / "fixture"
    fixture.mkdir(parents=True, exist_ok=True)

    written = []
    for name, expected in _FIXTURE_FILES.items():
        path = fixture / name
        if path.exists():
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                raise RuntimeError(f"Phase-2 fixture refuses to overwrite existing nonfixture content: {path}")
        else:
            path.write_text(expected, encoding="utf-8", newline="\n")
        written.append(str(path.resolve()))

    return {
        "fixture_root": str(fixture.resolve()),
        "files": written,
        "fixture_revision": 1,
    }


def _read_call(path: str, *, offset: int = 1, limit: int = 60) -> dict:
    return {"tool": "read_file", "args": {"path": path, "offset": offset, "limit": limit}}


def _search_call(path: str, pattern: str) -> dict:
    return {
        "tool": "search_files",
        "args": {"pattern": pattern, "path": path, "limit": 30},
    }


def build_operation_spec(operation: str) -> dict:
    """Map one frozen workload name to a real Hermes worker or generated-RPC operation."""
    operation = str(operation)
    worker_specs = {
        "bounded_read": {
            "worker_operation": "read",
            "payload": {"path": "fixture/source_a.py", "start_line": 1, "limit": 100},
        },
        "paginated_read": {
            "worker_operation": "read",
            "payload": {"path": "fixture/source_b.py", "start_line": 101, "limit": 100},
        },
        "exact_search": {
            "worker_operation": "search",
            "payload": {
                "query": "deterministic-marker-042",
                "path": "fixture/source_a.py",
                "limit": 30,
            },
        },
        "repository_search": {
            "worker_operation": "search",
            "payload": {
                "query": "benchmark_value",
                "path": "fixture",
                "file_glob": "*.py",
                "limit": 30,
            },
        },
        "context_search": {
            "worker_operation": "search",
            "payload": {
                "query": "context-target",
                "path": "fixture/source_a.py",
                "context": 2,
                "limit": 30,
            },
        },
        "no_match_search": {
            "worker_operation": "search",
            "payload": {
                "query": "JAR_EXP_0013_NO_MATCH_Q93Z",
                "path": "fixture",
                "file_glob": "*.py",
                "limit": 30,
            },
        },
        "file_discovery": {
            "worker_operation": "search",
            "payload": {
                "query": "*.py",
                "target": "files",
                "path": "fixture",
                "limit": 30,
            },
        },
        "shell_builtin": {
            "worker_operation": "shell",
            "payload": {"command": "printf 'jar-exp-0013-shell\\n'"},
        },
        "python_process": {
            "worker_operation": "shell",
            "payload": {"command": "python -c \"print('jar-exp-0013-python')\""},
        },
        "git_process": {
            "worker_operation": "shell",
            "payload": {"command": "git --version"},
        },
    }
    if operation in worker_specs:
        return {
            "operation_name": operation,
            "lane": "worker",
            **worker_specs[operation],
        }

    read_paths = [
        "fixture/source_a.py",
        "fixture/source_b.py",
        "fixture/source_c.py",
        "fixture/source_a.py",
    ]
    rpc_specs = {
        "sequential_read_rpc": {
            "strategy_by_condition": {"A": "sequential", "B": "sequential"},
            "calls": [_read_call(path, offset=30, limit=60) for path in read_paths],
        },
        "parallel_read_rpc": {
            "strategy_by_condition": {"A": "sequential", "B": "parallel"},
            "calls": [_read_call(path, offset=30, limit=60) for path in read_paths],
        },
        "mixed_read_search_rpc": {
            "strategy_by_condition": {"A": "sequential", "B": "parallel"},
            "calls": [
                _read_call("fixture/source_a.py", offset=30, limit=60),
                _search_call("fixture/source_a.py", "benchmark_value"),
                _read_call("fixture/source_b.py", offset=30, limit=60),
                _search_call("fixture/source_b.py", "secondary_benchmark_value"),
            ],
        },
    }
    if operation in rpc_specs:
        return {
            "operation_name": operation,
            "lane": "rpc",
            **rpc_specs[operation],
        }

    raise ValueError(f"unsupported frozen tool microbenchmark operation: {operation}")


class ToolMicrobenchOperationRunner:
    """Bind the Phase-2 executor to isolated stock/ToolRush workers and optional real RPC."""

    def __init__(
        self,
        *,
        stock_worker,
        toolrush_worker,
        rpc_runner: Callable[[str, str, list[dict]], object] | None,
        clock_ns: Callable[[], int] = perf_counter_ns,
    ):
        self.stock_worker = stock_worker
        self.toolrush_worker = toolrush_worker
        self.rpc_runner = rpc_runner
        self.clock_ns = clock_ns
        if not callable(clock_ns):
            raise TypeError("clock_ns must be callable")

    def __call__(self, condition: str, operation: str, sample_kind: str, repetition: int) -> dict:
        if condition not in {"A", "B"}:
            raise ValueError(f"unsupported Phase-2 condition: {condition}")
        if sample_kind not in {"cold", "warm"}:
            raise ValueError(f"unsupported Phase-2 sample kind: {sample_kind}")
        if not isinstance(repetition, int) or repetition < 0:
            raise ValueError("Phase-2 repetition must be a non-negative integer")

        spec = build_operation_spec(operation)
        started = self.clock_ns()
        if spec["lane"] == "worker":
            worker = self.stock_worker if condition == "A" else self.toolrush_worker
            execute = getattr(worker, "execute", None)
            if not callable(execute):
                raise RuntimeError(f"{condition} Hermes worker does not expose execute()")
            observable = execute(spec["worker_operation"], dict(spec["payload"]))
        else:
            if self.rpc_runner is None or not callable(self.rpc_runner):
                raise RuntimeError("Phase-2 RPC lane is not bound to a real generated-RPC runner")
            strategy = spec["strategy_by_condition"][condition]
            calls = [
                {"tool": call["tool"], "args": dict(call["args"])}
                for call in spec["calls"]
            ]
            observable = self.rpc_runner(condition, strategy, calls)
        elapsed_ms = (self.clock_ns() - started) / 1_000_000
        if elapsed_ms < 0:
            raise RuntimeError("Phase-2 timing clock moved backwards")
        return {
            "observable": observable,
            "elapsed_ms": elapsed_ms,
            "stderr": "",
        }
