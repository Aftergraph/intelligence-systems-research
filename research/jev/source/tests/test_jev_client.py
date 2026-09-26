from __future__ import annotations

import httpx

from jev_engineering.jev_client import JevClient


def test_system_one_builds_typesafe_request_and_parses_answers() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {
                    "safe": {"type": "noul", "noul": 0.91},
                    "route": {
                        "type": "choice",
                        "choice": "astra",
                        "confidence": 0.8,
                        "probabilities": {"astra": 0.8, "other": 0.2},
                    },
                    "scope": {
                        "type": "score",
                        "score": 2.3,
                        "confidence": 0.7,
                        "legend": {"0": "drop", "1": "maybe", "2": "keep"},
                        "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7},
                    },
                },
                "usage": {"input_tokens": 42, "output_tokens": 0},
            },
        )

    transport = httpx.MockTransport(handler)
    client = JevClient(
        api_key="ts_test",
        base_url="https://api.typesafe.ai",
        model="jev-latest",
        transport=transport,
    )
    result = client.system_one(
        state={"task": "fix tests"},
        questions={
            "safe": {"type": "noul", "instructions": "Safe?"},
            "route": {
                "type": "choice",
                "instructions": "Which model?",
                "criteria": {"astra": "frontier", "other": "other"},
            },
            "scope": {
                "type": "score",
                "instructions": "Relevant?",
                "criteria": ["drop", "maybe", "keep"],
            },
        },
    )

    assert seen["url"] == "https://api.typesafe.ai/v1/systemone"
    assert seen["auth"] == "Bearer ts_test"
    assert '"model":"jev-latest"' in seen["body"].replace(" ", "")
    assert result.noul("safe") == 0.91
    assert result.choice("route").choice == "astra"
    assert result.score("scope").score == 2.3
    assert result.usage.input_tokens == 42
