"""Cross-repo black-box probe fabric for STUDY-015."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data" / "study015_probe_receipt.schema.json"
TARGETS_PATH = ROOT / "data" / "study015_probe_targets.draft.json"


class ProbeFabricError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_receipt(
    receipt: dict[str, Any],
    *,
    target: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_schema = schema if schema is not None else load_json(SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(active_schema)
    jsonschema.validate(receipt, active_schema)

    if receipt["component"] != target["component"]:
        raise ProbeFabricError(
            f"component mismatch: receipt={receipt['component']} target={target['component']}"
        )
    if receipt["source_head"] != target["expected_head"]:
        raise ProbeFabricError(
            f"source-head mismatch for {target['component']}: "
            f"{receipt['source_head']} != {target['expected_head']}"
        )
    missing = [
        name
        for name in target["required_mechanisms"]
        if receipt["mechanisms"].get(name) is not True
    ]
    if missing:
        raise ProbeFabricError(
            f"{target['component']} did not demonstrate required mechanisms: {missing}"
        )
    return receipt


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def composition_root(receipts: list[dict[str, Any]]) -> str:
    chunks = []
    for receipt in sorted(receipts, key=lambda item: item["component"]):
        digest = hashlib.sha256(canonical_receipt_bytes(receipt)).hexdigest()
        chunks.append(f"{receipt['component']}={digest}")
    payload = "\n".join(chunks) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_target(target: dict[str, Any], repo_dir: Path) -> dict[str, Any]:
    actual_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True
    ).strip()
    if actual_head != target["expected_head"]:
        raise ProbeFabricError(
            f"checkout head mismatch for {target['component']}: "
            f"{actual_head} != {target['expected_head']}"
        )

    proc = subprocess.run(
        target["command"],
        cwd=repo_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ProbeFabricError(
            f"{target['component']} probe failed rc={proc.returncode}: "
            f"{proc.stderr[-4000:]}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise ProbeFabricError(f"{target['component']} probe produced no receipt")
    try:
        receipt = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise ProbeFabricError(
            f"{target['component']} final stdout line is not JSON: {lines[-1]!r}"
        ) from exc
    return validate_receipt(receipt, target=target)


def compose(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    components = sorted(receipt["component"] for receipt in receipts)
    if len(components) != len(set(components)):
        raise ProbeFabricError("duplicate component receipt")
    return {
        "schema": "study015.composition-probe/1.0",
        "study_id": "STUDY-015",
        "execution_class": "LOCAL_CROSS_REPO_PROBE",
        "network_used_by_component_probes": False,
        "component_count": len(receipts),
        "components": components,
        "source_heads": {
            receipt["component"]: receipt["source_head"]
            for receipt in sorted(receipts, key=lambda item: item["component"])
        },
        "probe_root_sha256": composition_root(receipts),
        "receipts": receipts,
    }


def parse_component_roots(values: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ProbeFabricError("--component-root must be component=/path")
        component, raw_path = value.split("=", 1)
        out[component] = Path(raw_path).resolve()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component-root", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    roots = parse_component_roots(args.component_root)
    manifest = load_json(TARGETS_PATH)
    receipts = []
    for target in manifest["targets"]:
        component = target["component"]
        repo_dir = roots.get(component)
        if repo_dir is None:
            raise ProbeFabricError(f"missing --component-root for {component}")
        receipts.append(run_target(target, repo_dir))

    result = compose(receipts)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
