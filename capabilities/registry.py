from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class Capability:
    uri: str
    description: str
    handler: Optional[Callable] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval: bool = False
    is_idempotent: bool = True

class CapabilityRegistry:
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}

    def register(self, capability: Capability):
        self._capabilities[capability.uri] = capability

    def get(self, uri: str) -> Optional[Capability]:
        return self._capabilities.get(uri)

    def list_all(self) -> List[Capability]:
        return list(self._capabilities.values())

    def get_tool_definitions_for_llm(self, allowed_uris: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Converts registered capabilities into OpenAI/Anthropic tool formats."""
        tools = []
        for uri, cap in self._capabilities.items():
            if allowed_uris is not None:
                matched = any(
                    uri == a or (a.endswith("*") and uri.startswith(a[:-1]))
                    for a in allowed_uris
                )
                if not matched:
                    continue

            name = uri.replace("://", "_").replace("/", "_").replace(".", "_")
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": cap.description,
                    "parameters": cap.parameters_schema or {"type": "object", "properties": {}}
                }
            })
        return tools
