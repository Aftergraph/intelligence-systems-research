from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Iterable

from .types import CandidateFile


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    """One candidate context chunk with explicit utility and lifecycle signals."""

    key: str
    text: str
    token_estimate: int
    relevance: float
    information_gain: float = 1.0
    freshness: float = 1.0
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("context candidate key must be non-empty")
        if self.token_estimate <= 0:
            raise ValueError("token_estimate must be positive")
        for name, value in (
            ("relevance", self.relevance),
            ("information_gain", self.information_gain),
            ("freshness", self.freshness),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def content_hash(self) -> str:
        normalized = "\n".join(line.rstrip() for line in self.text.strip().splitlines())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @property
    def utility(self) -> float:
        return float(self.relevance) * float(self.information_gain) * float(self.freshness)

    @property
    def utility_density(self) -> float:
        return self.utility / self.token_estimate


@dataclass(frozen=True, slots=True)
class GarbageCollectionResult:
    kept: tuple[ContextCandidate, ...]
    excluded: dict[str, str]


class SemanticGarbageCollector:
    """Fail-closed lifecycle and exact-redundancy filter for context candidates."""

    def collect(
        self,
        candidates: Iterable[ContextCandidate],
        *,
        invalidated_dependencies: set[str] | None = None,
    ) -> GarbageCollectionResult:
        invalidated_dependencies = invalidated_dependencies or set()
        excluded: dict[str, str] = {}
        best_by_hash: dict[str, ContextCandidate] = {}

        for candidate in candidates:
            if candidate.freshness <= 0.0:
                excluded[candidate.key] = "stale"
                continue
            if any(dep in invalidated_dependencies for dep in candidate.dependencies):
                excluded[candidate.key] = "invalidated_dependency"
                continue
            digest = candidate.content_hash
            incumbent = best_by_hash.get(digest)
            if incumbent is None:
                best_by_hash[digest] = candidate
                continue
            # Exact duplicate chunks are not worth paying context tokens for twice.
            winner, loser = sorted(
                (incumbent, candidate),
                key=lambda item: (item.utility_density, item.utility, item.key),
                reverse=True,
            )
            best_by_hash[digest] = winner
            excluded[loser.key] = "duplicate"

        kept = tuple(
            sorted(
                best_by_hash.values(),
                key=lambda item: (item.utility_density, item.utility, item.key),
                reverse=True,
            )
        )
        return GarbageCollectionResult(kept=kept, excluded=excluded)


@dataclass(frozen=True, slots=True)
class ContextProjection:
    projection_id: str
    selected: tuple[ContextCandidate, ...]
    excluded: dict[str, str]
    token_budget: int
    tokens_used: int
    candidate_tokens: int

    @property
    def useful_context_ratio(self) -> float:
        if self.tokens_used <= 0:
            return 0.0
        weighted = sum(item.token_estimate * item.utility for item in self.selected)
        return max(0.0, min(1.0, weighted / self.tokens_used))

    @property
    def compression_ratio(self) -> float:
        if self.candidate_tokens <= 0:
            return 0.0
        return self.tokens_used / self.candidate_tokens

    def render(self) -> str:
        chunks: list[str] = []
        for item in self.selected:
            chunks.append(
                f"### {item.key} [Context utility={item.utility:.3f}; "
                f"tokens≈{item.token_estimate}; freshness={item.freshness:.2f}]\n{item.text}"
            )
        return "\n\n".join(chunks)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "projection_id": self.projection_id,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "candidate_tokens": self.candidate_tokens,
            "useful_context_ratio": self.useful_context_ratio,
            "compression_ratio": self.compression_ratio,
            "selected": [
                {
                    "key": item.key,
                    "content_hash": item.content_hash,
                    "token_estimate": item.token_estimate,
                    "relevance": item.relevance,
                    "information_gain": item.information_gain,
                    "freshness": item.freshness,
                    "dependencies": list(item.dependencies),
                }
                for item in self.selected
            ],
            "excluded": dict(self.excluded),
        }


class ContextCompiler:
    """Compile a bounded, fresh, non-redundant projection for one model call."""

    def __init__(self, *, garbage_collector: SemanticGarbageCollector | None = None) -> None:
        self.garbage_collector = garbage_collector or SemanticGarbageCollector()

    def compile(
        self,
        candidates: Iterable[ContextCandidate],
        *,
        token_budget: int,
        invalidated_dependencies: set[str] | None = None,
    ) -> ContextProjection:
        if token_budget < 0:
            raise ValueError("token_budget must be non-negative")
        candidate_list = list(candidates)
        candidate_tokens = sum(item.token_estimate for item in candidate_list)
        gc = self.garbage_collector.collect(
            candidate_list,
            invalidated_dependencies=invalidated_dependencies,
        )
        excluded = dict(gc.excluded)
        selected: list[ContextCandidate] = []
        used = 0
        for item in gc.kept:
            if used + item.token_estimate > token_budget:
                excluded[item.key] = "token_budget"
                continue
            selected.append(item)
            used += item.token_estimate

        fingerprint = "|".join(
            [str(token_budget)]
            + [f"{item.key}:{item.content_hash}:{item.token_estimate}" for item in selected]
        )
        projection_id = "ctx_" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]
        return ContextProjection(
            projection_id=projection_id,
            selected=tuple(selected),
            excluded=excluded,
            token_budget=token_budget,
            tokens_used=used,
            candidate_tokens=candidate_tokens,
        )


def estimate_tokens(text: str) -> int:
    # Provider-neutral conservative approximation for planning, never billing evidence.
    return max(1, math.ceil(len(text.encode("utf-8")) / 4))


def compile_candidate_files(
    selected: list[CandidateFile],
    *,
    token_budget: int,
    invalidated_dependencies: set[str] | None = None,
    compiler: ContextCompiler | None = None,
) -> ContextProjection:
    candidates = [
        ContextCandidate(
            key=item.path,
            text=item.excerpt,
            token_estimate=estimate_tokens(item.excerpt),
            relevance=max(0.0, min(1.0, float(item.score) / 4.0)),
            information_gain=max(0.0, min(1.0, 0.5 + (float(item.confidence) * 0.5))),
            freshness=1.0,
            dependencies=(f"file:{item.path}",),
            metadata={"jev_score": item.score, "jev_confidence": item.confidence},
        )
        for item in selected
    ]
    return (compiler or ContextCompiler()).compile(
        candidates,
        token_budget=token_budget,
        invalidated_dependencies=invalidated_dependencies,
    )
