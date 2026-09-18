from providers.base import ProviderResponse
from experiments.live_benchmark.study012_full_runner import retryable_failure,retry_delay_seconds,failure_provenance

def R(status=None,category="HTTP_ERROR",headers=None):
 return ProviderResponse(content="",provider="x",model_id="m",is_live=False,raw_response={"failure":{"category":category,"http_status":status,"headers":headers or {}}})

def test_payment_and_auth_failures_never_retry():
 assert retryable_failure(R(402)) is False
 assert retryable_failure(R(401)) is False
 assert retryable_failure(R(403)) is False

def test_transient_failures_retry():
 assert retryable_failure(R(429)) is True
 assert retryable_failure(R(503)) is True
 assert retryable_failure(R(None,"TIMEOUT")) is True

def test_retry_after_is_honored_bounded():
 assert retry_delay_seconds(R(429,headers={"retry-after":"2"}),1)==2
 assert retry_delay_seconds(R(429,headers={"retry-after":"999"}),1)==1
