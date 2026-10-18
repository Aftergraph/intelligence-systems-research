from __future__ import annotations

import json
from importlib.resources import files


def test_v18_contracts_are_packaged_and_draft_2020_12() -> None:
    names = [
        "execution-context.v1.schema.json",
        "workload-assertion.v1.schema.json",
        "public-signed-receipt.v1.schema.json",
        "worker-endpoint.v1.schema.json",
        "quorum-verdict.v1.schema.json",
    ]
    root = files("jev_engineering").joinpath("schemas")
    for name in names:
        payload = json.loads(root.joinpath(name).read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["type"] == "object"
