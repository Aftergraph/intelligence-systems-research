from __future__ import annotations

import json
import httpx
import pytest

from jev_engineering.compatible_decisions import OpenAICompatibleDecisionBackend
from jev_engineering.openai_decisions import OpenAIDecisionError


def _questions():
    return {"done": {"type": "noul", "instructions": "done?"}}


def _valid_payload():
    return {
        "id": "req-good",
        "model": "qwen-test",
        "choices": [{"message": {"tool_calls": [{"function": {
            "name": "submit_decisions",
            "arguments": json.dumps({"answers": {"done": {"type": "noul", "noul": 0.9, "confidence": 0.8}}}),
        }}]}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 5},
    }


def test_malformed_first_response_retries_and_preserves_lineage_and_usage():
    calls=[]
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls)==1:
            return httpx.Response(200,headers={"x-request-id":"req-bad-header"},json={"id":"req-bad","choices":[],"usage":{"prompt_tokens":10,"completion_tokens":2}})
        return httpx.Response(200,headers={"x-request-id":"req-good-header"},json=_valid_payload())
    backend=OpenAICompatibleDecisionBackend(api_key="test",model="qwen-test",base_url="https://example.test/v1",transport=httpx.MockTransport(handler),max_attempts=2)
    response=backend.system_one(state={"x":1},questions=_questions())
    assert len(calls)==2
    assert response.noul("done") == pytest.approx(0.9)
    assert set(response.request_ids)=={"req-bad-header","req-bad","req-good-header","req-good"}
    assert response.usage.input_tokens==30
    assert response.usage.output_tokens==7
    assert response.raw["aftergraph_attempts"]==2


def test_all_malformed_responses_fail_closed_after_bound():
    count=0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count+=1
        return httpx.Response(200,json={"id":f"req-{count}","choices":[]})
    backend=OpenAICompatibleDecisionBackend(api_key="test",model="qwen-test",base_url="https://example.test/v1",transport=httpx.MockTransport(handler),max_attempts=2)
    with pytest.raises(OpenAIDecisionError,match="no assistant message"):
        backend.system_one(state={},questions=_questions())
    assert count==2


def test_nonretryable_4xx_fails_immediately():
    count=0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count+=1
        return httpx.Response(400,json={"error":"bad"})
    backend=OpenAICompatibleDecisionBackend(api_key="test",model="qwen-test",base_url="https://example.test/v1",transport=httpx.MockTransport(handler),max_attempts=2)
    with pytest.raises(OpenAIDecisionError,match="HTTP 400"):
        backend.system_one(state={},questions=_questions())
    assert count==1