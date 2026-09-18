import io,json
from urllib import error
from providers.http_failure import provider_error_snapshot
from experiments.live_benchmark.study012_provider_forensics import TARGETS,MAX_CALLS

def test_probe_plan_is_bounded():
 assert len(TARGETS)==3
 assert MAX_CALLS==12

def test_http_failure_snapshot_preserves_status_and_safe_metadata():
 body=json.dumps({"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"quota exceeded"}}).encode()
 exc=error.HTTPError("https://example",429,"Too Many Requests",{"Retry-After":"2","X-RateLimit-Remaining":"0"},io.BytesIO(body))
 out=provider_error_snapshot(exc,"secret")
 assert out["category"]=="HTTP_ERROR"
 assert out["http_status"]==429
 assert out["provider_status"]=="RESOURCE_EXHAUSTED"
 assert out["provider_code"]==429
 assert out["headers"]["retry-after"]=="2"
 assert "secret" not in json.dumps(out)
