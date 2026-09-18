import json,pytest
from providers.hf_publicai import HuggingFacePublicAIProvider,HF_MODEL
def test_hf_publicai_is_backend_pinned():
 p=HuggingFacePublicAIProvider(api_key="x")
 assert list(p.get_supported_models())==[HF_MODEL]
 with pytest.raises(ValueError,match="unfrozen_hf_backend"):p.generate("p",model="other")
def test_hf_publicai_truthful_success(monkeypatch):
 import providers.hf_publicai as m
 class Resp:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return json.dumps({"choices":[{"message":{"content":"READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=HuggingFacePublicAIProvider(api_key="x").generate("p",model=HF_MODEL)
 assert r.is_live and r.content=="READY_OK"
