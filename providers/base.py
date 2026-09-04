from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

# ponytail: Core vendor-neutral abstractions for model providers and routing.
# Enforces truthful provider statuses: LIVE_VERIFIED, LIVE_CAPABLE_UNVERIFIED, STUB, MOCK, etc.

VALID_PROVIDER_STATUSES = {
    "LIVE_VERIFIED",
    "LIVE_CAPABLE_UNVERIFIED",
    "STUB",
    "MOCK",
    "LOCAL",
    "DISABLED",
    "DEPRECATED"
}

@dataclass
class ModelMetadata:
    provider: str
    model_id: str
    context_window: int = 128000
    supports_tools: bool = True
    supports_reasoning: bool = False
    multimodality: bool = False
    pricing_per_million_input: float = 0.0
    pricing_per_million_output: float = 0.0
    availability: str = "ACTIVE"
    operational_status: str = "LIVE_CAPABLE_UNVERIFIED"
    source: str = "provider_catalog"
    observed_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    deprecation_date: Optional[str] = None
    provider_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProviderResponse:
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    provider: str = ""
    model_id: str = ""
    is_live: bool = False  # MUST ONLY be True when a real external network call succeeded!
    raw_response: Optional[Dict[str, Any]] = None

@dataclass
class RoutingReceipt:
    receipt_id: str
    mission_id: str
    run_id: str
    requested_capabilities: List[str]
    candidate_models: List[str]
    rejected_candidates: Dict[str, str]  # model_id -> rejection reason
    eligible_candidates: List[str]
    score_breakdown: Dict[str, Dict[str, float]]  # model_id -> {dimension: score}
    selected_provider: str
    selected_model: str
    budget_state: Dict[str, Any]
    policy_state: str
    fallback_reason: Optional[str] = None
    catalog_snapshot_version: str = "Q3-2026-v2.0"
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "requested_capabilities": self.requested_capabilities,
            "candidate_models": self.candidate_models,
            "rejected_candidates": self.rejected_candidates,
            "eligible_candidates": self.eligible_candidates,
            "score_breakdown": self.score_breakdown,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "budget_state": self.budget_state,
            "policy_state": self.policy_state,
            "fallback_reason": self.fallback_reason,
            "catalog_snapshot_version": self.catalog_snapshot_version,
            "timestamp": self.timestamp
        }

class ModelProvider(ABC):
    def __init__(self, provider_name: str, default_model: str, initial_status: str = "LIVE_CAPABLE_UNVERIFIED"):
        self.provider_name = provider_name
        self.default_model = default_model
        assert initial_status in VALID_PROVIDER_STATUSES
        self.operational_status = initial_status

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        dry_run: bool = False
    ) -> ProviderResponse:
        """Generates completion or tool calls from the model."""
        pass

    @abstractmethod
    def get_supported_models(self) -> Dict[str, ModelMetadata]:
        """Returns catalog of supported models."""
        pass

    def discover_models(self) -> Dict[str, ModelMetadata]:
        """Discovers models dynamically from provider endpoint, falling back to static snapshot."""
        return self.get_supported_models()
