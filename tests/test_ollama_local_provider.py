import json
from providers.ollama_local import OllamaLocalProvider

def test_ollama_local_dry_run_never_claims_live():
    r=OllamaLocalProvider().generate("hello",dry_run=True)
    assert r.is_live is False

def test_ollama_local_payload_disables_thinking(monkeypatch):
    import providers.ollama_local as m
    captured={}
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self):
            return json.dumps({
                "done":True,
                "message":{"role":"assistant","content":"LOCAL_READY_OK"},
                "prompt_eval_count":21,
                "eval_count":4,
                "total_duration":551971500,
            }).encode()
    def fake(req,timeout=0):
        captured["payload"]=json.loads(req.data.decode())
        return Resp()
    monkeypatch.setattr(m.request,"urlopen",fake)
    r=OllamaLocalProvider().generate("p",max_tokens=16,temperature=0.0)
    assert r.is_live is True
    assert r.content=="LOCAL_READY_OK"
    assert captured["payload"]["think"] is False
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"]["temperature"]==0.0
    assert captured["payload"]["options"]["num_predict"]==16
    assert r.total_tokens==25

def test_ollama_local_failure_never_claims_live(monkeypatch):
    import providers.ollama_local as m
    def boom(*a,**k): raise TimeoutError("forced")
    monkeypatch.setattr(m.request,"urlopen",boom)
    r=OllamaLocalProvider().generate("p")
    assert r.is_live is False
    assert r.raw_response["failure"]["category"]=="TIMEOUT"
