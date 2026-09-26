from __future__ import annotations

import json
from pathlib import Path

import pytest

from jev_engineering.relay_fabric import (
    RelayClientConfig,
    RelayHubConfig,
    RelayNodeConfig,
    generate_relay_client_config_template,
    generate_relay_hub_config_template,
    generate_relay_node_config_template,
)


def test_relay_templates_are_secret_free_and_structurally_bounded():
    hub = generate_relay_hub_config_template()
    node = generate_relay_node_config_template()
    client = generate_relay_client_config_template(sender_id="coordinator", worker_id="worker:jonas-lenovo")
    text = json.dumps([hub, node, client])
    assert "PRIVATE KEY-----" not in text
    assert "dgr_live_" not in text
    assert "apikey_" not in text
    assert hub["allowed_node_ids"] == ["worker:jonas-lenovo", "worker:vds"]
    assert client["signing_key_id"] == "coordinator"


def test_relay_client_config_rejects_invalid_public_key(tmp_path: Path):
    for name in ("ca", "cert", "key", "sign"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    cfg = RelayClientConfig(
        sender_id="coordinator", worker_id="worker", relay_host="relay", relay_port=9444,
        ca_file=tmp_path / "ca", certificate_file=tmp_path / "cert", private_key_file=tmp_path / "key",
        signing_key_file=tmp_path / "sign", signing_key_id="coordinator", worker_public_key_b64="not-base64",
    )
    with pytest.raises(ValueError, match="worker_public_key_b64"):
        cfg.validate()
