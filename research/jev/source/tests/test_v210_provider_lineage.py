from jev_engineering.telemetry import extract_provider_request_id


def test_request_id_normalization_common_shapes():
    assert extract_provider_request_id({"id": "resp_123"}) == "resp_123"
    assert extract_provider_request_id({"responseId": "google-123"}) == "google-123"
    assert extract_provider_request_id({}) is None
