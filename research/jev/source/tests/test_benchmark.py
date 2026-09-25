from jev_engineering.benchmark import aggregate_records


def test_aggregate_records_reports_vsr_fcr_and_weighted_control_tax():
    records = [
        {
            'condition': 'jev', 'case_id': 'a', 'status': 'verified',
            'metrics': {
                'provider_input_tokens': 100, 'provider_output_tokens': 20,
                'decision_input_tokens': 10, 'decision_output_tokens': 2,
                'completion_claims': 1, 'false_completion_claims': 0,
                'wall_time_ms': 1000, 'provider_latency_ms': 700,
                'verification_latency_ms': 100,
            },
        },
        {
            'condition': 'jev', 'case_id': 'b', 'status': 'failed',
            'metrics': {
                'provider_input_tokens': 200, 'provider_output_tokens': 40,
                'decision_input_tokens': 20, 'decision_output_tokens': 4,
                'completion_claims': 2, 'false_completion_claims': 1,
                'wall_time_ms': 3000, 'provider_latency_ms': 2100,
                'verification_latency_ms': 200,
            },
        },
    ]
    summary = aggregate_records(records)['jev']
    assert summary['missions'] == 2
    assert summary['verified'] == 1
    assert summary['vsr'] == 0.5
    assert summary['fcr'] == 1 / 3
    assert summary['provider_tokens'] == 360
    assert summary['decision_tokens'] == 36
    assert summary['control_plane_token_tax'] == 36 / 396
    assert summary['p50_wall_time_ms'] == 2000


def test_preflight_manifest_enforces_same_generator_and_reports_missing_keys(tmp_path, monkeypatch):
    from jev_engineering.benchmark import preflight_manifest

    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "a.yaml").write_text('''
decision:
  backend: typesafe
  api_key_env: TYPESAFE_TEST
models:
  qwen:
    provider: dialagram
    model: qwen-3.8-max-thinking
    tier: frontier
    transport: openai_compatible
    base_url: https://dialagram.me/router/v1
    api_key_env: DIALAGRAM_TEST
''')
    (configs / "b.yaml").write_text('''
decision:
  backend: openai_compatible
  api_key_env: DIALAGRAM_TEST
  base_url: https://dialagram.me/router/v1
  model: qwen-3.8-max-thinking
models:
  qwen:
    provider: dialagram
    model: qwen-3.8-max-thinking
    tier: frontier
    transport: openai_compatible
    base_url: https://dialagram.me/router/v1
    api_key_env: DIALAGRAM_TEST
''')
    case = tmp_path / "case"
    case.mkdir()
    (case / "test_x.py").write_text("def test_x(): assert False\n")
    manifest = tmp_path / "bench.yaml"
    manifest.write_text('''
version: 1
conditions:
  - id: jev
    config: configs/a.yaml
  - id: frontier
    config: configs/b.yaml
cases:
  - id: x
    source: case
    task: fix x
    verify: python -m pytest -q
''')
    monkeypatch.delenv("TYPESAFE_TEST", raising=False)
    monkeypatch.delenv("DIALAGRAM_TEST", raising=False)
    report = preflight_manifest(manifest)
    assert report["generator_invariant"] is True
    assert report["missing_env"] == ["DIALAGRAM_TEST", "TYPESAFE_TEST"]


def test_run_manifest_fails_closed_before_live_calls_when_credentials_missing(tmp_path, monkeypatch):
    import pytest
    from jev_engineering.benchmark import run_manifest

    configs = tmp_path / "configs"
    configs.mkdir()
    config_text = '''
decision:
  backend: typesafe
  api_key_env: TYPESAFE_TEST
models:
  qwen:
    provider: dialagram
    model: qwen-3.8-max-thinking
    tier: frontier
    transport: openai_compatible
    base_url: https://dialagram.me/router/v1
    api_key_env: DIALAGRAM_TEST
'''
    (configs / "a.yaml").write_text(config_text)
    case = tmp_path / "case"; case.mkdir()
    (case / "test_x.py").write_text("def test_x(): assert False\n")
    manifest = tmp_path / "bench.yaml"
    manifest.write_text('''
version: 1
conditions:
  - id: jev
    config: configs/a.yaml
cases:
  - id: x
    source: case
    task: fix x
    verify: python -m pytest -q
''')
    monkeypatch.delenv("TYPESAFE_TEST", raising=False)
    monkeypatch.delenv("DIALAGRAM_TEST", raising=False)
    with pytest.raises(RuntimeError, match="missing environment credentials"):
        run_manifest(manifest, output_dir=tmp_path / "out")
    assert not (tmp_path / "out" / "results.jsonl").exists()
