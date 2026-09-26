from __future__ import annotations

from dataclasses import dataclass

from .proof_graph import ProofGraph


@dataclass(frozen=True, slots=True)
class DiversityQuorumPolicy:
    min_positive: int = 2
    min_trust_domains: int = 2
    reject_on_negative: bool = True

    def __post_init__(self) -> None:
        if self.min_positive < 1 or self.min_trust_domains < 1:
            raise ValueError("quorum minima must be >= 1")


@dataclass(frozen=True, slots=True)
class DiversityQuorumVerdict:
    accepted: bool
    conflict: bool
    positive_verifiers: tuple[str, ...]
    positive_trust_domains: tuple[str, ...]
    negative_verifiers: tuple[str, ...]


class DiversityQuorumVerifier:
    """Quorum that requires verifier identity *and* trust-domain diversity.

    Evidence claims declare `metadata.trust_domain`. Claims without a domain can
    still count as verifier votes but cannot satisfy the diversity requirement.
    """

    def __init__(self, policy: DiversityQuorumPolicy) -> None:
        self.policy = policy

    def evaluate(self, graph: ProofGraph, *, subject: str, predicate: str) -> DiversityQuorumVerdict:
        positives: set[str] = set()
        domains: set[str] = set()
        negatives: set[str] = set()
        for claim in graph.claims():
            if claim.subject != subject or claim.predicate != predicate or not graph.is_fresh(claim.claim_id):
                continue
            if claim.verdict:
                positives.add(claim.verifier)
                domain = str(claim.metadata.get("trust_domain") or "").strip()
                if domain:
                    domains.add(domain)
            else:
                negatives.add(claim.verifier)
        conflict = bool(negatives)
        accepted = (
            len(positives) >= self.policy.min_positive
            and len(domains) >= self.policy.min_trust_domains
            and not (self.policy.reject_on_negative and conflict)
        )
        return DiversityQuorumVerdict(
            accepted=accepted,
            conflict=conflict,
            positive_verifiers=tuple(sorted(positives)),
            positive_trust_domains=tuple(sorted(domains)),
            negative_verifiers=tuple(sorted(negatives)),
        )
