import json
from importlib.resources import files


def test_live_provider_evidence_schema_is_packaged():
    path = files("jev_engineering").joinpath("schemas/live-provider-evidence.v1.schema.json")
    payload = json.loads(path.read_text())
    assert payload["properties"]["live_provider_measurement"]["type"] == "boolean"
    assert payload["properties"]["campaign_sha256"]["pattern"] == "^[0-9a-f]{64}$"
