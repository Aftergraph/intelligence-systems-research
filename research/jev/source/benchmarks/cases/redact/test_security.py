from security import redact_authorization

def test_redacts_bearer_secret():
    value = redact_authorization("Authorization: Bearer sk-secret_123 and ok")
    assert value == "Authorization: Bearer [REDACTED] and ok"
    assert "secret" not in value

def test_leaves_unrelated_text():
    assert redact_authorization("hello") == "hello"
