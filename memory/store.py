import re
from typing import Any, Dict, List, Optional

class MemoryPolicy:
    def __init__(self, sanitize_secrets: bool = True):
        self.sanitize_secrets = sanitize_secrets
        self.secret_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{20,}"),
            re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
            re.compile(r"dgr_live_[a-zA-Z0-9]{20,}"),
            re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}")
        ]

    def sanitize(self, text: str) -> str:
        if not self.sanitize_secrets:
            return text
        sanitized = text
        for pat in self.secret_patterns:
            sanitized = pat.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

class MemoryStore:
    def __init__(self, policy: Optional[MemoryPolicy] = None):
        self.policy = policy or MemoryPolicy()
        self._working_memory: Dict[str, Any] = {}
        self._persistent_facts: List[Dict[str, Any]] = []

    def set_working(self, key: str, value: Any):
        if isinstance(value, str):
            value = self.policy.sanitize(value)
        self._working_memory[key] = value

    def get_working(self, key: str, default: Any = None) -> Any:
        return self._working_memory.get(key, default)

    def add_fact(self, fact: str, source: str = "agent"):
        clean_fact = self.policy.sanitize(fact)
        self._persistent_facts.append({"fact": clean_fact, "source": source})

    def get_facts(self) -> List[str]:
        return [item["fact"] for item in self._persistent_facts]
