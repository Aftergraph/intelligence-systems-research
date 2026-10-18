from __future__ import annotations

from pathlib import Path

from jev_engineering.config import AppConfig
from jev_engineering.providers.factory import LiveProviderFactory
from jev_engineering.types import ModelProfile


ROOT = Path(__file__).resolve().parents[1]


def test_hermes_dialagram_typesafe_profile_has_current_18_model_catalog() -> None:
    cfg = AppConfig.load(ROOT / "configs" / "hermes-dialagram-typesafe.yaml")
    assert len(cfg.registry.models) == 18
    aliases = {m.alias for m in cfg.registry.models}
    assert {
        "qwen-3.8-max-thinking",
        "qwen-3.8-max",
        "qwen-3.8-omni-flash-thinking",
        "qwen-3.8-omni-flash",
        "meta-muse-spark-1.3",
        "qwen-3.7-max-thinking",
        "qwen-3.7-max",
        "qwen-3.7-plus-thinking",
        "xiaomi-mimo-2.5",
        "qwen-3.7-plus",
        "qwen-3.6-max-preview-thinking",
        "qwen-3.6-max-preview",
        "qwen-3.6-plus-thinking",
        "meta-muse-spark-1.2",
        "qwen-3.6-plus",
        "qwen-3.5-plus-thinking",
        "qwen-3.5-plus",
        "qwen-3.5-omni-plus",
    } == aliases
    assert {m.alias for m in cfg.registry.eligible(frontier_required=True)} == {
        "qwen-3.8-max-thinking",
        "qwen-3.8-max",
    }
    decision = cfg.raw["decision"]
    assert decision["backend"] == "typesafe"
    assert decision["api_key_env"] == "TYPESAFE_API_KEY"


def test_dialagram_provider_uses_router_default_and_dedicated_key_env(monkeypatch) -> None:
    monkeypatch.setenv("DIALAGRAM_API_KEY", "nxr-test")
    profile = ModelProfile(
        alias="qwen-3.8-max-thinking",
        provider="dialagram",
        model="qwen-3.8-max-thinking",
        tier="frontier",
        transport="openai_compatible",
    )
    session = LiveProviderFactory().create(
        profile,
        task="probe",
        context="",
        tools=[],
        instructions="Reply concisely.",
    )
    assert session.url == "https://dialagram.me/router/v1/chat/completions"
    assert session.model == "qwen-3.8-max-thinking"
    assert session.client.headers["Authorization"] == "Bearer nxr-test"


def test_every_dialagram_model_uses_openai_compatible_contract(monkeypatch) -> None:
    cfg = AppConfig.load(ROOT / "configs" / "hermes-dialagram-typesafe.yaml")
    monkeypatch.setenv("DIALAGRAM_API_KEY", "nxr-test")
    factory = LiveProviderFactory()
    for profile in cfg.registry.models:
        session = factory.create(
            profile,
            task="contract probe",
            context="",
            tools=[],
            instructions="Reply concisely.",
        )
        assert session.url == "https://dialagram.me/router/v1/chat/completions"
        assert session.model == profile.model
        assert session.client.headers["Authorization"] == "Bearer nxr-test"
