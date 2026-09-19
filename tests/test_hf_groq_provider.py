import json
from providers.hf_groq import HFGroqProvider

def test_hf_groq_rejects_unpinned_backend():
 r=HFGroqProvider(api_key="x").generate("p",model="openai/gpt-oss-120b:fastest")
 assert r.is_live is False
 assert r.raw_response["failure"]["category"]=="ROUTING_POLICY"

def test_hf_groq_truthful_success(monkeypatch):
 import providers.hf_groq as m
 class Resp:
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def read(self):return json.dumps({"choices":[{"message":{"content":"HF_GROQ_READY_OK"}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
 monkeypatch.setattr(m.request,"urlopen",lambda *a,**k:Resp())
 r=HFGroqProvider(api_key="x").generate("p",model="openai/gpt-oss-120b:groq")
 assert r.is_live and r.content=="HF_GROQ_READY_OK"
 assert r.raw_response["gateway"]=="huggingface"
 assert r.raw_response["backend"]=="groq"
