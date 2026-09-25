from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _p50(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def aggregate_records(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate live benchmark JSON records by experimental condition.

    Definitions used here are intentionally explicit:
    - VSR = VERIFIED missions / total missions.
    - FCR = completion claims followed by a failing deterministic verifier /
      total completion claims.
    - Control-plane token tax = typed-decision tokens / all measured model
      tokens. It is a token tax, not a monetary CPVO estimate.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("condition") or "unknown")].append(record)

    result: dict[str, dict[str, Any]] = {}
    for condition, rows in grouped.items():
        verified = sum(1 for row in rows if str(row.get("status")) == "verified")
        completion_claims = 0
        false_completion_claims = 0
        provider_tokens = 0
        decision_tokens = 0
        wall: list[float] = []
        provider_latency: list[float] = []
        verification_latency: list[float] = []
        turns: list[float] = []
        for row in rows:
            metrics = row.get("metrics") or {}
            completion_claims += int(_num(metrics.get("completion_claims")))
            false_completion_claims += int(_num(metrics.get("false_completion_claims")))
            provider_tokens += int(_num(metrics.get("provider_input_tokens"))) + int(
                _num(metrics.get("provider_output_tokens"))
            )
            decision_tokens += int(_num(metrics.get("decision_input_tokens"))) + int(
                _num(metrics.get("decision_output_tokens"))
            )
            wall.append(_num(metrics.get("wall_time_ms")))
            provider_latency.append(_num(metrics.get("provider_latency_ms")))
            verification_latency.append(_num(metrics.get("verification_latency_ms")))
            turns.append(_num(row.get("turns")))

        total_tokens = provider_tokens + decision_tokens
        missions = len(rows)
        result[condition] = {
            "missions": missions,
            "verified": verified,
            "vsr": (verified / missions) if missions else 0.0,
            "completion_claims": completion_claims,
            "false_completion_claims": false_completion_claims,
            "fcr": (
                false_completion_claims / completion_claims if completion_claims else 0.0
            ),
            "provider_tokens": provider_tokens,
            "decision_tokens": decision_tokens,
            "total_model_tokens": total_tokens,
            "control_plane_token_tax": (
                decision_tokens / total_tokens if total_tokens else 0.0
            ),
            "p50_wall_time_ms": _p50(wall),
            "p50_provider_latency_ms": _p50(provider_latency),
            "p50_verification_latency_ms": _p50(verification_latency),
            "p50_turns": _p50(turns),
        }
    return result


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError("Benchmark JSONL rows must be objects")
        rows.append(value)
    return rows


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"YAML root must be a mapping: {path}")
    return payload


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def load_manifest(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    payload = _load_yaml(source)
    conditions = payload.get("conditions") or []
    cases = payload.get("cases") or []
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("Benchmark manifest requires non-empty conditions")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark manifest requires non-empty cases")
    resolved = dict(payload)
    resolved["_path"] = source
    resolved["conditions"] = [dict(x) for x in conditions]
    resolved["cases"] = [dict(x) for x in cases]
    return resolved


def _generator_signature(config_path: Path) -> tuple[tuple[Any, ...], ...]:
    from .config import AppConfig

    cfg = AppConfig.load(config_path)
    frontier = cfg.registry.eligible(frontier_required=True, require_tools=True)
    return tuple(
        sorted(
            (
                model.alias,
                model.provider,
                model.model,
                model.transport,
                model.base_url,
            )
            for model in frontier
        )
    )


def _required_envs(config_path: Path) -> set[str]:
    from .config import AppConfig

    cfg = AppConfig.load(config_path)
    decision = cfg.raw.get("decision") or cfg.raw.get("jev") or {}
    backend = str(decision.get("backend") or "jev").casefold()
    required: set[str] = set()
    if backend not in {"local", "heuristic"}:
        default = "OPENAI_API_KEY" if backend in {"openai", "chatgpt", "gpt"} else (
            "DIALAGRAM_API_KEY"
            if backend in {"openai_compatible", "compatible", "chat_completions"}
            else "TYPESAFE_API_KEY"
        )
        required.add(str(decision.get("api_key_env") or default))
    for model in cfg.registry.eligible(frontier_required=True, require_tools=True):
        if model.api_key_env:
            required.add(str(model.api_key_env))
        elif model.provider.casefold() in {"dialagram", "nexum"}:
            required.add("DIALAGRAM_API_KEY")
    return required


def preflight_manifest(path: str | Path) -> dict[str, Any]:
    import os

    manifest = load_manifest(path)
    base = Path(manifest["_path"]).parent
    signatures: dict[str, tuple[tuple[Any, ...], ...]] = {}
    required: set[str] = set()
    condition_rows: list[dict[str, Any]] = []
    for condition in manifest["conditions"]:
        condition_id = str(condition.get("id") or "").strip()
        if not condition_id:
            raise ValueError("Every benchmark condition requires an id")
        config_value = str(condition.get("config") or "").strip()
        if not config_value:
            raise ValueError(f"Condition {condition_id!r} requires config")
        config_path = _resolve(base, config_value)
        if not config_path.is_file():
            raise FileNotFoundError(config_path)
        signature = _generator_signature(config_path)
        if not signature:
            raise ValueError(f"Condition {condition_id!r} has no eligible frontier generator")
        signatures[condition_id] = signature
        envs = _required_envs(config_path)
        required.update(envs)
        condition_rows.append(
            {
                "id": condition_id,
                "config": config_value,
                "required_env": sorted(envs),
                "generator_signature": [list(x) for x in signature],
            }
        )

    invariant = len({signature for signature in signatures.values()}) == 1
    if not invariant:
        raise ValueError(
            "Generator invariant failed: paired control-plane conditions must use the same frontier generator set"
        )

    case_rows: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_id = str(case.get("id") or "").strip()
        source_value = str(case.get("source") or "").strip()
        if not case_id or not source_value or not str(case.get("task") or "").strip():
            raise ValueError("Every benchmark case requires id, source, and task")
        source = _resolve(base, source_value)
        if not source.is_dir():
            raise FileNotFoundError(source)
        case_rows.append(
            {
                "id": case_id,
                "source": source_value,
                "verify": str(case.get("verify") or "python -m pytest -q"),
            }
        )

    return {
        "manifest": str(Path(path)),
        "conditions": condition_rows,
        "cases": case_rows,
        "generator_invariant": invariant,
        "required_env": sorted(required),
        "missing_env": sorted(name for name in required if not os.environ.get(name)),
    }


def run_manifest(
    path: str | Path,
    *,
    output_dir: str | Path,
    repeats: int = 1,
    seed: int = 20260924,
) -> dict[str, Any]:
    """Execute the paired live benchmark and persist raw evidence + summary.

    The same frontier generator signature is enforced across conditions before
    any mission starts. Each mission receives a fresh copy of the broken
    fixture, and the baseline verifier must fail before the agent may run.
    """
    import os
    import random
    import shutil
    import tempfile
    from datetime import UTC, datetime

    from .agent import CodingAgent
    from .config import AppConfig
    from .decisions import DecisionEngine
    from .tools import RepoTools

    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    preflight = preflight_manifest(path)
    if preflight["missing_env"]:
        missing = ", ".join(preflight["missing_env"])
        raise RuntimeError(f"Live benchmark blocked: missing environment credentials: {missing}")

    manifest = load_manifest(path)
    base = Path(manifest["_path"]).parent
    out = Path(output_dir).resolve()
    evidence_root = out / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []

    condition_map: dict[str, dict[str, Any]] = {}
    for condition in manifest["conditions"]:
        condition_id = str(condition["id"])
        condition_map[condition_id] = {
            **condition,
            "config_path": _resolve(base, str(condition["config"])),
        }

    for repeat in range(1, repeats + 1):
        for case in manifest["cases"]:
            case_id = str(case["id"])
            source = _resolve(base, str(case["source"]))
            task = str(case["task"])
            verify_command = str(case.get("verify") or "python -m pytest -q")
            order = list(condition_map)
            rng.shuffle(order)
            for order_index, condition_id in enumerate(order):
                condition = condition_map[condition_id]
                with tempfile.TemporaryDirectory(prefix=f"jev-bench-{case_id}-") as tmp:
                    workspace = Path(tmp) / "workspace"
                    shutil.copytree(source, workspace)

                    baseline_tools = RepoTools(workspace, command_mode="verify_only")
                    baseline = baseline_tools.run_command(verify_command, safety_action="allow")
                    baseline_exit = int(baseline.get("exit_code", 1))
                    if baseline_exit == 0:
                        raise RuntimeError(
                            f"Invalid benchmark fixture {case_id!r}: baseline verifier already passes"
                        )

                    cfg = AppConfig.load(condition["config_path"])
                    decision_cfg = cfg.raw.get("decision") or cfg.raw.get("jev") or {}
                    engine = DecisionEngine(
                        cfg.decision_backend(), decision_model=decision_cfg.get("model")
                    )
                    runtime = cfg.runtime
                    audit_dir = evidence_root / condition_id
                    audit_dir.mkdir(parents=True, exist_ok=True)
                    audit_path = audit_dir / f"{case_id}.r{repeat}.audit.jsonl"
                    agent = CodingAgent(
                        workspace=workspace,
                        decisions=engine,
                        registry=cfg.registry,
                        provider_factory=cfg.provider_factory(),
                        verify_command=verify_command,
                        max_turns=int(runtime.get("max_turns", 24)),
                        scope_top_k=int(runtime.get("scope_top_k", 8)),
                        frontier_required=True,
                        command_mode=str(runtime.get("command_mode", "verify_only")),
                        audit_path=audit_path,
                        retention_every=int(runtime.get("retention_every", 6)),
                        loop_check_every=int(runtime.get("loop_check_every", 4)),
                        policy=dict(runtime.get("policy") or {}),
                        intelligence_fabric=cfg.intelligence_fabric(),
                        generation_required_vsr=cfg.required_vsr("generation"),
                    )
                    result = agent.run(task)
                    model_profile = None
                    if result.model_alias:
                        try:
                            model_profile = cfg.registry.by_alias(result.model_alias)
                        except KeyError:
                            model_profile = None
                    provider_name = model_profile.provider if model_profile is not None else None
                    provider_base_url = model_profile.base_url if model_profile is not None else None
                    provider_key_env = model_profile.api_key_env if model_profile is not None else None
                    if model_profile is not None and not provider_key_env:
                        provider_key_env = {
                            "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                            "google": "GOOGLE_API_KEY", "gemini": "GOOGLE_API_KEY",
                            "dialagram": "DIALAGRAM_API_KEY", "nexum": "DIALAGRAM_API_KEY",
                        }.get(model_profile.provider.casefold())
                    provider_authenticated = bool(provider_key_env and os.environ.get(provider_key_env))
                    transport_security = "https" if (provider_base_url or "https://provider.invalid").startswith("https://") else "local-or-plaintext"
                    records.append(
                        {
                            "timestamp_utc": datetime.now(UTC).isoformat(),
                            "benchmark": str(manifest.get("name") or Path(path).stem),
                            "condition": condition_id,
                            "case_id": case_id,
                            "repeat": repeat,
                            "randomized_order_index": order_index,
                            "status": result.status.value,
                            "trace_id": result.trace_id,
                            "model_alias": result.model_alias,
                            "model": result.model,
                            "provider": provider_name,
                            "provider_request_ids": list(result.provider_request_ids),
                            "provider_authenticated": provider_authenticated,
                            "transport_security": transport_security,
                            "turns": result.turns,
                            "baseline_verification_exit_code": baseline_exit,
                            "verification_exit_code": result.verification_exit_code,
                            "metrics": result.metrics,
                            "audit_path": str(audit_path.relative_to(out)),
                        }
                    )

    raw_path = out / "results.jsonl"
    write_jsonl(raw_path, records)
    summary = {
        "benchmark": str(manifest.get("name") or Path(path).stem),
        "hypothesis": manifest.get("hypothesis"),
        "manifest": str(Path(path).resolve()),
        "seed": seed,
        "repeats": repeats,
        "generator_invariant": True,
        "definitions": {
            "VSR": "verified missions / total missions",
            "FCR": "completion claims followed by failing deterministic verifier / completion claims",
            "control_plane_token_tax": "decision-plane tokens / all measured model tokens",
        },
        "conditions": aggregate_records(records),
        "raw_results": str(raw_path),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
