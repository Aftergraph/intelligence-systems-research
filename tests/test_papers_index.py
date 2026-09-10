"""Public paper index must resolve to the canonical manuscripts on disk."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "PAPERS"
INDEX = PAPERS / "README.md"


def _indexed_manuscripts() -> list[str]:
    text = INDEX.read_text(encoding="utf-8")
    return [
        target
        for target in re.findall(r"\]\(([^)]+\.md)\)", text)
        if "/" not in target and target != "README.md"
    ]


def test_every_indexed_manuscript_exists():
    missing = [name for name in _indexed_manuscripts() if not (PAPERS / name).is_file()]
    assert missing == []


def test_index_covers_each_canonical_manuscript_once():
    canonical = sorted(p.name for p in PAPERS.glob("[0-9][0-9]-*.md"))
    indexed = sorted(_indexed_manuscripts())
    assert indexed == canonical
