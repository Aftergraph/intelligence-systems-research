from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from jev_engineering.node_daemon import generate_node_config_template
from jev_engineering.relay_fabric import (
    generate_relay_client_config_template,
    generate_relay_hub_config_template,
    generate_relay_node_config_template,
)

ROOT = Path(__file__).resolve().parents[1]


def _validate(schema_name: str, value: dict) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)


def test_v23_config_templates_match_versioned_contracts():
    _validate("relay-hub-config.v1.schema.json", generate_relay_hub_config_template())
    _validate("relay-node-config.v1.schema.json", generate_relay_node_config_template())
    _validate(
        "relay-client-config.v1.schema.json",
        generate_relay_client_config_template(sender_id="coordinator", worker_id="worker:jonas-lenovo"),
    )
    _validate("node-agent-config.v2.schema.json", generate_node_config_template(node_id="worker:jonas-lenovo"))


def test_v23_contracts_are_packaged_in_source_package_tree():
    for name in (
        "relay-hub-config.v1.schema.json",
        "relay-node-config.v1.schema.json",
        "relay-client-config.v1.schema.json",
        "node-agent-config.v2.schema.json",
    ):
        assert (ROOT / "src" / "jev_engineering" / "schemas" / name).is_file()
