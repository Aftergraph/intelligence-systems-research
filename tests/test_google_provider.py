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

def test_google_25_flash_disables_thinking_for_bounded_canary(monkeypatch):
    import json
    import providers.google as g
    captured={}
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self):
            return json.dumps({
              "candidates":[{"content":{"parts":[{"text":"AFTERGRAPH_CANARY_OK"}]}}],
              "usageMetadata":{"promptTokenCount":1,"candidatesTokenCount":1,"totalTokenCount":2}
            }).encode()
    def fake(req,timeout=0):
        captured["payload"]=json.loads(req.data.decode())
        return Resp()
    monkeypatch.setattr(g.request,"urlopen",fake)
    p=GoogleProvider(api_key="secret")
    r=p.generate("hello",model="gemini-2.5-flash",max_tokens=32,temperature=0.0)
    assert captured["payload"]["generationConfig"]["thinkingConfig"]["thinkingBudget"]==0
    assert r.content=="AFTERGRAPH_CANARY_OK"
    assert r.is_live is True

def test_google_parser_excludes_thought_parts(monkeypatch):
    import json
    import providers.google as g
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self):
            return json.dumps({
              "candidates":[{"content":{"parts":[
                {"text":"internal summary","thought":True},
                {"text":"AFTERGRAPH_CANARY_OK"}
              ]}}],
              "usageMetadata":{"promptTokenCount":1,"thoughtsTokenCount":4,"candidatesTokenCount":1,"totalTokenCount":6}
            }).encode()
    monkeypatch.setattr(g.request,"urlopen",lambda *a,**k:Resp())
    r=GoogleProvider(api_key="secret").generate("hello",model="gemini-2.5-flash")
    assert r.content=="AFTERGRAPH_CANARY_OK"
