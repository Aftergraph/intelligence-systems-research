from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True, slots=True)
class CandidateFile:
    path: str
    excerpt: str
    score: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelProfile:
    alias: str
    provider: str
    model: str
    tier: str = "unclassified"
    transport: str = "openai_compatible"
    base_url: str | None = None
    api_key_env: str | None = None
    context_window: int | None = None
    supports_tools: bool = True
    reasoning_effort: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_frontier(self) -> bool:
        return self.tier.casefold() == "frontier"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    action: str
    destructive_probability: float
    human_probability: float
    reason: str = ""


@dataclass(frozen=True, slots=True)
class DoneVerdict:
    verified: bool
    done_probability: float
    judgeable_probability: float
    reason: str = ""


class AgentStatus(str, Enum):
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    NEEDS_APPROVAL = "needs_human"  # compatibility alias
    UNVERIFIED = "unverified"
    MAX_TURNS = "max_turns"


@dataclass(slots=True)
class AgentResult:
    status: AgentStatus
    trace_id: str
    model_alias: str | None = None
    model: str | None = None
    turns: int = 0
    verification_exit_code: int | None = None
    verification_output: str = ""
    final_text: str = ""
    message: str = ""
    audit_path: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    provider_request_ids: list[str] = field(default_factory=list)
