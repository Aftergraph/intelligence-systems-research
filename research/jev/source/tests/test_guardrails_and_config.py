from __future__ import annotations

import json
import os

import pytest

from jev_engineering.audit import AuditLog
from jev_engineering.config import make_decision_backend
from jev_engineering.decisions import HeuristicDecisionBackend
from jev_engineering.provider_factory import ProviderConfigurationError, ProviderFactory
from jev_engineering.tools import RepoTools, ToolPolicyError
from jev_engineering.types import ModelProfile


def test_command_environment_does_not_inherit_provider_secrets(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-secret")
    tools = RepoTools(tmp_path, command_mode="full")
    result = tools.run_command(
        "python -c \"import os; print(os.getenv('OPENAI_API_KEY')); print(os.getenv('TYPESAFE_API_KEY'))\""
    )
    assert result["exit_code"] == 0
    assert result["output"].splitlines() == ["None", "None"]


def test_preflight_rejects_catastrophic_command_before_any_model_decision(tmp_path) -> None:
    tools = RepoTools(tmp_path)
    with pytest.raises(ToolPolicyError):
        tools.preflight("run_command", {"command": "rm -rf /"})


def test_audit_redacts_secrets_but_preserves_metric_token_counts(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(path)
    audit.record("x", api_key="abc", authorization="Bearer z", input_tokens=42)
    row = json.loads(path.read_text())
    assert row["api_key"] == "[REDACTED]"
    assert row["authorization"] == "[REDACTED]"
    # Token *counts* are telemetry, not credentials.
    assert row["input_tokens"] == 42


def test_offline_fallback_is_explicit() -> None:
    cfg = {"jev": {"backend": "typesafe", "api_key_env": "MISSING_FOR_TEST", "offline_fallback": True}}
    assert isinstance(make_decision_backend(cfg), HeuristicDecisionBackend)


def test_live_jev_requires_key_without_fallback(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_FOR_TEST", raising=False)
    cfg = {"jev": {"backend": "typesafe", "api_key_env": "MISSING_FOR_TEST", "offline_fallback": False}}
    with pytest.raises(RuntimeError):
        make_decision_backend(cfg)


def test_provider_factory_requires_explicit_key_for_compatible_gateway(monkeypatch) -> None:
    monkeypatch.delenv("NO_KEY", raising=False)
    profile = ModelProfile(
        alias="x", provider="x", model="m", tier="frontier", transport="openai_compatible",
        base_url="https://example.invalid/v1", api_key_env="NO_KEY"
    )
    with pytest.raises(ProviderConfigurationError):
        ProviderFactory().create(profile, task="x", context="", tools=[], instructions="x")


def test_preflight_requires_human_for_external_publish_like_actions(tmp_path) -> None:
    tools = RepoTools(tmp_path, command_mode="full")
    assert tools.preflight("run_command", {"command": "git push origin main"}) == "confirm"


def test_openai_decision_backend_requires_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MISSING_FOR_TEST", raising=False)
    cfg = {
        "decision": {
            "backend": "openai",
            "api_key_env": "OPENAI_MISSING_FOR_TEST",
            "model": "gpt-5.6-sol",
        }
    }
    with pytest.raises(RuntimeError, match="OPENAI_MISSING_FOR_TEST"):
        make_decision_backend(cfg)


def test_openai_decision_backend_configures_gpt_56_sol(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_TEST_KEY", "sk-test")
    cfg = {
        "decision": {
            "backend": "openai",
            "api_key_env": "OPENAI_TEST_KEY",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
        }
    }
    backend = make_decision_backend(cfg)
    assert backend.model == "gpt-5.6-sol"
    assert backend.reasoning_effort == "high"


def test_openai_compatible_decision_backend_configures_dialagram(monkeypatch) -> None:
    monkeypatch.setenv("DIALAGRAM_TEST_KEY", "secret")
    cfg = {
        "decision": {
            "backend": "openai_compatible",
            "api_key_env": "DIALAGRAM_TEST_KEY",
            "base_url": "https://dialagram.me/router/v1",
            "model": "qwen-3.8-max-thinking",
        }
    }
    backend = make_decision_backend(cfg)
    assert backend.model == "qwen-3.8-max-thinking"
    assert backend.base_url == "https://dialagram.me/router/v1"
