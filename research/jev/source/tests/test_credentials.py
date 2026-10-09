import os

from jev_engineering.credentials import load_allowed_env_file


def test_load_allowed_env_file_maps_hermes_dialagram_alias_without_exposing_values(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text(
        'HERMES_CUSTOM_DIALAGRAM_ME_API_KEY=nxr-secret\n'
        'TYPESAFE_API_KEY=ts-secret\n'
        'UNRELATED_SECRET=do-not-load\n'
    )
    monkeypatch.delenv('DIALAGRAM_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('UNRELATED_SECRET', raising=False)
    report = load_allowed_env_file(env_file)
    assert report == {
        'DIALAGRAM_API_KEY': True,
        'TYPESAFE_API_KEY': True,
    }
    assert os.environ['DIALAGRAM_API_KEY'] == 'nxr-secret'
    assert os.environ['TYPESAFE_API_KEY'] == 'ts-secret'
    assert 'UNRELATED_SECRET' not in os.environ
    assert 'nxr-secret' not in repr(report)
    assert 'ts-secret' not in repr(report)


def test_load_allowed_env_file_does_not_override_existing_by_default(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text('DIALAGRAM_API_KEY=new-value\n')
    monkeypatch.setenv('DIALAGRAM_API_KEY', 'existing')
    report = load_allowed_env_file(env_file)
    assert report['DIALAGRAM_API_KEY'] is True
    assert os.environ['DIALAGRAM_API_KEY'] == 'existing'
