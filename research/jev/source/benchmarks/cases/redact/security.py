import re

def redact_authorization(text: str) -> str:
    """Redact Bearer credentials from arbitrary log text."""
    return re.sub(r"Bearer\\s+([A-Za-z0-9._-]+)", r"Bearer \\1", text)
