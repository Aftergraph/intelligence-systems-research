from experiments.runtime_acceleration.verification.differential import compare_observable


def test_differential_detects_semantic_mismatch():
    result = compare_observable({"text": "alpha", "status": 0}, {"text": "beta", "status": 0})
    assert result.equal is False
    assert result.classification == "SEMANTIC_MISMATCH"


def test_differential_detects_error_class_mismatch_before_payload():
    result = compare_observable(
        {"error_class": "TimeoutError", "message": "control"},
        {"error_class": "ValueError", "message": "treatment"},
    )
    assert result.equal is False
    assert result.classification == "ERROR_CLASS_MISMATCH"


def test_differential_equal_mapping_ignores_mapping_key_order():
    result = compare_observable({"a": 1, "b": [2, 3]}, {"b": [2, 3], "a": 1})
    assert result.equal is True
    assert result.classification == "EQUIVALENT"
