from providers.openrouter import OpenRouterProvider

def test_openrouter_dry_run_never_claims_live():
 p=OpenRouterProvider(api_key="placeholder")
 r=p.generate("hello",dry_run=True)
 assert r.is_live is False and r.total_tokens==0

def test_openrouter_static_catalog_matches_frozen_ids():
 m=OpenRouterProvider(api_key=None).get_supported_models()
 assert "google/gemma-4-31b-it" in m
 assert "z-ai/glm-5.2" in m

def test_openrouter_failure_never_claims_live(monkeypatch):
 import providers.openrouter as o
 def boom(*a,**k): raise RuntimeError("forced secret")
 monkeypatch.setattr(o.request,"urlopen",boom)
 p=OpenRouterProvider(api_key="secret")
 r=p.generate("hello")
 assert r.is_live is False
 assert "secret" not in str(r.raw_response)
