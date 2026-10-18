import json
from importlib.resources import files


def test_paired_holdout_schema_is_packaged_and_draft_2020_12():
    path = files("jev_engineering").joinpath("schemas/paired-holdout-execution.v1.schema.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["$schema"].endswith("draft/2020-12/schema")
    assert payload["properties"]["live_provider_measurement"]["type"] == "boolean"
