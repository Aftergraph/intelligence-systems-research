import re

def slugify(value: str) -> str:
    """Return a lowercase ASCII-ish URL slug with single hyphens."""
    value = value.strip().lower()
    return re.sub(r"[^a-z0-9]+", "", value)
