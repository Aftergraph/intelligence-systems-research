import json
from providers.nvidia import NvidiaProvider
from providers.novita import NovitaProvider

def _fake_response(text="OK"):
 class Resp:
  def __enter__(self): return self
  def __exit__(self,*a): pass
  def read(self): return json.dumps({"choices":[{"message":{"content":text}}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}).encode()
 return Resp()

def test_nvidia_truthful_success(monkeypatch):
 import providers.nvidia as m
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:_fake_response("FORENSIC_OK"))
 r=NvidiaProvider(api_key="x").generate("p",model="nvidia/nemotron-3-ultra-550b-a55b")
 assert r.is_live and r.content=="FORENSIC_OK" and r.total_tokens==3

def test_novita_truthful_success(monkeypatch):
 import providers.novita as m
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:_fake_response("VERIFIED"))
 r=NovitaProvider(api_key="x").generate("p",model="zai-org/glm-5.2")
 assert r.is_live and r.content=="VERIFIED" and r.total_tokens==3

def test_direct_provider_dry_runs_never_claim_live():
 assert NvidiaProvider(api_key="x").generate("p",dry_run=True).is_live is False
 assert NovitaProvider(api_key="x").generate("p",dry_run=True).is_live is False
