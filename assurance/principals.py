from dataclasses import dataclass, field
from typing import List, Set

# ponytail: Explicit Logical Assurance Boundary Principals.
# AgentPrincipal is mathematically barred from issuing verification decisions or transitioning to VERIFIED.

@dataclass(frozen=True)
class Principal:
    name: str
    capabilities: Set[str] = field(default_factory=set)

    def has_capability(self, cap: str) -> bool:
        return cap in self.capabilities

# AgentPrincipal: Can propose actions and candidate completions. CANNOT verify.
AgentPrincipal = Principal(
    name="AgentPrincipal",
    capabilities={
        "agent.reasoning",
        "agent.capability_request",
        "agent.candidate_completion"
    }
)

# AssurancePrincipal: Sole authority to evaluate receipts and transition to VERIFIED or RECOVERING.
AssurancePrincipal = Principal(
    name="AssurancePrincipal",
    capabilities={
        "assurance.evaluate",
        "assurance.issue_receipt",
        "mission.transition.verified",
        "mission.transition.recovering"
    }
)
