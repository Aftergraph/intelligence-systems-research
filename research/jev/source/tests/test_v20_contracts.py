import json
from importlib.resources import files


def test_v20_contract_schemas_are_packaged():
    expected = {
        "execution-event.v1.schema.json": "Aftergraph ExecutionEvent v1",
        "signed-proof-delta.v1.schema.json": "Aftergraph SignedProofDelta v1",
    }
    for name, title in expected.items():
        payload = json.loads(files("jev_engineering").joinpath(f"schemas/{name}").read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["title"] == title
        assert payload["required"]
