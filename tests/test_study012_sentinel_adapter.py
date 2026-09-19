import hashlib,json,subprocess
from pathlib import Path
from experiments.live_benchmark.study012_sentinel_adapter import verify_checkout,verify_research_envelope,PINNED_SENTINEL_COMMIT

def test_adapter_is_exact_commit_pinned(tmp_path,monkeypatch):
 (tmp_path/"bin").mkdir(); (tmp_path/"bin"/"sentinel-research-verify.js").write_text("")
 class P: stdout=PINNED_SENTINEL_COMMIT+"\n"
 monkeypatch.setattr(subprocess,"run",lambda *a,**k:P())
 assert verify_checkout(tmp_path)==(True,None)

def test_adapter_rejects_commit_drift(tmp_path,monkeypatch):
 (tmp_path/"bin").mkdir(); (tmp_path/"bin"/"sentinel-research-verify.js").write_text("")
 class P: stdout="0"*40+"\n"
 monkeypatch.setattr(subprocess,"run",lambda *a,**k:P())
 assert verify_checkout(tmp_path)==(False,"sentinel_commit_mismatch")
