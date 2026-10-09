from jev_engineering.decisions import DecisionEngine
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.telemetry import TokenUsage, extract_token_usage


def test_extract_token_usage_normalizes_openai_compatible_and_cached_tokens():
    usage = extract_token_usage({
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 20,
            'prompt_tokens_details': {'cached_tokens': 60},
        }
    })
    assert usage == TokenUsage(input_tokens=100, output_tokens=20, cached_input_tokens=60)


def test_extract_token_usage_normalizes_responses_and_anthropic_and_google():
    assert extract_token_usage({'usage': {'input_tokens': 80, 'output_tokens': 10, 'input_tokens_details': {'cached_tokens': 40}}}) == TokenUsage(80, 10, 40)
    assert extract_token_usage({'usage': {'input_tokens': 70, 'output_tokens': 9, 'cache_read_input_tokens': 30}}) == TokenUsage(70, 9, 30)
    assert extract_token_usage({'usageMetadata': {'promptTokenCount': 55, 'candidatesTokenCount': 7, 'cachedContentTokenCount': 22}}) == TokenUsage(55, 7, 22)


def test_decision_engine_accumulates_typed_decision_usage():
    backend = ScriptedDecisionBackend([
        {
            'model': 'jev-test',
            'usage': {'input_tokens': 25, 'output_tokens': 3},
            'answers': {'looping': {'type': 'noul', 'noul': 0.2}},
        }
    ])
    engine = DecisionEngine(backend)
    assert engine.loop_probability(task='x', recent_actions=['a']) == 0.2
    metrics = engine.telemetry()
    assert metrics['calls'] == 1
    assert metrics['input_tokens'] == 25
    assert metrics['output_tokens'] == 3
    assert metrics['latency_ms'] >= 0
