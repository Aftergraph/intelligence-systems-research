from __future__ import annotations
import json
import httpx
from jev_engineering.jev_client import JevClient


def test_typesafe_specific_request_header_is_captured():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        return httpx.Response(
            200,
            headers={"x-typesafe-request-id": "ts-req-216"},
            json={"model":"jev-1.13.0","answers":{"q":{"type":"noul","noul":0.5,"confidence":1.0}},"usage":{}},
        )
    with JevClient(api_key="dummy", transport=httpx.MockTransport(handler)) as client:
        response = client.system_one(
            state={"x":1},
            questions={"q":{"type":"noul","instructions":"test"}},
        )
    assert response.request_ids == ("ts-req-216",)