import json

import httpx

from jev_engineering.compatible_decisions import OpenAICompatibleDecisionBackend


def test_openai_compatible_decisions_forces_typed_tool_and_parses_usage():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['path'] = request.url.path
        body = json.loads(request.content)
        seen['body'] = body
        return httpx.Response(
            200,
            json={
                'model': 'qwen-3.8-max-thinking',
                'choices': [{
                    'message': {
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': [{
                            'id': 'call-1',
                            'type': 'function',
                            'function': {
                                'name': 'submit_decisions',
                                'arguments': json.dumps({
                                    'answers': {
                                        'risk': {'type': 'noul', 'noul': 0.07, 'confidence': 0.91},
                                        'route': {'type': 'choice', 'choice': 'a', 'confidence': 0.88},
                                    }
                                }),
                            },
                        }],
                    }
                }],
                'usage': {'prompt_tokens': 120, 'completion_tokens': 18},
            },
        )

    backend = OpenAICompatibleDecisionBackend(
        api_key='secret',
        model='qwen-3.8-max-thinking',
        base_url='https://dialagram.me/router/v1',
        transport=httpx.MockTransport(handler),
    )
    response = backend.system_one(
        state={'task': 'x'},
        questions={
            'risk': {'type': 'noul', 'instructions': 'risk?'},
            'route': {'type': 'choice', 'instructions': 'pick', 'criteria': {'a': 'A', 'b': 'B'}},
        },
    )

    assert seen['path'] == '/router/v1/chat/completions'
    assert seen['body']['tool_choice']['function']['name'] == 'submit_decisions'
    assert response.noul('risk') == 0.07
    assert response.choice('route').choice == 'a'
    assert response.usage.input_tokens == 120
    assert response.usage.output_tokens == 18


def test_openai_compatible_decisions_rejects_ineligible_choice():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                'choices': [{
                    'message': {
                        'tool_calls': [{
                            'id': 'call-1',
                            'type': 'function',
                            'function': {
                                'name': 'submit_decisions',
                                'arguments': json.dumps({
                                    'answers': {'route': {'type': 'choice', 'choice': 'evil', 'confidence': 1.0}}
                                }),
                            },
                        }]
                    }
                }]
            },
        )

    backend = OpenAICompatibleDecisionBackend(
        api_key='secret',
        model='qwen-3.8-max-thinking',
        base_url='https://dialagram.me/router/v1',
        transport=httpx.MockTransport(handler),
    )
    try:
        backend.system_one(
            state={},
            questions={'route': {'type': 'choice', 'criteria': {'a': 'A', 'b': 'B'}}},
        )
    except Exception as exc:
        assert 'outside configured criteria' in str(exc).lower()
    else:
        raise AssertionError('expected invalid choice to fail closed')
