from __future__ import annotations

import copy
import sys
from types import SimpleNamespace

from jev_engineering.providers.litellm_bridge import LiteLLMProvider
from jev_engineering.types import ToolSpec


class _Message:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def model_dump(self) -> dict:
        return dict(self.payload)


def test_litellm_bridge_is_model_id_driven_and_preserves_tool_results(monkeypatch) -> None:
    calls: list[dict] = []

    def completion(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        if len(calls) == 1:
            message = _Message(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "dynamic-call-1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"a.py"}',
                            },
                        }
                    ],
                }
            )
        else:
            message = _Message({"role": "assistant", "content": "done"})
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=completion))
    provider = LiteLLMProvider(model="arbitrary-provider/arbitrary-frontier-model")
    session = provider.start(
        task="fix",
        context="a.py",
        instructions="use tools",
        tools=[
            ToolSpec(
                "read_file",
                "read",
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            )
        ],
    )
    first = session.step()
    assert first.tool_calls[0].id == "dynamic-call-1"
    assert calls[0]["model"] == "arbitrary-provider/arbitrary-frontier-model"
    second = session.step({"dynamic-call-1": {"content": "x = 1"}})
    assert second.text == "done"
    assert calls[1]["messages"][-1]["role"] == "tool"
    assert calls[1]["messages"][-1]["tool_call_id"] == "dynamic-call-1"
