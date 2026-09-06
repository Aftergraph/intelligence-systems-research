from __future__ import annotations

from typing import Callable

_ALLOWED_RPC_TOOLS = frozenset({"read_file", "search_files"})
_MAX_RPC_CALLS = 16


def validate_rpc_calls(calls: object) -> list[dict]:
    if not isinstance(calls, list) or not (1 <= len(calls) <= _MAX_RPC_CALLS):
        raise ValueError(f"Phase-2 RPC call batch must contain 1..{_MAX_RPC_CALLS} calls")
    validated: list[dict] = []
    for index, raw in enumerate(calls):
        if not isinstance(raw, dict):
            raise TypeError(f"RPC call {index} must be a mapping")
        tool = raw.get("tool")
        if tool not in _ALLOWED_RPC_TOOLS:
            raise ValueError(f"RPC call {index} tool must be read_file or search_files")
        args = raw.get("args")
        if not isinstance(args, dict):
            raise TypeError(f"RPC call {index} args must be a mapping")
        validated.append({"tool": str(tool), "args": dict(args)})
    return validated


def _validate_results(results: object, expected_count: int) -> list[dict]:
    if not isinstance(results, list) or len(results) != expected_count:
        actual = len(results) if isinstance(results, list) else "non-list"
        raise RuntimeError(
            f"generated RPC result count mismatch: expected {expected_count}, got {actual}"
        )
    normalized: list[dict] = []
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise RuntimeError(f"RPC result {index} must be a mapping")
        if result.get("error") is not None:
            raise RuntimeError(f"RPC result {index} reported an error: {result.get('error')}")
        normalized.append(dict(result))
    return normalized


def execute_rpc_batch(client_namespace: dict, strategy: str, calls: object) -> list[dict]:
    """Execute one validated batch through the generated hermes_tools client namespace."""
    if not isinstance(client_namespace, dict):
        raise TypeError("generated RPC client namespace must be a mapping")
    validated = validate_rpc_calls(calls)
    strategy = str(strategy).strip().lower()
    if strategy == "sequential":
        call = client_namespace.get("_call")
        if not callable(call):
            raise RuntimeError("generated sequential RPC surface _call is unavailable")
        results = [call(item["tool"], dict(item["args"])) for item in validated]
    elif strategy == "parallel":
        parallel = client_namespace.get("parallel")
        if not callable(parallel):
            raise RuntimeError("generated parallel surface is unavailable in this Hermes lane")
        results = parallel(
            [{"tool": item["tool"], "args": dict(item["args"])} for item in validated]
        )
    else:
        raise ValueError(f"unsupported Phase-2 RPC strategy: {strategy}")
    return _validate_results(results, len(validated))


def build_worker_rpc_runner(stock_worker, toolrush_worker) -> Callable[[str, str, list[dict]], list[dict]]:
    """Route A/B RPC batches to their isolated workers without fallback substitution."""

    def run(condition: str, strategy: str, calls: list[dict]) -> list[dict]:
        if condition == "A":
            worker = stock_worker
        elif condition == "B":
            worker = toolrush_worker
        else:
            raise ValueError(f"unsupported Phase-2 RPC condition: {condition}")
        execute = getattr(worker, "execute", None)
        if not callable(execute):
            raise RuntimeError(f"condition {condition} worker does not expose execute()")
        validated = validate_rpc_calls(calls)
        response = execute(
            "rpc_batch",
            {
                "strategy": str(strategy),
                "calls": validated,
            },
        )
        if not isinstance(response, dict):
            raise RuntimeError("rpc_batch worker response must be a mapping")
        return _validate_results(response.get("results"), len(validated))

    return run
