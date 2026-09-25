from __future__ import annotations

import json
from importlib.resources import files


def test_v14_learning_contract_schemas_are_packaged() -> None:
    names = {
        "learning-candidate.v1.schema.json": "Aftergraph LearningCandidate v1",
        "shadow-observation.v1.schema.json": "Aftergraph ShadowObservation v1",
        "speculative-transaction.v1.schema.json": "Aftergraph SpeculativeTransaction v1",
    }
    for name, title in names.items():
        payload = json.loads(files("jev_engineering").joinpath(f"schemas/{name}").read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["title"] == title
        assert payload["required"]
