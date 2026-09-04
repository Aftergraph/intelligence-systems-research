import re
import uuid
import yaml

# ponytail: Minimal rule-based & template-driven intent compiler.
# Converts natural-language human intent into a valid Mission contract
# conforming to schemas/mission.v0alpha1.json.
# Upgrade path: Can bind to an LLM extraction prompt when online.

class MissionCompiler:
    def __init__(self):
        pass

    def compile(self, natural_language_intent, mission_id=None, budget_usd=5.0, max_tokens=100000):
        """Compiles human intent into a structured Mission contract dictionary."""
        intent = natural_language_intent.strip()
        m_id = mission_id or f"mission-{uuid.uuid4().hex[:8]}"

        # Extract basic intent components heuristically
        success_criteria = ["task_executed_successfully"]
        
        # Check for test / build keywords
        lower = intent.lower()
        if "test" in lower:
            success_criteria.append("unit_tests_passed")
        if "build" in lower:
            success_criteria.append("build_passed")
        if "lint" in lower or "format" in lower:
            success_criteria.append("lint_checks_passed")
        if "deploy" in lower:
            success_criteria.append("deployment_verified")
        if "health" in lower:
            success_criteria.append("health_check_passed")

        # Check for monetary budget mentions (e.g. "$10", "15 EUR")
        money_match = re.search(r'(\$|€|EUR|USD)\s*(\d+(?:\.\d+)?)', intent, re.IGNORECASE)
        currency = "USD"
        if money_match:
            val = float(money_match.group(2))
            if "€" in money_match.group(1) or "EUR" in money_match.group(1).upper():
                currency = "EUR"
            budget_usd = val

        mission_doc = {
            "apiVersion": "intelligence.systems/v0alpha1",
            "kind": "Mission",
            "metadata": {
                "id": m_id,
                "version": 1,
                "name": intent[:50] + ("..." if len(intent) > 50 else "")
            },
            "objective": {
                "outcome": intent,
                "context": "Compiled from natural-language human intent."
            },
            "inputs": {},
            "success": {
                "all": success_criteria
            },
            "constraints": {
                "max_retries": 2,
                "require_isolated_environment": True
            },
            "budget": {
                "wall_clock": {
                    "max": "30m"
                },
                "tokens": {
                    "max": int(max_tokens)
                },
                "money": {
                    "max": float(budget_usd),
                    "currency": currency
                },
                "human_interventions": {
                    "max": 3
                }
            },
            "authority": {
                "default": "scoped_to_mission"
            },
            "assurance": {
                "verification": {
                    "independence": "required",
                    "minimum_tier": "tier_2_deterministic"
                }
            },
            "evidence": {
                "required": [f"{c}_proof" for c in success_criteria]
            },
            "recovery": {
                "retry_limit": 2,
                "on_failure": ["retry", "escalate"]
            }
        }
        return mission_doc

    def compile_to_yaml(self, natural_language_intent, **kwargs):
        doc = self.compile(natural_language_intent, **kwargs)
        return yaml.dump(doc, sort_keys=False)
