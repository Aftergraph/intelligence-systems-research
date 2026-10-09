from pathlib import Path


def test_github_secret_helper_never_embeds_provider_key_shapes() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / 'scripts/install_github_secrets.sh').read_text(encoding='utf-8')
    assert 'gh secret set TYPESAFE_API_KEY' in text
    assert 'gh secret set DIALAGRAM_API_KEY' in text
    assert 'apikey_' not in text
    assert 'dgr_live_' not in text
    assert 'printf' in text
