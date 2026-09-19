"""Frozen pricing validation for JAR-EXP-0015.

The 0015 pricing document uses its own schema so the JAR-EXP-0014 pricing
loader never has to widen its experiment binding. Validation mirrors the
0014 fail-closed rules: concrete pinned Jev model, positive input price,
free output, conservative context bound, and docs.typesafe.ai provenance.
"""

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .cost_guard import CostGuardError, PricingSpec


JAR15_PRICING_SCHEMA = "jar-exp-0015.typesafe-pricing/0.1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def load_jar15_pricing_spec(path: Path) -> PricingSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != JAR15_PRICING_SCHEMA:
        raise CostGuardError("0015 pricing spec schema invalid")
    if data.get("experiment_id") != "JAR-EXP-0015":
        raise CostGuardError("0015 pricing spec experiment mismatch")
    if data.get("status") != "FROZEN_PREEXECUTION":
        raise CostGuardError("0015 pricing spec is not frozen")

    model_id = data.get("model_id")
    if not isinstance(model_id, str) or not re.fullmatch(
        r"jev-\d+\.\d+\.\d+", model_id
    ):
        raise CostGuardError("0015 pricing spec model is not a concrete Jev version")

    try:
        input_price = Decimal(data["input_usd_per_million_tokens"])
        output_price = Decimal(data["output_usd_per_million_tokens"])
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise CostGuardError("0015 pricing spec token price invalid") from exc
    if input_price <= 0 or output_price != 0:
        raise CostGuardError("0015 pricing spec price assumptions invalid")

    max_tokens = data.get("conservative_max_input_tokens_per_request")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 65536:
        raise CostGuardError("0015 pricing spec context bound is not conservative")

    source_url = data.get("source_url")
    markers = data.get("required_source_markers")
    if (
        not isinstance(source_url, str)
        or not source_url.startswith("https://docs.typesafe.ai/")
        or not isinstance(markers, list)
        or not markers
        or not all(isinstance(item, str) and item.strip() for item in markers)
    ):
        raise CostGuardError("0015 pricing spec provenance invalid")

    return PricingSpec(
        model_id=model_id,
        input_usd_per_million_tokens=input_price,
        output_usd_per_million_tokens=output_price,
        conservative_max_input_tokens_per_request=max_tokens,
        source_url=source_url,
        required_source_markers=tuple(markers),
        canonical_sha256=_canonical_sha256(data),
    )


def jar15_worst_case_microusd(spec: PricingSpec, provider_calls: int) -> int:
    if provider_calls <= 0:
        raise CostGuardError("provider call count must be positive")
    return spec.max_request_cost_microusd * provider_calls
