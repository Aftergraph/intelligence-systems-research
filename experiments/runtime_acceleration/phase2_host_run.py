from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from .controlled_host import capture_preflight_snapshot
from .phase2_bindings import (
    ToolMicrobenchOperationRunner,
    prepare_tool_microbench_workspace,
)
from .phase2_rpc import build_worker_rpc_runner
from .phase2_tool_microbench import execute_tool_microbench_plan
from .protocol import load_protocol
from .runtime_bridge import HermesWorkerClient


def _surface(worker, label: str) -> dict:
    surface = getattr(worker, "surface", None)
    if not isinstance(surface, dict):
        raise RuntimeError(f"{label} worker did not report a surface mapping")
    return surface


def validate_phase2_worker_surfaces(stock_worker, toolrush_worker) -> dict:
    """Fail closed unless the isolated workers expose the frozen Phase-2 RPC lanes."""
    stock = _surface(stock_worker, "stock")
    treatment = _surface(toolrush_worker, "ToolRush")

    if stock.get("mode") != "stock":
        raise RuntimeError(f"stock worker mode mismatch: {stock.get('mode')}")
    if treatment.get("mode") != "toolrush":
        raise RuntimeError(f"ToolRush worker mode mismatch: {treatment.get('mode')}")

    stock_rpc = stock.get("rpc")
    treatment_rpc = treatment.get("rpc")
    if not isinstance(stock_rpc, dict) or not isinstance(treatment_rpc, dict):
        raise RuntimeError("Phase-2 workers must report generated RPC surfaces")
    if stock_rpc.get("transport") != "tcp_loopback":
        raise RuntimeError("stock generated RPC transport must be tcp_loopback")
    if treatment_rpc.get("transport") != "tcp_loopback":
        raise RuntimeError("ToolRush generated RPC transport must be tcp_loopback")
    if stock_rpc.get("sequential_available") is not True:
        raise RuntimeError("stock generated sequential RPC surface is unavailable")
    if treatment_rpc.get("sequential_available") is not True:
        raise RuntimeError("ToolRush generated sequential RPC surface is unavailable")
    if treatment_rpc.get("parallel_available") is not True:
        raise RuntimeError("ToolRush generated parallel RPC surface is unavailable")

    return {
        "stock": dict(stock_rpc),
        "toolrush": dict(treatment_rpc),
    }


