import json
from providers.byteplus import BytePlusProvider
def test_byteplus_dry_run_never_claims_live():
 assert BytePlusProvider(api_key="x").generate("p",dry_run=True).is_live is False
def test_byteplus_truthful_success(monkeypatch):
 import providers.byteplus as m
 class Resp:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return json.dumps({"choices":[{"message":{"content":"READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=BytePlusProvider(api_key="x").generate("p",model="seed-2-0-lite-260428")
 assert r.is_live and r.content=="READY_OK" and r.total_tokens==2
