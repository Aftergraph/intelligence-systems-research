from __future__ import annotations

import json

from jev_engineering.model_registry import ModelRegistry


def test_registry_loads_configured_models_and_enforces_frontier() -> None:
    reg = ModelRegistry.from_dict(
        {
            "models": {
                "astra": {
                    "provider": "openai",
                    "model": "gpt-5.6-sol",
                    "tier": "frontier",
                    "transport": "openai_responses",
                },
                "fast": {
                    "provider": "openrouter",
                    "model": "vendor/fast",
                    "tier": "fast",
                    "transport": "openai_compatible",
                },
            }
        }
    )
    assert [m.alias for m in reg.eligible(frontier_required=True)] == ["astra"]


def test_litellm_catalog_import_supports_arbitrary_providers_and_models(tmp_path) -> None:
    catalog = {
        "openai/gpt-5.6-sol": {
            "litellm_provider": "openai",
            "max_input_tokens": 1050000,
            "supports_function_calling": True,
        },
        "anthropic/example-frontier-model": {
            "litellm_provider": "anthropic",
            "max_input_tokens": 1000000,
            "supports_function_calling": True,
        },
        "custom/vendor-model": {
            "litellm_provider": "custom_provider",
            "max_input_tokens": 128000,
        },
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    reg = ModelRegistry.from_litellm_catalog(path)
    assert {m.provider for m in reg.models} == {"openai", "anthropic", "custom_provider"}
    assert len(reg.models) == 3


def test_config_can_merge_full_litellm_catalog_with_explicit_frontier_override(tmp_path) -> None:
    from jev_engineering.config import make_registry

    catalog = {
        "vendor/a": {"litellm_provider": "vendor", "supports_function_calling": True},
        "vendor/b": {"litellm_provider": "vendor", "supports_function_calling": True},
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog))
    reg = make_registry({
        "litellm_catalog": str(path),
        "frontier_models": ["vendor/b"],
        "models": {},
    })
    assert {m.alias for m in reg.models} == {"vendor/a", "vendor/b"}
    assert [m.alias for m in reg.eligible(frontier_required=True)] == ["vendor/b"]


def test_catalog_models_fail_closed_until_explicitly_promoted_frontier() -> None:
    reg = ModelRegistry.from_dict(
        {
            "models": {
                "discovered-model": {
                    "provider": "new-provider",
                    "model": "brand-new-model",
                    "transport": "litellm",
                }
            }
        }
    )
    assert reg.by_alias("discovered-model").tier == "unclassified"
    assert reg.eligible(frontier_required=True) == []
    promoted = reg.with_frontier_aliases(["discovered-model"])
    assert [m.alias for m in promoted.eligible(frontier_required=True)] == ["discovered-model"]
