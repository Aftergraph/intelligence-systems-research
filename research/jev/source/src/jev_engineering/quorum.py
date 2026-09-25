from __future__ import annotations

from dataclasses import dataclass

from .proof_graph import ProofGraph


@dataclass(frozen=True, slots=True)
class QuorumPolicy:
    min_positive: int = 2
    reject_on_negative: bool = True

    def __post_init__(self) -> None:
        if self.min_positive < 1:
            raise ValueError("min_positive must be >= 1")


@dataclass(frozen=True, slots=True)
class QuorumVerdict:
    accepted: bool
    conflict: bool
    positive_verifiers: tuple[str, ...]
    negative_verifiers: tuple[str, ...]


class QuorumVerifier:
    def __init__(self, policy: QuorumPolicy) -> None:
        self.policy = policy

    def evaluate(self, graph: ProofGraph, *, subject: str, predicate: str) -> QuorumVerdict:
        positives: set[str] = set()
        negatives: set[str] = set()
        for claim in graph.claims():
            claim_id = claim.claim_id
            if claim.subject != subject or claim.predicate != predicate or not graph.is_fresh(claim_id):
                continue
            target = positives if claim.verdict else negatives
            target.add(claim.verifier)
        conflict = bool(negatives)
        accepted = len(positives) >= self.policy.min_positive and not (self.policy.reject_on_negative and conflict)
        return QuorumVerdict(accepted, conflict, tuple(sorted(positives)), tuple(sorted(negatives)))
