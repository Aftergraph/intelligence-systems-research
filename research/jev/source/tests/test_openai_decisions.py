from __future__ import annotations

import json

import httpx
import pytest

from jev_engineering.openai_decisions import OpenAIDecisionBackend, OpenAIDecisionError


def test_openai_decision_backend_forces_typed_submit_function() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        body = json.loads(request.read())
        seen["body"] = body
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.6-sol",
                "output": [
                    {
                        "type": "function_call",
                        "name": "submit_decisions",
                        "call_id": "call_decide",
                        "arguments": json.dumps(
                            {
                                "answers": {
                                    "route": {
                                        "type": "choice",
                                        "choice": "sol",
                                        "confidence": 0.93,
                                    },
                                    "risk": {
                                        "type": "noul",
                                        "noul": 0.08,
                                        "confidence": 0.88,
                                    },
                                    "scope": {
                                        "type": "score",
                                        "score": 3.8,
                                        "confidence": 0.91,
                                    },
                                }
                            }
                        ),
                    }
                ],
                "usage": {"input_tokens": 123, "output_tokens": 45},
            },
        )

    backend = OpenAIDecisionBackend(
        api_key="sk-test",
        model="gpt-5.6-sol",
        reasoning_effort="high",
        transport=httpx.MockTransport(handler),
    )
    result = backend.system_one(
        state={"task": "fix the bug"},
        questions={
            "route": {
                "type": "choice",
                "instructions": "Pick a model",
                "criteria": {"sol": "frontier", "other": "fallback"},
            },
            "risk": {"type": "noul", "instructions": "Is this destructive?"},
            "scope": {
                "type": "score",
                "instructions": "How relevant?",
                "criteria": ["none", "weak", "useful", "strong", "essential"],
            },
        },
    )

    assert seen["url"] == "https://api.openai.com/v1/responses"
    assert seen["auth"] == "Bearer sk-test"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-5.6-sol"
    assert body["reasoning"] == {"effort": "high"}
    assert body["tool_choice"] == {"type": "function", "name": "submit_decisions"}
    assert body["parallel_tool_calls"] is False
    assert body["tools"][0]["strict"] is True
    params = body["tools"][0]["parameters"]
    assert params["required"] == ["answers"]
    assert set(params["properties"]["answers"]["required"]) == {"route", "risk", "scope"}
    assert result.choice("route").choice == "sol"
    assert result.noul("risk") == 0.08
    assert result.score("scope").score == 3.8
    assert result.usage.input_tokens == 123
    assert result.usage.output_tokens == 45


def test_openai_decision_backend_rejects_ineligible_choice() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.6-sol",
                "output": [
                    {
                        "type": "function_call",
                        "name": "submit_decisions",
                        "arguments": json.dumps(
                            {
                                "answers": {
                                    "route": {
                                        "type": "choice",
                                        "choice": "invented-model",
                                        "confidence": 1.0,
                                    }
                                }
                            }
                        ),
                    }
                ],
            },
        )

    backend = OpenAIDecisionBackend(
        api_key="sk-test",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(OpenAIDecisionError, match="outside configured criteria"):
        backend.system_one(
            state={},
            questions={
                "route": {
                    "type": "choice",
                    "instructions": "Pick",
                    "criteria": {"sol": "frontier"},
                }
            },
        )
