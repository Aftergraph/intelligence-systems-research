"""JAR-EXP-0015 stage-separated pre-request cost guards."""

from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable

from .cost_guard import (
    BudgetLedger,
    CostGuardError,
    CostReservation,
    PreRequestCostGuard,
    PricingSpec,
)


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def load_jar15_pricing_spec(path: Path) -> PricingSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "jar-exp-0015.typesafe-pricing/0.1":
        raise CostGuardError("JAR-EXP-0015 pricing schema invalid")
    if data.get("experiment_id") != "JAR-EXP-0015":
        raise CostGuardError("JAR-EXP-0015 pricing experiment mismatch")
    if data.get("status") != "FROZEN_PREEXECUTION":
        raise CostGuardError("JAR-EXP-0015 pricing is not frozen")

    model_id = data.get("model_id")
    if not isinstance(model_id, str) or not re.fullmatch(r"jev-\d+\.\d+\.\d+", model_id):
        raise CostGuardError("JAR-EXP-0015 model is not concrete")

    try:
        input_price = Decimal(data["input_usd_per_million_tokens"])
        output_price = Decimal(data["output_usd_per_million_tokens"])
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise CostGuardError("JAR-EXP-0015 pricing values invalid") from exc
    if input_price <= 0 or output_price != 0:
        raise CostGuardError("JAR-EXP-0015 pricing assumptions invalid")

    max_tokens = data.get("conservative_max_input_tokens_per_request")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 65536:
        raise CostGuardError("JAR-EXP-0015 context bound invalid")

    source_url = data.get("source_url")
    markers = data.get("required_source_markers")
    if (
        source_url != "https://docs.typesafe.ai/models"
        or not isinstance(markers, list)
        or not markers
        or not all(isinstance(x, str) and x.strip() for x in markers)
    ):
        raise CostGuardError("JAR-EXP-0015 pricing provenance invalid")

    spec = PricingSpec(
        model_id=model_id,
        input_usd_per_million_tokens=input_price,
        output_usd_per_million_tokens=output_price,
        conservative_max_input_tokens_per_request=max_tokens,
        source_url=source_url,
        required_source_markers=tuple(markers),
        canonical_sha256=_canonical_sha256(data),
    )
    if spec.max_request_cost_microusd != data.get("max_request_cost_microusd"):
        raise CostGuardError("JAR-EXP-0015 per-request bound mismatch")
    return spec



class JAR15StageCostGuard:
    """Stage-bound wrapper that enforces the frozen case-ID call ceiling."""

    def __init__(self, *, base: PreRequestCostGuard, stage: str, allowed_case_ids: frozenset[str]) -> None:
        if stage not in {"calibration", "holdout"}:
            raise ValueError("stage must be calibration or holdout")
        if len(allowed_case_ids) != 1952:
            raise CostGuardError("stage allowed-case set must contain exactly 1952 ids")
        self.base = base
        self.stage = stage
        self.allowed_case_ids = allowed_case_ids
        self.spec = base.spec
        self.ledger = base.ledger

    def reserve_request(
        self,
        *,
        request_id: str,
        decision_type: str,
        state: dict[str, Any],
        contract: dict[str, Any],
        requested_model: str,
    ) -> CostReservation:
        if request_id not in self.allowed_case_ids:
            raise CostGuardError(
                f"{self.stage} request id is outside the frozen stage split"
            )
        return self.base.reserve_request(
            request_id=request_id,
            decision_type=decision_type,
            state=state,
            contract=contract,
            requested_model=requested_model,
        )

    def begin_transport(self, reservation: CostReservation) -> None:
        if reservation.request_id not in self.allowed_case_ids:
            raise CostGuardError("transport reservation is outside frozen stage split")
        self.base.begin_transport(reservation)

    def complete_request(
        self, reservation: CostReservation, *, actual_input_tokens: int
    ) -> None:
        if reservation.request_id not in self.allowed_case_ids:
            raise CostGuardError("completion reservation is outside frozen stage split")
        self.base.complete_request(
            reservation, actual_input_tokens=actual_input_tokens
        )

def jar15_budget_ledger_path(stage: str) -> Path:
    if stage not in {"calibration", "holdout"}:
        raise ValueError("stage must be calibration or holdout")
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0015"
        / f"{stage}-budget-v01.sqlite"
    )


def _gate_path(root: Path, stage: str) -> Path:
    if stage == "calibration":
        return Path(root) / "data" / "jar_exp_0015_calibration_gate_v01.json"
    if stage == "holdout":
        return Path(root) / "data" / "jar_exp_0015_holdout_gate_v01.json"
    raise ValueError("stage must be calibration or holdout")


def build_jar15_cost_guard(
    *,
    root: Path,
    stage: str,
    ledger_path: Path | None = None,
    pricing_fetcher: Callable[[str], str] | None = None,
) -> JAR15StageCostGuard:
    root = Path(root)
    gate = json.loads(_gate_path(root, stage).read_text(encoding="utf-8"))
    spec = load_jar15_pricing_spec(
        root / "data" / "jar_exp_0015_typesafe_pricing_v01.json"
    )

    if gate.get("requested_model") != spec.model_id:
        raise CostGuardError("stage gate model does not match pricing spec")
    if gate.get("sdk_retries_allowed") is not False:
        raise CostGuardError("stage gate must prohibit SDK retries")

    max_calls = gate.get("max_provider_calls")
    if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls <= 0:
        raise CostGuardError("stage call ceiling invalid")
    if max_calls != 1952:
        raise CostGuardError("stage call ceiling does not match frozen split")

    max_cost = gate.get("max_cost_usd")
    if not isinstance(max_cost, (int, float)) or isinstance(max_cost, bool) or max_cost <= 0:
        raise CostGuardError("stage cost ceiling invalid")
    approved_microusd = int(
        (Decimal(str(max_cost)) * Decimal(1_000_000)).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    worst_case = max_calls * spec.max_request_cost_microusd
    if worst_case > approved_microusd:
        raise CostGuardError("stage ceiling is below worst-case reservation total")

    canonical_path = jar15_budget_ledger_path(stage)
    selected = Path(ledger_path) if ledger_path is not None else canonical_path
    ledger = BudgetLedger(
        selected,
        run_id=f"JAR-EXP-0015-{stage}-v01",
        approved_budget_microusd=approved_microusd,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    return PreRequestCostGuard(
        spec=spec,
        ledger=ledger,
        pricing_fetcher=pricing_fetcher,
    )
