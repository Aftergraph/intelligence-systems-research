from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_v216_lineage_proof_is_bounded_and_not_performance_claim() -> None:
    manifest = yaml.safe_load((ROOT / "benchmarks/v216_authenticated_lineage_proof.yaml").read_text())
    assert len(manifest["cases"]) == 1
    assert "not a performance estimate" in manifest["hypothesis"]

    for rel in ("configs/v216-proof-frontier.yaml", "configs/v216-proof-jev.yaml"):
        cfg = yaml.safe_load((ROOT / rel).read_text())
        assert cfg["runtime"]["max_turns"] == 4
        assert cfg["runtime"]["command_mode"] == "verify_only"

    script = (ROOT / "scripts/run_v216_lineage_proof.py").read_text()
    assert "holdout_pairs=1" in script
    assert "incumbent_condition='qwen-frontier-control'" in script
    assert "candidate_condition='qwen-jev-control'" in script
    assert "'authenticated_live_ab_executed':False" in script
    assert "'performance_claim':False" in script
    assert "from_private_key_b64" not in script
    assert "from_private_key_bytes" in script
    assert "base64.b64decode" in script


def test_v216_lineage_proof_keeps_conditions_provider_distinct() -> None:
    frontier = yaml.safe_load((ROOT / "configs/v216-proof-frontier.yaml").read_text())
    jev = yaml.safe_load((ROOT / "configs/v216-proof-jev.yaml").read_text())
    assert frontier["decision"]["backend"] == "openai_compatible"
    assert frontier["decision"]["api_key_env"] == "DIALAGRAM_API_KEY"
    assert jev["decision"]["backend"] == "typesafe"
    assert jev["decision"]["api_key_env"] == "TYPESAFE_API_KEY"
