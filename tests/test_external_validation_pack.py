"""
test_external_validation_pack.py
================================

Pins the equivalence between the in-tree conformance suite and the
external_validation_pack_vNext bundle that will be sent to independent
implementers (under IP hold — not yet transmitted).

The pack is the canonical "what the implementer sees" surface. If the
in-tree suite drifts (e.g., new TC added, schema updated) without
mirroring the change in the pack, the pack goes stale and an
implementer's results will not match the program's record. This test
fails loudly on any drift.

It also verifies the standalone runner is functional and that no
hardcoded secrets are present in the pack (the pack must be
self-contained, with no credentials baked in).

ponytail: stdlib only; deterministic; no network.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "external_validation_pack_vNext"
IN_TREE = ROOT / "conformance"


def _read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ─── Pack structure ───────────────────────────────────────────────────────


def test_pack_required_files_present():
    required = [
        "README.md",
        "SPECIFICATION.md",
        "NORMATIVE_TERMINOLOGY.md",
        "IMPLEMENTATION_RUBRIC.md",
        "conformance/standalone_runner.py",
        "conformance/test_cases.json",
    ]
    for r in required:
        assert (PACK / r).is_file(), f"missing required pack file: {r}"


def test_pack_schemas_present():
    for schema in ["intelligence-system.v0alpha1.json",
                   "mission.v0alpha1.json",
                   "delegation.v0alpha1.json",
                   "evidence.v0alpha1.json"]:
        assert (PACK / "schemas" / schema).is_file(), f"missing pack schema: {schema}"


def test_pack_test_vectors_present():
    vectors = list((PACK / "test_vectors").glob("*.json"))
    assert len(vectors) >= 3, f"expected >=3 test vectors, got {len(vectors)}"


# ─── Conformance suite drift ─────────────────────────────────────────────


def test_pack_test_cases_match_in_tree():
    """The pack's test cases must be byte-identical to the in-tree
    suite. Any change to the in-tree cases (new TC, modified
    expectation) must be mirrored in the pack before transmission."""
    in_tree = _read_json(IN_TREE / "test_cases.json")
    pack = _read_json(PACK / "conformance" / "test_cases.json")
    assert in_tree == pack, \
        "conformance test cases drifted between in-tree and pack"


# ─── Pack hygiene ─────────────────────────────────────────────────────────


_SECRET_PATTERNS = [
    re.compile(r"dgr_live_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS
]


def test_pack_has_no_hardcoded_secrets():
    """No API keys, AWS access keys, or other secrets in the pack."""
    for path in PACK.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".jsonl", ".txt", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pat in _SECRET_PATTERNS:
                m = pat.search(text)
                assert m is None, f"secret pattern {pat.pattern} in {path}: {m.group(0)}"


# ─── Standalone runner functional ────────────────────────────────────────


def test_standalone_runner_exits_zero():
    """The runner must run (exit 0) in self-check mode when no candidate
    is provided. This is the test an external implementer runs first
    to validate the toolchain."""
    result = subprocess.run(
        [sys.executable, str(PACK / "conformance" / "standalone_runner.py")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"standalone runner failed (exit {result.returncode}): "
        f"stdout={result.stdout[-300:]!r} stderr={result.stderr[-300:]!r}"
    )
    assert "STANDALONE EXTERNAL CONFORMANCE RUNNER" in result.stdout, \
        "runner banner missing"
