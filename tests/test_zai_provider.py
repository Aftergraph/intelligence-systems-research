import json
from providers.zai import ZaiProvider
def test_zai_dry_run_never_claims_live():
 assert ZaiProvider(api_key="x").generate("p",dry_run=True).is_live is False
def test_zai_truthful_success(monkeypatch):
 import providers.zai as m
 class Resp:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return json.dumps({"choices":[{"message":{"content":"READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=ZaiProvider(api_key="x").generate("p",model="glm-5.3-flash")
 assert r.is_live and r.content=="READY_OK" and r.total_tokens==2
