import yaml

# ponytail: Progressive disclosure formatter for Mission contracts.
# Ensures small and mid-tier models only receive what they need (Tier 1 <= 500 tokens),
# eliminating context pressure while preserving strict assurance (Tier 2 & 3).

class ProgressiveDisclosure:
    @staticmethod
    def get_tier1_execution_payload(mission_doc, allowed_capabilities=None):
        """Tier 1: Minimal model context payload for planning and tool execution."""
        payload = {
            "mission_id": mission_doc["metadata"]["id"],
            "objective": mission_doc["objective"]["outcome"],
            "constraints": mission_doc.get("constraints", {}),
            "budget": {
                "max_tokens": mission_doc.get("budget", {}).get("tokens", {}).get("max"),
                "max_money": f"{mission_doc.get('budget', {}).get('money', {}).get('max', '')} {mission_doc.get('budget', {}).get('money', {}).get('currency', 'USD')}"
            },
            "allowed_capabilities": allowed_capabilities or ["mcp://*"]
        }
        return yaml.dump(payload, sort_keys=False)

    @staticmethod
    def get_tier2_verification_payload(mission_doc):
        """Tier 2: Verification payload used by the independent verifier."""
        payload = {
            "mission_id": mission_doc["metadata"]["id"],
            "acceptance_criteria": mission_doc.get("success", {}),
            "assurance_rules": mission_doc.get("assurance", {}),
            "required_evidence": mission_doc.get("evidence", {}).get("required", [])
        }
        return yaml.dump(payload, sort_keys=False)

    @staticmethod
    def get_tier3_audit_payload(mission_doc, engine_metrics, evidence_store):
        """Tier 3: Complete audit payload for organizational governance and ISO/IEC compliance."""
        payload = {
            "mission_metadata": mission_doc["metadata"],
            "metrics": engine_metrics,
            "evidence": list(evidence_store.values()),
            "telemetry_mapping": "opentelemetry_genai"
        }
        return yaml.dump(payload, sort_keys=False)
