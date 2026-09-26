from __future__ import annotations

import httpx

from jev_engineering.providers.openai_responses import OpenAIResponsesProvider
from jev_engineering.types import ToolSpec


TOOLS = [
    ToolSpec(
        name="read_file",
        description="Read a file",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )
]


def test_openai_responses_provider_parses_function_calls_and_continues() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        calls.append(body)
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "id": "resp_1",
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "read_file",
                            "arguments": '{"path":"a.py"}',
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "resp_2",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "done"}],
                    }
                ],
            },
        )

    provider = OpenAIResponsesProvider(
        api_key="sk-test",
        model="gpt-5.6-sol",
        transport=httpx.MockTransport(handler),
    )
    session = provider.start(
        task="fix it",
        context="a.py candidate",
        tools=TOOLS,
        instructions="Use tools.",
    )
    turn1 = session.step()
    assert turn1.tool_calls[0].name == "read_file"
    turn2 = session.step({"call_1": {"content": "x = 1"}})
    assert turn2.text == "done"
    assert '"type":"function_call_output"' in calls[1].replace(" ", "")
