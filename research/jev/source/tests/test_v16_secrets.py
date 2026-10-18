from __future__ import annotations

import os
from pathlib import Path

import pytest

from jev_engineering.secrets import SecretResolver, secret_fingerprint, write_private_env


def test_secret_resolver_prefers_process_env(monkeypatch, tmp_path: Path) -> None:
    p = tmp_path / '.env'
    p.write_text('DIALAGRAM_API_KEY=file-value\nTYPESAFE_API_KEY=file-type\n', encoding='utf-8')
    monkeypatch.setenv('DIALAGRAM_API_KEY', 'process-value')
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    resolver = SecretResolver(env_file=p)
    assert resolver.get('DIALAGRAM_API_KEY') == 'process-value'
    assert resolver.get('TYPESAFE_API_KEY') == 'file-type'
    assert resolver.status('DIALAGRAM_API_KEY').source == 'process_env'


def test_secret_status_never_returns_secret(monkeypatch) -> None:
    monkeypatch.setenv('TYPESAFE_API_KEY', 'super-secret-value')
    payload = SecretResolver().status('TYPESAFE_API_KEY', include_fingerprint=True).to_dict()
    assert 'super-secret-value' not in repr(payload)
    assert payload['fingerprint'] == secret_fingerprint('super-secret-value')


def test_hermes_alias_maps_to_canonical(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv('DIALAGRAM_API_KEY', raising=False)
    p = tmp_path / '.env'
    p.write_text('HERMES_CUSTOM_DIALAGRAM_ME_API_KEY=abc123\n', encoding='utf-8')
    resolver = SecretResolver(env_file=p)
    assert resolver.get('DIALAGRAM_API_KEY') == 'abc123'


def test_write_private_env_owner_only(tmp_path: Path) -> None:
    p = write_private_env(tmp_path / 'secrets.env', {'TYPESAFE_API_KEY': 'one', 'DIALAGRAM_API_KEY': 'two'})
    mode = p.stat().st_mode & 0o777
    assert mode == 0o600
    assert 'TYPESAFE_API_KEY=one' in p.read_text()


def test_unknown_secret_is_rejected() -> None:
    with pytest.raises(KeyError):
        SecretResolver().get('NOT_ALLOWED')
