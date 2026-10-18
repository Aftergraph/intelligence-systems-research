import json
from importlib.resources import files


def test_v15_contracts_are_packaged():
    names = {
        "action-proposal.v1.schema.json": "Aftergraph ActionProposal v1",
        "effect-receipt.v1.schema.json": "Aftergraph EffectReceipt v1",
        "shadow-mission.v1.schema.json": "Aftergraph ShadowMissionSummary v1",
        "promotion-registry.v1.schema.json": "Aftergraph PromotionRegistry v1",
    }
    for name, title in names.items():
        payload = json.loads(files("jev_engineering").joinpath(f"schemas/{name}").read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["title"] == title
        assert payload["required"]
