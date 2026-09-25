"""Canonical source-head fingerprinting for STUDY-015."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "study015_source_heads.draft.json"


def canonical_fingerprint(heads: Mapping[str, str]) -> str:
    for repo, sha in heads.items():
        if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
            raise ValueError(f"invalid git SHA for {repo}: {sha}")
    payload = "\n".join(f"{repo}={heads[repo]}" for repo in sorted(heads)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_heads(path: Path = DEFAULT_MANIFEST) -> dict[str, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return dict(doc["heads"])
