from __future__ import annotations

import json

import httpx

from jev_engineering.providers.anthropic_messages import AnthropicMessagesProvider
from jev_engineering.providers.google_generate_content import GoogleGenerateContentProvider
from jev_engineering.types import ToolSpec


TOOL = ToolSpec(
    "read_file",
    "Read a file",
    {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
)


def test_anthropic_messages_preserves_tool_use_and_tool_result() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        bodies.append(body)
        if len(bodies) == 1:
            return httpx.Response(
                200,
                json={
                    "content": [
                        {"type": "text", "text": "checking"},
                        {"type": "tool_use", "id": "toolu_1", "name": "read_file", "input": {"path": "a.py"}},
                    ]
                },
            )
        return httpx.Response(200, json={"content": [{"type": "text", "text": "done"}]})

    provider = AnthropicMessagesProvider(
        api_key="test",
        model="claude-opus-5",
        transport=httpx.MockTransport(handler),
    )
    session = provider.start(task="fix", context="a.py", tools=[TOOL], instructions="Use tools")
    first = session.step()
    assert first.tool_calls[0].id == "toolu_1"
    second = session.step({"toolu_1": {"content": "x=1"}})
    assert second.text == "done"
    assert bodies[1]["messages"][-1]["content"][0]["tool_use_id"] == "toolu_1"


def test_google_generate_content_preserves_function_call_id() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        bodies.append(body)
        if len(bodies) == 1:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {
                                        "functionCall": {
                                            "call_id": "gcall_1",
                                            "name": "read_file",
                                            "args": {"path": "a.py"},
                                        },
                                        "thoughtSignature": "opaque-signature",
                                    }
                                ],
                            }
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"role": "model", "parts": [{"text": "done"}]}}]},
        )

    provider = GoogleGenerateContentProvider(
        api_key="test",
        model="gemini-frontier",
        transport=httpx.MockTransport(handler),
    )
    session = provider.start(task="fix", context="a.py", tools=[TOOL], instructions="Use tools")
    first = session.step()
    assert first.tool_calls[0].id == "gcall_1"
    second = session.step({"gcall_1": {"content": "x=1"}})
    assert second.text == "done"
    response_part = bodies[1]["contents"][-1]["parts"][0]["functionResponse"]
    assert response_part["call_id"] == "gcall_1"
    assert response_part["name"] == "read_file"
