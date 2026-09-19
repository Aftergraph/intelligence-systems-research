from pathlib import Path


def test_optional_typesafe_requirements_are_exactly_pinned():
    root = Path(__file__).resolve().parents[1]
    lines = [
        line.strip()
        for line in (root / "requirements-typesafe.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines == ["typesafe-sdk==0.7.0"]


def test_sdk_verifier_explicitly_declares_zero_network():
    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts" / "verify_system_one_sdk.py").read_text(
        encoding="utf-8"
    )
    assert "NETWORK_CALLS=0" in text
    assert ".system_one(" not in text
