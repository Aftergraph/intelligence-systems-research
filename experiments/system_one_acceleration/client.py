"""Optional TypeSafe SDK boundary for JAR-EXP-0014.

The module does not import or call TypeSafe at import time. Tests inject a fake SDK/client,
so repository CI remains zero-network. Production/runtime integration is out of scope here.
"""

from importlib import import_module
from pathlib import Path
from time import perf_counter
import json
from typing import Any, Mapping


class TypeSafeBoundaryError(RuntimeError):
    pass


def load_frozen_contracts(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("status") != "FROZEN_PRECALIBRATION":
        raise TypeSafeBoundaryError("question contracts are not frozen")
    contracts = data.get("contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise TypeSafeBoundaryError("question contracts missing")
    return contracts


def _sdk_module(sdk: Any | None = None) -> Any:
    if sdk is not None:
        return sdk
    try:
        return import_module("typesafe_sdk")
    except ImportError as exc:
        raise TypeSafeBoundaryError(
            "typesafe_sdk is not installed; live System One execution is unavailable"
        ) from exc


def build_sdk_questions(
    contracts: Mapping[str, Mapping[str, Any]], *, sdk: Any | None = None
) -> dict[str, Any]:
    module = _sdk_module(sdk)
    built: dict[str, Any] = {}

    for key, contract in contracts.items():
        kind = contract.get("type")
        instructions = contract.get("instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise TypeSafeBoundaryError(f"{key}: instructions missing")

        if kind == "noul":
            built[key] = module.Noul(instructions=instructions)
        elif kind == "choice":
            criteria = contract.get("criteria")
            if not isinstance(criteria, dict) or not criteria:
                raise TypeSafeBoundaryError(f"{key}: choice criteria missing")
            built[key] = module.Choice(
                instructions=instructions,
                criteria=criteria,
            )
        elif kind == "score":
            criteria = contract.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                raise TypeSafeBoundaryError(f"{key}: score criteria missing")
            built[key] = module.Score(
                instructions=instructions,
                criteria=criteria,
            )
        else:
            raise TypeSafeBoundaryError(f"{key}: unsupported question type {kind!r}")

    return built


def invoke_system_one(
    *,
    client: Any,
    state: Any,
    questions: Mapping[str, Any],
    requested_model: str,
) -> tuple[Any, float]:
    """Invoke an injected TypeSafe-compatible client and return response + latency.

    Callers own authorization, budgets, retries and evidence persistence.
    This boundary intentionally has no retry loop or fallback side effects.
    """
    if not requested_model:
        raise TypeSafeBoundaryError("requested_model is required")
    started = perf_counter()
    response = client.system_one(
        model=requested_model,
        state=state,
        questions=dict(questions),
    )
    latency_ms = (perf_counter() - started) * 1000.0
    returned = getattr(response, "model", None)
    if not isinstance(returned, str) or not returned:
        raise TypeSafeBoundaryError("provider response did not include model identity")
    return response, latency_ms
