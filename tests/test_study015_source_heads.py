import json
from pathlib import Path

from experiments.study015.source_fingerprint import canonical_fingerprint

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "study015_source_heads.draft.json"

REQUIRED = {
    "after-graph-governance","aie","trust-gateway","runtime","works-execution",
    "sentinel","continuum","context-continuity","skills-vault","model-registry",
    "STEWARD-by-Aftergraph",
}


def test_source_head_manifest_has_required_repos_and_valid_shas():
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    heads = doc["heads"]
    assert REQUIRED <= set(heads)
    assert all(len(sha) == 40 for sha in heads.values())
    assert all(set(sha) <= set("0123456789abcdef") for sha in heads.values())


def test_fingerprint_is_order_independent_and_sha256():
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    heads = doc["heads"]
    forward = canonical_fingerprint(heads)
    reverse = canonical_fingerprint(dict(reversed(list(heads.items()))))
    assert forward == reverse
    assert len(forward) == 64
