from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from .browser_runtime import ChromiumBackendFactory, ObscuraBackendFactory
from .controlled_host import capture_preflight_snapshot
from .fixture_server import fixture_server
from .phase1_executor import execute_phase1_plan
from .protocol import load_protocol
from .runtime_bridge import HermesWorkerClient, build_runtime_adapter_factory


class Phase1HostRunError(RuntimeError):
    """Raised before treatment execution when the controlled-host contract is invalid."""


_REQUIRED_RUNTIME_CONFIG = (
    "hermes_python",
    "hermes_root",
    "workspace",
    "toolrush_plugin",
    "obscura_executable",
)


def _load_json(path: str | Path, label: str) -> dict:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise Phase1HostRunError(f"{label} must be a JSON object")
    return payload


def _require_controlled_contract(
    config: dict,
    plan: dict,
    protocol: dict,
    host_probe: dict,
) -> dict[str, str]:
    identities = {
        config.get("experiment_id"),
        plan.get("experiment_id"),
        protocol.get("experiment_id"),
        host_probe.get("experiment_id"),
    }
    if identities != {"JAR-EXP-0013"}:
        raise Phase1HostRunError("unexpected JAR-EXP-0013 experiment identity")
    if host_probe.get("state") != "READY":
        raise Phase1HostRunError("controlled host must be READY before Phase-1 runtime starts")
    if plan.get("phase") != "TRACE_REPLAY" or plan.get("plan_only") is not True:
        raise Phase1HostRunError("Phase-1 requires the frozen TRACE_REPLAY plan")
    if tuple(plan.get("conditions", ())) != ("A", "B", "C", "D"):
        raise Phase1HostRunError("Phase-1 plan conditions must be exactly A/B/C/D")

    missing = [field for field in _REQUIRED_RUNTIME_CONFIG if not config.get(field)]
    if missing:
        raise Phase1HostRunError(f"missing controlled runtime config: {', '.join(missing)}")

    protocol_pins = protocol.get("pins")
    probe_pins = host_probe.get("pins")
    if not isinstance(protocol_pins, dict) or not isinstance(probe_pins, dict):
        raise Phase1HostRunError("controlled host pin evidence is missing")
    pins: dict[str, str] = {}
    for name in ("toolrush", "obscura"):
        expected = str(protocol_pins.get(name, "")).strip().lower()
        observed = str(probe_pins.get(name, "")).strip().lower()
        if not expected or observed != expected:
            raise Phase1HostRunError(
                f"{name} pin mismatch between frozen protocol and controlled-host probe"
            )
        pins[name] = expected
    return pins


def run_phase1_host(
    config: dict,
    plan: dict,
    protocol: dict,
    host_probe: dict,
    *,
    evidence_root: str | Path,
    execution_id: str,
    fixture_server_factory: Callable[[], object] = fixture_server,
    worker_factory: Callable[[dict, str], object] = HermesWorkerClient,
    chromium_factory_cls=ChromiumBackendFactory,
    obscura_factory_cls=ObscuraBackendFactory,
    adapter_factory_builder: Callable[..., object] = build_runtime_adapter_factory,
    executor: Callable[..., dict] = execute_phase1_plan,
    snapshot_provider: Callable[[], dict] = capture_preflight_snapshot,
) -> dict:
    """Run frozen deterministic Phase-1 on one already-READY controlled host.

    This orchestration layer starts no model/provider workload. It binds the exact stock and
    ToolRush Hermes workers, drives Chromium and Obscura against the same loopback fixture,
    delegates all timing/evidence semantics to ``execute_phase1_plan``, and always reaps both
    persistent Hermes workers when the execution scope exits.
    """
    if not isinstance(config, dict) or not isinstance(plan, dict):
        raise TypeError("controlled-host config and plan must be mappings")
    if not isinstance(protocol, dict) or not isinstance(host_probe, dict):
        raise TypeError("protocol and host probe must be mappings")
    if not str(execution_id).strip():
        raise Phase1HostRunError("execution_id must be non-empty")

    pins = _require_controlled_contract(config, plan, protocol, host_probe)
    root = Path(evidence_root)

    with fixture_server_factory() as fixture_base_url:
        stock_worker = worker_factory(dict(config), "stock")
        toolrush_worker = None
        try:
            toolrush_worker = worker_factory(dict(config), "toolrush")

            chromium_factory = chromium_factory_cls(
                fixture_base_url=str(fixture_base_url),
                executable_path=config.get("chromium_executable"),
                evidence_root=root,
            )
            obscura_factory = obscura_factory_cls(
                obscura_executable=config["obscura_executable"],
                fixture_base_url=str(fixture_base_url),
                evidence_root=root,
            )
            condition_factory = adapter_factory_builder(
                stock_worker=stock_worker,
                toolrush_worker=toolrush_worker,
                chromium_backend_factory=chromium_factory,
                obscura_backend_factory=obscura_factory,
                toolrush_revision=pins["toolrush"],
                obscura_revision=pins["obscura"],
            )

            return executor(
                plan,
                protocol,
                host_probe,
                evidence_root=root,
                execution_id=str(execution_id),
                adapter_factory=condition_factory,
                snapshot_provider=snapshot_provider,
            )
        finally:
            if toolrush_worker is not None:
                toolrush_worker.close()
            stock_worker.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute JAR-EXP-0013 deterministic Phase-1 on a READY controlled host."
    )
    parser.add_argument("--config", required=True, help="Controlled-host JSON config")
    parser.add_argument("--plan", required=True, help="Frozen TRACE_REPLAY JSON plan")
    parser.add_argument("--probe", required=True, help="READY controlled-host probe JSON")
    parser.add_argument("--protocol", required=True, help="Frozen protocol.yaml")
    parser.add_argument("--evidence-root", required=True, help="Append-only evidence root")
    parser.add_argument("--execution-id", required=True, help="Unique immutable execution id")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    runner: Callable[..., dict] = run_phase1_host,
) -> int:
    args = _parser().parse_args(argv)
    config = _load_json(args.config, "controlled-host config")
    plan = _load_json(args.plan, "measurement plan")
    probe = _load_json(args.probe, "controlled-host probe")
    protocol = load_protocol(Path(args.protocol))

    summary = runner(
        config,
        plan,
        protocol,
        probe,
        evidence_root=Path(args.evidence_root),
        execution_id=args.execution_id,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("state") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
