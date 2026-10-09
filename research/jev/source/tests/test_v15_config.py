from pathlib import Path

from jev_engineering.config import AppConfig


def test_config_can_build_local_shadow_decision_plane_and_promotion_registry(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
decision:
  backend: local
shadow_decision:
  enabled: true
  backend: local
  incumbent_strategy: frontier-control
  candidate_strategy: jev-shadow
intelligence_fabric:
  enabled: true
  promotion_registry_path: routes.json
  frontier_budget: {input_tokens: 0, output_tokens: 0}
  strategies:
    - id: rule
      source: rule
      capabilities: [decision]
      predicted_vsr: 0.99
      estimated_cost_usd: 0.0
      estimated_latency_ms: 1
""",
        encoding="utf-8",
    )
    cfg = AppConfig.load(config)
    shadow = cfg.shadow_decision_backend()
    assert shadow is not None
    backend, metadata = shadow
    assert backend is not None
    assert metadata["candidate_strategy"] == "jev-shadow"
    fabric = cfg.intelligence_fabric()
    assert fabric is not None
    assert fabric.promotion_registry is not None
