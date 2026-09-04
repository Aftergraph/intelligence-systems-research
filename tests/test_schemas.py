import json
import os
import sys
import yaml
import jsonschema

# ponytail: minimal runnable check for Phase B schema validation & complexity budget.
# No frameworks, no fixtures. Fails with AssertionError if broken.

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_schemas():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workspace = os.path.abspath(os.path.join(base_dir, ".."))
    schema_dir = os.path.join(workspace, "schemas")
    example_dir = os.path.join(workspace, "examples")

    # 1. Load schemas
    is_schema = load_json(os.path.join(schema_dir, "intelligence-system.v0alpha1.json"))
    mission_schema = load_json(os.path.join(schema_dir, "mission.v0alpha1.json"))
    delegation_schema = load_json(os.path.join(schema_dir, "delegation.v0alpha1.json"))
    evidence_schema = load_json(os.path.join(schema_dir, "evidence.v0alpha1.json"))

    # Validate the schemas themselves against Draft 2020-12 meta-schema
    for name, schema in [
        ("IntelligenceSystem", is_schema),
        ("Mission", mission_schema),
        ("Delegation", delegation_schema),
        ("Evidence", evidence_schema)
    ]:
        jsonschema.Draft202012Validator.check_schema(schema)

    # 2. Validate examples/INTELLIGENCE.yaml
    is_example = load_yaml(os.path.join(example_dir, "INTELLIGENCE.yaml"))
    jsonschema.validate(instance=is_example, schema=is_schema)

    # 3. Validate examples/mission.release.yaml
    mission_example = load_yaml(os.path.join(example_dir, "mission.release.yaml"))
    jsonschema.validate(instance=mission_example, schema=mission_schema)

    # 4. Validate a sample Delegation object
    sample_delegation = {
        "id": "del-test-001",
        "principal": "urn:principal:human:jonas",
        "delegate": "urn:agent:code-agent",
        "purpose": "urn:mission:swe-bench-lite:test-42",
        "scope": {
            "allowed_capabilities": ["mcp://git/commit", "mcp://fs/write"],
            "denied_capabilities": ["mcp://aws/*"]
        },
        "valid_from": "2026-09-03T20:00:00Z",
        "expires_at": "2026-09-03T22:00:00Z",
        "allow_redelegation": False,
        "max_delegation_depth": 1
    }
    jsonschema.validate(instance=sample_delegation, schema=delegation_schema)

    # 5. Validate a sample EvidenceItem object
    sample_evidence = {
        "id": "ev-001",
        "mission_id": "release-production",
        "criterion_ref": "tests_passed",
        "tier": "tier_2_deterministic",
        "verifier": {
            "type": "test_harness",
            "identifier": "pytest-runner",
            "version": "8.3.2"
        },
        "result": "SATISFIED",
        "evidence_data": {
            "exit_code": 0,
            "stdout": "42 passed in 1.2s"
        },
        "timestamp": "2026-09-03T21:15:00Z",
        "freshness_seconds": 1800
    }
    jsonschema.validate(instance=sample_evidence, schema=evidence_schema)

    # 6. Negative test: ensure invalid mission fails schema
    invalid_mission = {"apiVersion": "invalid", "kind": "Mission"}
    try:
        jsonschema.validate(instance=invalid_mission, schema=mission_schema)
        raise AssertionError("Expected ValidationError was not raised for invalid mission.")
    except jsonschema.ValidationError:
        pass  # Expected

    # 7. Complexity budget check:
    # Estimate tokens: ~4 chars per token for YAML representation
    yaml_str = yaml.dump(mission_example)
    char_count = len(yaml_str)
    estimated_tokens = char_count / 3.8
    assert estimated_tokens <= 500, f"Mission contract token budget exceeded: ~{estimated_tokens:.1f} tokens > 500 ceiling"

    print(f"SUCCESS: All schemas valid. Mission example serialized: {char_count} chars (~{estimated_tokens:.1f} tokens). Within <= 500 budget.")

if __name__ == "__main__":
    test_schemas()
