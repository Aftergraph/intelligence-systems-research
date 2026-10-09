from pathlib import Path


def test_v23_deploy_assets_use_bounded_relay_commands():
    hub = Path('deploy/aftergraph-jev-relay-hub.service.template').read_text(encoding='utf-8')
    node = Path('deploy/aftergraph-jev-relay-node.service.template').read_text(encoding='utf-8')
    assert 'relay-hub-serve' in hub
    assert 'relay-node-serve' in node
    assert 'shell' not in hub.casefold()
    assert 'shell' not in node.casefold()
    assert 'Restart=always' in node


def test_v23_doc_states_physical_truth_boundary():
    text = Path('docs/V23_OUTBOUND_RELAY_FABRIC.md').read_text(encoding='utf-8')
    assert 'outbound-only' in text
    assert 'does **not** claim' in text
    assert 'Jonas-Lenovo' in text
