from pathlib import Path


def test_legacy_provider_campaigns_no_longer_self_certify_authenticated_live_measurement():
    source = Path("src/jev_engineering/cli.py").read_text(encoding="utf-8")
    assert 'legacy v2.5 evidence lacks v2.9 authenticated signed paired receipts' in source
    assert 'provider-backed benchmark executed, but v2.9 authenticated signed paired receipts were not produced' in source
