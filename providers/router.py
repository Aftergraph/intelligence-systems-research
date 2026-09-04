import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from providers.base import ModelProvider, ModelMetadata, ProviderResponse, RoutingReceipt
from providers.dialagram import DialagramProvider
from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.google import GoogleProvider
from providers.openrouter import OpenRouterProvider, LocalProvider

# ponytail: Policy-Constrained Scored Router.
# Evaluates hard constraints -> policy filter -> multi-dimensional scoring -> generates durable RoutingReceipt.

class ModelRouter:
    def __init__(self, trajectory_recorder=None):
        self.trajectory_recorder = trajectory_recorder
        self.providers: Dict[str, ModelProvider] = {
            "dialagram": DialagramProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "google": GoogleProvider(),
            "openrouter": OpenRouterProvider(),
            "local": LocalProvider()
        }
        self.primary_provider = "dialagram"
        self.fallback_chain = ["dialagram", "anthropic", "openai", "local"]

    def register_provider(self, name: str, provider: ModelProvider):
        self.providers[name] = provider

    def route_request(
        self,
        mission_id: str,
        run_id: Optional[str] = None,
        requested_capabilities: Optional[List[str]] = None,
        requires_reasoning: bool = False,
        requires_tools: bool = True,
        preferred_provider: Optional[str] = None,
        disallowed_providers: Optional[List[str]] = None
    ) -> Tuple[str, str, RoutingReceipt]:
        """Executes Policy-Constrained Scored Routing and produces a durable RoutingReceipt."""
        req_caps = requested_capabilities or (["tools"] if requires_tools else [])
        disallowed = set(disallowed_providers or [])
        active_run_id = run_id or f"run-{mission_id[:8]}"

        all_candidates = []
        rejected = {}
        eligible = []
        score_breakdown = {}

        # 1. Harvest candidates
        for prov_name, provider in self.providers.items():
            if prov_name in disallowed:
                rejected[prov_name] = "Disallowed by security/data privacy policy"
                continue
            models = provider.get_supported_models()
            for m_id, meta in models.items():
                full_id = f"{prov_name}:{m_id}"
                all_candidates.append(full_id)

                # Hard constraints
                if requires_tools and not meta.supports_tools:
                    rejected[full_id] = "Does not support tool calls"
                    continue
                if requires_reasoning and not meta.supports_reasoning:
                    rejected[full_id] = "Does not support extended reasoning"
                    continue

                eligible.append(full_id)

                # 2. Multi-dimensional Scoring
                # Dimensions: reasoning (0-10), tools (0-10), context capacity (0-10), cost efficiency (0-10)
                reasoning_score = 10.0 if meta.supports_reasoning else 5.0
                tools_score = 10.0 if meta.supports_tools else 2.0
                context_score = min(10.0, meta.context_window / 25000.0)
                cost_score = 10.0 if meta.pricing_per_million_input == 0.0 else max(1.0, 10.0 - (meta.pricing_per_million_input / 2.0))

                # Preference bonus
                pref_bonus = 5.0 if prov_name == preferred_provider else 0.0

                total_score = (reasoning_score * 0.3) + (tools_score * 0.3) + (context_score * 0.2) + (cost_score * 0.2) + pref_bonus
                score_breakdown[full_id] = {
                    "reasoning": reasoning_score,
                    "tools": tools_score,
                    "context": context_score,
                    "cost_efficiency": cost_score,
                    "preference_bonus": pref_bonus,
                    "total": round(total_score, 2)
                }

        # 3. Selection
        if eligible:
            eligible.sort(key=lambda x: score_breakdown[x]["total"], reverse=True)
            selected_full = eligible[0]
            selected_prov, selected_m = selected_full.split(":", 1)
        else:
            # Fallback to default
            selected_prov = "dialagram"
            selected_m = "qwen-3.8-max"

        receipt = RoutingReceipt(
            receipt_id=f"rt-{uuid.uuid4().hex[:12]}",
            mission_id=mission_id,
            run_id=active_run_id,
            requested_capabilities=req_caps,
            candidate_models=all_candidates,
            rejected_candidates=rejected,
            eligible_candidates=eligible,
            score_breakdown=score_breakdown,
            selected_provider=selected_prov,
            selected_model=selected_m,
            budget_state={"status": "VALID"},
            policy_state="CONSTRAINTS_EVALUATED",
            catalog_snapshot_version="Q3-2026-v2.0"
        )

        if self.trajectory_recorder:
            self.trajectory_recorder.emit_event("POLICY_CONSTRAINED_ROUTING_DECISION", receipt.to_dict())

        return selected_prov, selected_m, receipt

    def resolve_model(
        self,
        requires_reasoning: bool = False,
        requires_tools: bool = True,
        max_cost_usd: Optional[float] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[str, str]:
        """Backward-compatible wrapper for route_request."""
        prov, model, _ = self.route_request(
            mission_id="m-compat",
            requires_reasoning=requires_reasoning,
            requires_tools=requires_tools,
            preferred_provider=preferred_provider
        )
        return prov, model

    def generate_with_fallback(
        self,
        prompt: str,
        system_prompt: str = "",
        model_id: Optional[str] = None,
        provider_name: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = False
    ) -> ProviderResponse:
        """Executes generation with automatic multi-provider fallback and provenance logging."""
        chain = list(self.fallback_chain)
        if provider_name and provider_name in chain:
            chain.remove(provider_name)
            chain.insert(0, provider_name)

        last_error = None
        for prov_key in chain:
            prov = self.providers.get(prov_key)
            if not prov:
                continue
            try:
                resp = prov.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model_id if prov_key == provider_name else None,
                    tools=tools,
                    dry_run=dry_run
                )
                if "[Dialagram Live Error" in resp.content or (resp.raw_response and "error" in resp.raw_response):
                    raise RuntimeError(f"Provider {prov_key} returned error: {resp.content}")

                if prov_key != chain[0] and self.trajectory_recorder:
                    self.trajectory_recorder.emit_event("PROVIDER_FALLBACK_TRIGGERED", {
                        "failed_provider": chain[0],
                        "active_provider": prov_key,
                        "model": resp.model_id,
                        "reason": str(last_error) if last_error else "automatic_fallback"
                    })
                return resp
            except Exception as e:
                last_error = e
                if self.trajectory_recorder:
                    self.trajectory_recorder.emit_event("PROVIDER_FAILURE", {
                        "provider": prov_key,
                        "error": str(e)
                    })

        return ProviderResponse(
            content=f"[Router Failure: All providers in fallback chain failed. Last error: {last_error}]",
            prompt_tokens=len(prompt.split()),
            completion_tokens=10,
            total_tokens=len(prompt.split()) + 10,
            cost_usd=0.0,
            latency_ms=10.0,
            provider="fallback",
            model_id="offline_stub",
            is_live=False
        )
