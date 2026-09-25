#!/usr/bin/env python3
"""Export every model known by the installed LiteLLM build to JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="litellm-model-catalog.json")
    args = parser.parse_args()
    try:
        import litellm  # type: ignore
    except ImportError as exc:
        raise SystemExit("LiteLLM is not installed; install the all-providers extra") from exc
    catalog = getattr(litellm, "model_cost", None) or getattr(litellm, "model_cost_map", None)
    if not isinstance(catalog, dict):
        raise SystemExit("Installed LiteLLM does not expose a model catalog mapping")
    path = Path(args.output)
    path.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {len(catalog)} models -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
