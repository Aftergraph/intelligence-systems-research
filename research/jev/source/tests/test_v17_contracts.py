from __future__ import annotations

import json
from importlib.resources import files


def test_v17_contract_schemas_are_packaged() -> None:
    names = {
        "authority-grant.v1.schema.json": "Aftergraph AuthorityGrant v1",
        "worker-lease.v1.schema.json": "Aftergraph WorkerLease v1",
        "provider-route.v1.schema.json": "Aftergraph ProviderRoute v1",
        "signed-receipt.v1.schema.json": "Aftergraph SignedReceipt v1",
    }
    for name, title in names.items():
        payload = json.loads(files("jev_engineering").joinpath(f"schemas/{name}").read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"].endswith(name)
        assert payload["title"] == title
        assert payload["required"]
