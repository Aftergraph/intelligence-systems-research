import json
from providers.opencode_go import OpenCodeGoProvider

def test_opencode_go_dry_run_never_claims_live():
 assert OpenCodeGoProvider(api_key="x").generate("p",dry_run=True).is_live is False

def test_opencode_go_truthful_success(monkeypatch):
 import providers.opencode_go as m
 class Resp:
  def __enter__(self): return self
  def __exit__(self,*a): pass
  def read(self): return json.dumps({"choices":[{"message":{"content":"OPENCODE_GO_READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=OpenCodeGoProvider(api_key="x").generate("p",model="deepseek-v4-flash")
 assert r.is_live and r.content=="OPENCODE_GO_READY_OK" and r.total_tokens==2
