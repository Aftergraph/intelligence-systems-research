from __future__ import annotations

import re
from pathlib import Path

from .types import CandidateFile

_SOURCE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".kts", ".cs",
    ".c", ".h", ".cpp", ".hpp", ".rb", ".php", ".swift", ".scala", ".sh", ".bash", ".zsh", ".md",
    ".toml", ".yaml", ".yml", ".json", ".jsonc", ".xml", ".sql", ".graphql", ".proto",
}
_SKIP = {".git", "node_modules", ".venv", "venv", "dist", "build", "coverage", "__pycache__", ".next", ".pytest_cache", ".jev", ".jev-one"}


def collect_candidates(root: str | Path, task: str, *, limit: int = 48, excerpt_chars: int = 5000) -> list[CandidateFile]:
    root = Path(root).resolve()
    terms = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", task)}
    scored: list[tuple[float, CandidateFile]] = []
    for p in root.rglob("*"):
        if not p.is_file() or any(part in _SKIP for part in p.parts):
            continue
        if p.suffix.lower() not in _SOURCE_SUFFIXES and p.name not in {"Makefile", "Dockerfile", "AGENTS.md"}:
            continue
        try:
            size = p.stat().st_size
            if size > 2_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.relative_to(root))
        hay = f"{rel}\n{text[:10000]}".lower()
        lexical = sum(1 for term in terms if term in hay)
        test_bonus = 0.5 if ("test" in task.lower() and "test" in rel.lower()) else 0.0
        source_bonus = 0.2 if p.suffix.lower() not in {".md", ".json", ".yaml", ".yml"} else 0.0
        score = lexical + test_bonus + source_bonus
        scored.append((score, CandidateFile(rel, text[:excerpt_chars])))
    scored.sort(key=lambda item: (item[0], item[1].path), reverse=True)
    return [candidate for _, candidate in scored[:limit]]


def format_selected_context(selected: list[CandidateFile]) -> str:
    chunks: list[str] = []
    for item in selected:
        chunks.append(f"### {item.path} [Jev scope={item.score:.2f}, confidence={item.confidence:.2f}]\n{item.excerpt}")
    return "\n\n".join(chunks)
