"""Normalization boundary for TypeSafe System One responses.

No network access occurs here. The adapter preserves provider-returned semantics and
fails closed on unknown answer shapes so experiment receipts do not invent fields.
"""

from collections.abc import Mapping
from typing import Any


class SystemOneNormalizationError(ValueError):
    pass


def _get(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _probabilities(value: Any) -> dict[str, float]:
    raw = _get(value, "probabilities")
    if raw is None:
        raise SystemOneNormalizationError("probabilities are required")
    try:
        probs = {str(key): float(probability) for key, probability in dict(raw).items()}
    except (TypeError, ValueError) as exc:
        raise SystemOneNormalizationError("invalid probability distribution") from exc
    if not probs or any(not 0.0 <= p <= 1.0 for p in probs.values()):
        raise SystemOneNormalizationError("probabilities must be within [0, 1]")
    if abs(sum(probs.values()) - 1.0) > 1e-3:
        raise SystemOneNormalizationError("probabilities must sum to approximately 1")
    return probs


def normalize_typesafe_answer(answer: Any) -> dict[str, Any]:
    """Map an SDK/dict answer into the receipt answer contract."""
    answer_type = _get(answer, "type")

    if answer_type == "noul":
        raw = _get(answer, "noul")
        if isinstance(raw, bool):
            raise SystemOneNormalizationError("Noul must preserve numeric probability")
        try:
            probability = float(raw)
        except (TypeError, ValueError) as exc:
            raise SystemOneNormalizationError("invalid Noul probability") from exc
        if not 0.0 <= probability <= 1.0:
            raise SystemOneNormalizationError("Noul probability must be within [0, 1]")
        return {
            "kind": "noul",
            "value": probability,
            "confidence": None,
            "distribution": None,
        }

    if answer_type == "choice":
        choice = _get(answer, "choice")
        confidence = _get(answer, "confidence")
        if not isinstance(choice, str) or not choice:
            raise SystemOneNormalizationError("Choice answer requires a selected label")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise SystemOneNormalizationError("invalid Choice confidence") from exc
        if not 0.0 <= confidence_value <= 1.0:
            raise SystemOneNormalizationError("Choice confidence must be within [0, 1]")
        probs = _probabilities(answer)
        if choice not in probs:
            raise SystemOneNormalizationError("selected Choice must exist in probabilities")
        return {
            "kind": "choice",
            "value": choice,
            "confidence": confidence_value,
            "distribution": probs,
        }

    if answer_type == "score":
        score = _get(answer, "score")
        confidence = _get(answer, "confidence")
        try:
            score_value = float(score)
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise SystemOneNormalizationError("invalid Score answer") from exc
        if not 0.0 <= confidence_value <= 1.0:
            raise SystemOneNormalizationError("Score confidence must be within [0, 1]")
        return {
            "kind": "score",
            "value": score_value,
            "confidence": confidence_value,
            "distribution": _probabilities(answer),
        }

    raise SystemOneNormalizationError(f"unsupported System One answer type: {answer_type!r}")


def returned_model(response: Any) -> str:
    model = _get(response, "model")
    if not isinstance(model, str) or not model:
        raise SystemOneNormalizationError("response model identity is required")
    return model
