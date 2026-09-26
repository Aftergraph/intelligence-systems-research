from __future__ import annotations

import json
import httpx

from jev_engineering.provider_health import check_dialagram, check_typesafe


def test_typesafe_health_contract_and_redaction() -> None:
    secret = 'secret-type'
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers['authorization'] == f'Bearer {secret}'
        if request.url.path.endswith('/models'):
            return httpx.Response(200, json={'models': [{'id': 'jev-latest'}]})
        body = json.loads(request.content)
        assert body['questions']['continue']['type'] == 'noul'
        return httpx.Response(200, json={'model': 'jev-latest', 'answers': {'continue': {'noul': 0.99}}})
    checks = check_typesafe(api_key=secret, transport=httpx.MockTransport(handler))
    assert [c.ok for c in checks] == [True, True]
    assert secret not in repr([c.to_dict() for c in checks])


def test_dialagram_health_contract_and_redaction() -> None:
    secret = 'secret-diala'
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers['authorization'] == f'Bearer {secret}'
        if request.method == 'GET':
            return httpx.Response(200, json={'data': [{'id': 'qwen-3.8-max-thinking'}]})
        body = json.loads(request.content)
        assert body['model'] == 'qwen-3.8-max-thinking'
        return httpx.Response(200, json={'model': body['model'], 'choices': [{'message': {'content': 'OK'}}]})
    checks = check_dialagram(api_key=secret, transport=httpx.MockTransport(handler))
    assert [c.ok for c in checks] == [True, True]
    assert secret not in repr([c.to_dict() for c in checks])


def test_provider_error_redacts_secret() -> None:
    secret = 'secret-redact-me'
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f'bad token {secret}')
    checks = check_dialagram(api_key=secret, transport=httpx.MockTransport(handler))
    assert checks[0].ok is False
    assert secret not in checks[0].detail
