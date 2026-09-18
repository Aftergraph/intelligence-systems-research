from providers.google import GoogleProvider

def test_google_dry_run_never_claims_live():
    p=GoogleProvider(api_key="placeholder")
    r=p.generate("hello",dry_run=True)
    assert r.is_live is False
    assert r.total_tokens==0

def test_google_static_catalog_uses_current_frozen_ids():
    p=GoogleProvider(api_key=None)
    models=p.get_supported_models()
    assert "gemini-2.5-flash" in models
    assert "gemini-2.5-pro" in models

def test_google_network_failure_never_claims_live(monkeypatch):
    import providers.google as g
    def boom(*a,**k): raise RuntimeError("forced")
    monkeypatch.setattr(g.request,"urlopen",boom)
    p=GoogleProvider(api_key="secret")
    r=p.generate("hello")
    assert r.is_live is False
    assert "secret" not in str(r.raw_response)
