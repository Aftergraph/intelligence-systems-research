import json
from providers.opencode_zen import OpenCodeZenProvider

def test_zen_mimo_dry_run_never_claims_live():
 assert OpenCodeZenProvider(api_key="x").generate("p",dry_run=True).is_live is False

def test_zen_mimo_truthful_success(monkeypatch):
 import providers.opencode_zen as m
 class Resp:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return json.dumps({"choices":[{"message":{"content":"ZEN_MIMO_READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=OpenCodeZenProvider(api_key="x").generate("p",model="mimo-v2.5-free")
 assert r.is_live and r.content=="ZEN_MIMO_READY_OK" and r.total_tokens==2
