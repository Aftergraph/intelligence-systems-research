from __future__ import annotations

import json
from importlib.resources import files

from jev_engineering.config import AppConfig


def test_v13_contract_schemas_exist_and_are_packaged() -> None:
    names = {
        "context-projection.v1.schema.json": "Aftergraph ContextProjection v1",
        "evidence-claim.v1.schema.json": "Aftergraph EvidenceClaim v1",
        "verification-plan.v1.schema.json": "Aftergraph VerificationPlan v1",
    }
    for name, title in names.items():
        payload = json.loads(files("jev_engineering").joinpath(f"schemas/{name}").read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["title"] == title
        assert payload["required"]


def test_config_builds_context_compiler_and_verification_portfolio(tmp_path) -> None:
    cfg_path = tmp_path / "v13.yaml"
    cfg_path.write_text(
        '''
decision:
  backend: local
context_compiler:
  enabled: true
  token_budget: 9000
verification_fabric:
  enabled: true
  requirement:
    required_assurance: 2
    required_detection: 0.9
    max_cost_usd: 0.10
  methods:
    - id: unit
      assurance_level: 1
      detection_probability: 0.75
      estimated_cost_usd: 0.01
      estimated_latency_ms: 100
      command: python -m pytest -q
    - id: compile
      assurance_level: 2
      detection_probability: 0.70
      estimated_cost_usd: 0.01
      estimated_latency_ms: 50
      command: python -m compileall -q src tests
models: {}
''',
        encoding="utf-8",
    )
    cfg = AppConfig.load(cfg_path)
    compiler, budget = cfg.context_compiler()
    optimizer, requirement = cfg.verification_portfolio()
    assert compiler is not None
    assert budget == 9000
    assert optimizer is not None and requirement is not None
    plan = optimizer.plan(requirement)
    assert {m.method_id for m in plan.methods} == {"unit", "compile"}
    assert plan.combined_detection >= 0.9
