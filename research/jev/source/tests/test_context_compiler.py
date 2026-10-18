from __future__ import annotations

from jev_engineering.context_compiler import (
    ContextCandidate,
    ContextCompiler,
    SemanticGarbageCollector,
    compile_candidate_files,
)
from jev_engineering.types import CandidateFile


def test_semantic_gc_drops_stale_invalidated_and_exact_duplicate_content() -> None:
    items = [
        ContextCandidate("a.py", "same", 10, relevance=1.0, information_gain=1.0),
        ContextCandidate("b.py", "same", 10, relevance=0.8, information_gain=0.9),
        ContextCandidate("old.py", "old", 10, relevance=1.0, freshness=0.0),
        ContextCandidate("bad.py", "bad", 10, relevance=1.0, dependencies=("dep:bad",)),
    ]
    result = SemanticGarbageCollector().collect(
        items,
        invalidated_dependencies={"dep:bad"},
    )
    assert [item.key for item in result.kept] == ["a.py"]
    assert result.excluded["b.py"] == "duplicate"
    assert result.excluded["old.py"] == "stale"
    assert result.excluded["bad.py"] == "invalidated_dependency"


def test_context_compiler_respects_budget_and_prefers_utility_density() -> None:
    candidates = [
        ContextCandidate("big.py", "x" * 400, 100, relevance=0.9, information_gain=1.0),
        ContextCandidate("small.py", "y" * 80, 20, relevance=0.95, information_gain=1.0),
        ContextCandidate("medium.py", "z" * 160, 40, relevance=0.8, information_gain=1.0),
    ]
    projection = ContextCompiler().compile(candidates, token_budget=60)
    assert [item.key for item in projection.selected] == ["small.py", "medium.py"]
    assert projection.tokens_used == 60
    assert projection.excluded["big.py"] == "token_budget"
    assert 0.0 < projection.useful_context_ratio <= 1.0


def test_compile_candidate_files_converts_jev_scores_into_bounded_projection() -> None:
    selected = [
        CandidateFile("critical.py", "a" * 800, score=4.0, confidence=0.95),
        CandidateFile("maybe.py", "b" * 800, score=2.0, confidence=0.50),
    ]
    projection = compile_candidate_files(selected, token_budget=250)
    assert projection.token_budget == 250
    assert projection.tokens_used <= 250
    assert projection.selected[0].key == "critical.py"
    rendered = projection.render()
    assert "critical.py" in rendered
    assert "Context utility=" in rendered