class Phase2WorkerLifecycle:
    """Own one fresh A/B worker pair per frozen tool operation.

    The pair is created before the first preflight snapshot for an operation, reused for that
    operation's cold+warm blocks, then closed before the next operation is prepared. Worker
    startup is therefore outside the measured operation timer while warm-state treatment is
    preserved within the operation.
    """

    def __init__(
        self,
        config: dict,
        *,
        worker_factory: Callable[[dict, str], object] = HermesWorkerClient,
    ):
        if not isinstance(config, dict):
            raise TypeError("Phase-2 host config must be a mapping")
        if config.get("experiment_id") != "JAR-EXP-0013":
            raise ValueError("Phase-2 host config requires experiment_id JAR-EXP-0013")
        workspace = config.get("workspace")
        if not isinstance(workspace, str) or not workspace.strip():
            raise ValueError("Phase-2 host config requires workspace")
        if not callable(worker_factory):
            raise TypeError("worker_factory must be callable")

        self.config = dict(config)
        self.worker_factory = worker_factory
        self.workspace = Path(workspace)
        self.fixture = prepare_tool_microbench_workspace(self.workspace)
        self.current_operation: str | None = None
        self.stock_worker = None
        self.toolrush_worker = None
        self.operation_runner: ToolMicrobenchOperationRunner | None = None
        self._closed = False

    def _close_current(self) -> None:
        workers = [self.toolrush_worker, self.stock_worker]
        self.toolrush_worker = None
        self.stock_worker = None
        self.operation_runner = None
        self.current_operation = None

        seen: set[int] = set()
        first_error: Exception | None = None
        for worker in workers:
            if worker is None or id(worker) in seen:
                continue
            seen.add(id(worker))
            close = getattr(worker, "close", None)
            if not callable(close):
                if first_error is None:
                    first_error = RuntimeError("Phase-2 worker does not expose close()")
                continue
            try:
                close()
            except Exception as exc:  # cleanup must attempt both workers
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    @staticmethod
    def _operation_for_pair(pair_id: str, pair_runs: list[dict]) -> str:
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("Phase-2 pair_id must be non-empty")
        if not isinstance(pair_runs, list) or len(pair_runs) != 2:
            raise ValueError("Phase-2 lifecycle requires an A/B paired block")
        operations = {
            run.get("operation")
            for run in pair_runs
            if isinstance(run, dict)
        }
        conditions = {
            run.get("condition")
            for run in pair_runs
            if isinstance(run, dict)
        }
        if len(operations) != 1 or None in operations:
            raise ValueError(f"Phase-2 pair {pair_id} has inconsistent operation identity")
        if conditions != {"A", "B"}:
            raise ValueError(f"Phase-2 pair {pair_id} must contain A/B exactly once")
        return str(next(iter(operations)))

    def prepare_pair(self, pair_id: str, pair_runs: list[dict]) -> None:
        if self._closed:
            raise RuntimeError("Phase-2 worker lifecycle is closed")
        operation = self._operation_for_pair(pair_id, pair_runs)
        if operation == self.current_operation and self.operation_runner is not None:
            return

        if self.stock_worker is not None or self.toolrush_worker is not None:
            self._close_current()

        # Re-verify deterministic fixture identity before every fresh worker pair. This is
        # outside the measurement timer and refuses foreign content instead of overwriting it.
        self.fixture = prepare_tool_microbench_workspace(self.workspace)

        stock = None
        treatment = None
        try:
            stock = self.worker_factory(self.config, "stock")
            treatment = self.worker_factory(self.config, "toolrush")
            validate_phase2_worker_surfaces(stock, treatment)
            rpc_runner = build_worker_rpc_runner(stock, treatment)
            runner = ToolMicrobenchOperationRunner(
                stock_worker=stock,
                toolrush_worker=treatment,
                rpc_runner=rpc_runner,
            )
        except Exception:
            for worker in (treatment, stock):
                if worker is None:
                    continue
                close = getattr(worker, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass
            raise

        self.stock_worker = stock
        self.toolrush_worker = treatment
        self.operation_runner = runner
        self.current_operation = operation

    def run_operation(
        self, condition: str, operation: str, sample_kind: str, repetition: int
    ) -> dict:
        if self._closed:
            raise RuntimeError("Phase-2 worker lifecycle is closed")
        if self.operation_runner is None or self.current_operation != operation:
            raise RuntimeError(
                f"Phase-2 operation {operation} was not prepared before measurement"
            )
        return self.operation_runner(condition, operation, sample_kind, repetition)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._close_current()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def run_controlled_phase2(
    config: dict,
    plan: dict,
    host_probe: dict,
    protocol: dict,
    *,
    evidence_root: str | Path,
    execution_id: str,
    worker_factory: Callable[[dict, str], object] = HermesWorkerClient,
    snapshot_provider: Callable[[], dict] = capture_preflight_snapshot,
) -> dict:
    """Run the frozen Phase-2 A/B tool microbenchmark on the authoritative host.

    This function intentionally does not create or relax the controlled-host probe. It consumes
    an already-READY probe, starts fresh isolated workers per operation, takes preflight after
    startup and before each paired block, and delegates immutable evidence/correctness handling
    to the Phase-2 executor.
    """
    if not callable(snapshot_provider):
        raise TypeError("snapshot_provider must be callable")

    lifecycle = Phase2WorkerLifecycle(config, worker_factory=worker_factory)
    try:
        return execute_tool_microbench_plan(
            plan,
            protocol,
            host_probe,
            evidence_root=evidence_root,
            execution_id=execution_id,
            operation_runner=lifecycle.run_operation,
            snapshot_provider=snapshot_provider,
            pair_prepare=lifecycle.prepare_pair,
        )
    finally:
        lifecycle.close()


def _load_json(path: str | Path, label: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{label} must be a JSON object")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute JAR-EXP-0013 Phase-2 tool microbenchmarks on a READY host."
    )
    parser.add_argument("--config", required=True, help="Controlled-host JSON config")
    parser.add_argument("--plan", required=True, help="Frozen TOOL_MICROBENCH JSON plan")
    parser.add_argument("--probe", required=True, help="READY controlled-host probe JSON")
    parser.add_argument("--protocol", required=True, help="Frozen protocol.yaml")
    parser.add_argument("--evidence-root", required=True, help="Append-only evidence root")
    parser.add_argument("--execution-id", required=True, help="Unique immutable execution id")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    runner: Callable[..., dict] = run_controlled_phase2,
) -> int:
    args = _parser().parse_args(argv)
    config = _load_json(args.config, "controlled-host config")
    plan = _load_json(args.plan, "Phase-2 plan")
    probe = _load_json(args.probe, "controlled-host probe")
    protocol = load_protocol(Path(args.protocol))
    summary = runner(
        config,
        plan,
        probe,
        protocol,
        evidence_root=Path(args.evidence_root),
        execution_id=args.execution_id,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("state") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
