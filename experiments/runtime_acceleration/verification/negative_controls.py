from __future__ import annotations


def assert_negative_control_failed(result: dict, expected_assertion: str) -> None:
    """Require a negative control to fail for the specific intended assertion."""
    if result.get("failed") is not True:
        raise AssertionError("negative control unexpectedly passed")
    if result.get("assertion") != expected_assertion:
        raise AssertionError(
            f"negative control failed for {result.get('assertion')!r}, expected {expected_assertion!r}"
        )
