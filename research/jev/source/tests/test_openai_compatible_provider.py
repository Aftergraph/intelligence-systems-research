from __future__ import annotations

import httpx

from jev_engineering.providers.openai_compatible import OpenAICompatibleProvider
from jev_engineering.types import ToolSpec


def test_openai_compatible_tool_loop() -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        bodies.append(body)
        if len(bodies) == 1:
            return httpx.Response(200, json={"choices": [{"message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"x.py"}'}}]
            }}]})
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "done"}}]})

    provider = OpenAICompatibleProvider(
        api_key="key", model="provider/frontier", base_url="https://gateway.example/v1",
        transport=httpx.MockTransport(handler),
    )
    session = provider.start(
        task="fix", context="x.py", instructions="use tools",
        tools=[ToolSpec("read_file", "read", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})],
    )
    first = session.step()
    assert first.tool_calls[0].name == "read_file"
    second = session.step({"c1": {"content": "ok"}})
    assert second.text == "done"
    assert '"role":"tool"' in bodies[1].replace(" ", "")
