from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .context_compiler import ContextCompiler
from .jev_client import JevClient
from .intelligence_fabric import (
    CompetenceGraph,
    FabricWeights,
    FrontierTokenBudget,
    IntelligenceBid,
    IntelligenceFabric,
)
from .compatible_decisions import OpenAICompatibleDecisionBackend
from .local_decisions import LocalDecisionBackend
from .model_registry import ModelRegistry
from .openai_decisions import OpenAIDecisionBackend
from .providers.factory import LiveProviderFactory
from .shadow_runtime import PromotionRegistry
from .verification_portfolio import (
    VerificationMethod,
    VerificationPortfolioOptimizer,
    VerificationRequirement,
    VerifierCorrelationMatrix,
)


@dataclass(slots=True)
class AppConfig:
    raw: dict[str, Any]
    registry: ModelRegistry
    source_path: Path | None = None

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        source = Path(path).resolve()
        payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise TypeError("Configuration root must be a mapping")
        configured = ModelRegistry.from_dict(payload)

        catalog_cfg = payload.get("catalog") or {}
        catalog_path = catalog_cfg.get("path") if isinstance(catalog_cfg, dict) else None
        catalog_path = catalog_path or payload.get("litellm_catalog")
        if catalog_path:
            resolved = Path(str(catalog_path))
            if not resolved.is_absolute():
                resolved = source.parent / resolved
            catalog = ModelRegistry.from_litellm_catalog(resolved)
            frontier_aliases = []
            if isinstance(catalog_cfg, dict):
                frontier_aliases.extend(catalog_cfg.get("frontier_models") or [])
            frontier_aliases.extend(payload.get("frontier_models") or [])
            catalog = catalog.with_frontier_aliases(frontier_aliases)
            registry = catalog.merged(configured)
        else:
            registry = configured
        return cls(payload, registry, source)

    def decision_backend(self):
        decision = self.raw.get("decision") or self.raw.get("jev") or {}
        backend = str(decision.get("backend") or "jev").casefold()
        if backend in {"local", "heuristic"}:
            return LocalDecisionBackend()
        if backend in {"openai_compatible", "compatible", "chat_completions"}:
            env = str(decision.get("api_key_env") or "DIALAGRAM_API_KEY")
            key = os.environ.get(env, "")
            if not key:
                if bool(decision.get("offline_fallback", False)):
                    return LocalDecisionBackend()
                raise RuntimeError(
                    f"OpenAI-compatible decision backend selected but {env} is not set. "
                    "Set the key or use decision.backend: local for an explicit offline run."
                )
            return OpenAICompatibleDecisionBackend(
                api_key=key,
                base_url=str(decision.get("base_url") or "https://dialagram.me/router/v1"),
                model=str(decision.get("model") or "qwen-3.8-max-thinking"),
                extra=dict(decision.get("request") or {}),
            )
        if backend in {"openai", "chatgpt", "gpt"}:
            env = str(decision.get("api_key_env") or "OPENAI_API_KEY")
            key = os.environ.get(env, "")
            if not key:
                if bool(decision.get("offline_fallback", False)):
                    return LocalDecisionBackend()
                raise RuntimeError(
                    f"OpenAI decision backend selected but {env} is not set. "
                    "Set the key or use decision.backend: local for an explicit offline run."
                )
            return OpenAIDecisionBackend(
                api_key=key,
                base_url=str(decision.get("base_url") or "https://api.openai.com/v1"),
                model=str(decision.get("model") or "gpt-5.6-sol"),
                reasoning_effort=decision.get("reasoning_effort", "high"),
            )
        if backend not in {"jev", "typesafe"}:
            raise ValueError(f"Unknown decision backend {backend!r}")
        env = str(decision.get("api_key_env") or "TYPESAFE_API_KEY")
        key = os.environ.get(env, "")
        if not key:
            if bool(decision.get("offline_fallback", False)):
                return LocalDecisionBackend()
            raise RuntimeError(
                f"Live Jev selected but {env} is not set. "
                "Use decision.backend: local only for an explicit non-Jev offline run."
            )
        return JevClient(
            api_key=key,
            base_url=str(decision.get("base_url") or "https://api.typesafe.ai"),
            model=str(decision.get("model") or "jev-latest"),
        )

    def shadow_decision_backend(self) -> tuple[Any, dict[str, Any]] | None:
        raw = self.raw.get("shadow_decision") or {}
        if not isinstance(raw, dict) or not bool(raw.get("enabled", False)):
            return None
        shadow_cfg = dict(raw)
        shadow_cfg.pop("enabled", None)
        nested = AppConfig(
            raw={"decision": shadow_cfg},
            registry=self.registry,
            source_path=self.source_path,
        )
        backend = nested.decision_backend()
        metadata = {
            "incumbent_strategy": str(raw.get("incumbent_strategy") or "incumbent-control"),
            "candidate_strategy": str(raw.get("candidate_strategy") or "shadow-control"),
            "model": raw.get("model"),
        }
        return backend, metadata


    def provider_factory(self) -> LiveProviderFactory:
        return LiveProviderFactory()


    def intelligence_fabric(self) -> IntelligenceFabric | None:
        raw = self.raw.get("intelligence_fabric") or {}
        if not isinstance(raw, dict) or not bool(raw.get("enabled", False)):
            return None

        budget_raw = raw.get("frontier_budget") or {}
        if not isinstance(budget_raw, dict):
            raise TypeError("intelligence_fabric.frontier_budget must be a mapping")
        budget = FrontierTokenBudget(
            input_limit=int(budget_raw.get("input_tokens", 0) or 0),
            output_limit=int(budget_raw.get("output_tokens", 0) or 0),
        )

        weights_raw = raw.get("weights") or {}
        if not isinstance(weights_raw, dict):
            raise TypeError("intelligence_fabric.weights must be a mapping")
        weights = FabricWeights(
            cost=float(weights_raw.get("cost", 1.0)),
            latency=float(weights_raw.get("latency", 0.0001)),
            uncertainty=float(weights_raw.get("uncertainty", 0.25)),
            risk=float(weights_raw.get("risk", 0.5)),
            frontier_tokens=float(weights_raw.get("frontier_tokens", 0.000001)),
        )

        strategies = raw.get("strategies") or []
        if not isinstance(strategies, list):
            raise TypeError("intelligence_fabric.strategies must be a list")
        bids: list[IntelligenceBid] = []
        for item in strategies:
            if not isinstance(item, dict):
                raise TypeError("each intelligence_fabric strategy must be a mapping")
            strategy_id = str(item.get("id") or "").strip()
            source = str(item.get("source") or "").strip()
            capabilities_raw = item.get("capabilities") or []
            if isinstance(capabilities_raw, str):
                capabilities = (capabilities_raw,)
            else:
                capabilities = tuple(str(v) for v in capabilities_raw)
            metadata = dict(item.get("metadata") or {})
            if item.get("model_alias") is not None:
                metadata["model_alias"] = str(item["model_alias"])
            if isinstance(item.get("competence_key"), dict):
                metadata["competence_key"] = dict(item["competence_key"])
            bids.append(
                IntelligenceBid(
                    strategy_id=strategy_id,
                    source=source,
                    capabilities=capabilities,
                    predicted_vsr=float(item.get("predicted_vsr", 0.0)),
                    estimated_cost_usd=float(item.get("estimated_cost_usd", 0.0)),
                    estimated_latency_ms=float(item.get("estimated_latency_ms", 0.0)),
                    uncertainty=float(item.get("uncertainty", 0.0)),
                    risk=float(item.get("risk", 0.0)),
                    frontier_input_tokens=int(item.get("frontier_input_tokens", 0) or 0),
                    frontier_output_tokens=int(item.get("frontier_output_tokens", 0) or 0),
                    authorized=bool(item.get("authorized", True)),
                    metadata=metadata,
                )
            )
        if not bids:
            raise ValueError("enabled intelligence_fabric requires at least one strategy")
        graph_path_raw = raw.get("competence_graph_path")
        graph_path = Path(str(graph_path_raw)) if graph_path_raw else None
        if graph_path is not None and not graph_path.is_absolute() and self.source_path is not None:
            graph_path = self.source_path.parent / graph_path
        competence_graph = None
        if graph_path is not None:
            competence_graph = CompetenceGraph.load(graph_path) if graph_path.exists() else CompetenceGraph()
        promotion_path_raw = raw.get("promotion_registry_path")
        promotion_path = Path(str(promotion_path_raw)) if promotion_path_raw else None
        if promotion_path is not None and not promotion_path.is_absolute() and self.source_path is not None:
            promotion_path = self.source_path.parent / promotion_path
        promotion_registry = None
        if promotion_path is not None:
            promotion_registry = (
                PromotionRegistry.load(promotion_path)
                if promotion_path.exists()
                else PromotionRegistry(path=promotion_path)
            )
        return IntelligenceFabric(
            bids=bids,
            frontier_budget=budget,
            weights=weights,
            competence_graph=competence_graph,
            competence_graph_path=graph_path,
            promotion_registry=promotion_registry,
        )

    def required_vsr(self, capability: str, *, default: float = 0.0) -> float:
        raw = self.raw.get("intelligence_fabric") or {}
        if not isinstance(raw, dict):
            return float(default)
        required = raw.get("required_vsr") or {}
        if isinstance(required, dict):
            return float(required.get(capability, default))
        return float(default)


    def context_compiler(self) -> tuple[ContextCompiler | None, int]:
        raw = self.raw.get("context_compiler") or {}
        if not isinstance(raw, dict) or not bool(raw.get("enabled", False)):
            return None, 0
        token_budget = int(raw.get("token_budget", 0) or 0)
        if token_budget <= 0:
            raise ValueError("enabled context_compiler requires token_budget > 0")
        return ContextCompiler(), token_budget

    def verification_portfolio(
        self,
    ) -> tuple[VerificationPortfolioOptimizer | None, VerificationRequirement | None]:
        raw = self.raw.get("verification_fabric") or {}
        if not isinstance(raw, dict) or not bool(raw.get("enabled", False)):
            return None, None
        methods_raw = raw.get("methods") or []
        if not isinstance(methods_raw, list) or not methods_raw:
            raise ValueError("enabled verification_fabric requires methods")
        methods: list[VerificationMethod] = []
        for item in methods_raw:
            if not isinstance(item, dict):
                raise TypeError("verification_fabric method must be a mapping")
            methods.append(
                VerificationMethod(
                    method_id=str(item.get("id") or ""),
                    assurance_level=int(item.get("assurance_level", 0)),
                    detection_probability=float(item.get("detection_probability", 0.0)),
                    estimated_cost_usd=float(item.get("estimated_cost_usd", 0.0)),
                    estimated_latency_ms=float(item.get("estimated_latency_ms", 0.0)),
                    command=str(item.get("command") or ""),
                    independent=bool(item.get("independent", False)),
                )
            )
        requirement_raw = raw.get("requirement") or {}
        if not isinstance(requirement_raw, dict):
            raise TypeError("verification_fabric.requirement must be a mapping")
        requirement = VerificationRequirement(
            required_assurance=int(requirement_raw.get("required_assurance", 1)),
            required_detection=float(requirement_raw.get("required_detection", 0.8)),
            defect_probability=float(requirement_raw.get("defect_probability", 0.1)),
            impact_usd=float(requirement_raw.get("impact_usd", 1.0)),
            max_cost_usd=(
                float(requirement_raw["max_cost_usd"])
                if requirement_raw.get("max_cost_usd") is not None
                else None
            ),
        )
        correlations = None
        correlations_raw = raw.get("correlations") or []
        if correlations_raw:
            if not isinstance(correlations_raw, list):
                raise TypeError("verification_fabric.correlations must be a list")
            correlations = VerifierCorrelationMatrix()
            for row in correlations_raw:
                if not isinstance(row, (list, tuple)) or len(row) != 3:
                    raise TypeError("each verifier correlation must be [method_a, method_b, correlation]")
                correlations.set(str(row[0]), str(row[1]), float(row[2]))
        optimizer = VerificationPortfolioOptimizer(
            methods,
            latency_weight=float(raw.get("latency_weight", 0.0)),
            correlations=correlations,
        )
        return optimizer, requirement

    @property
    def runtime(self) -> dict[str, Any]:
        value = self.raw.get("runtime") or {}
        return dict(value) if isinstance(value, dict) else {}


def make_registry(config: dict[str, Any]) -> ModelRegistry:
    """In-memory helper used by tests/embedding applications."""
    configured = ModelRegistry.from_dict(config)
    catalog_path = config.get("litellm_catalog")
    if not catalog_path:
        return configured
    catalog = ModelRegistry.from_litellm_catalog(Path(str(catalog_path)))
    catalog = catalog.with_frontier_aliases(config.get("frontier_models") or [])
    return catalog.merged(configured)


def make_decision_backend(config: dict[str, Any]):
    return AppConfig(raw=config, registry=ModelRegistry.from_dict(config)).decision_backend()
