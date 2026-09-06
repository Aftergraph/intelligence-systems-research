from __future__ import annotations

from pathlib import Path

import yaml


def load_trace(path: Path) -> list[dict]:
    """Load a frozen deterministic trace and validate its minimal schema."""
    with Path(path).open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("steps"), list):
        raise ValueError("trace must contain a steps list")
    steps = document["steps"]
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"trace step {index} must be a mapping")
        if not isinstance(step.get("operation"), str) or not step["operation"]:
            raise ValueError(f"trace step {index} missing operation")
        if not isinstance(step.get("payload", {}), dict):
            raise ValueError(f"trace step {index} payload must be a mapping")
        step.setdefault("payload", {})
    return steps
