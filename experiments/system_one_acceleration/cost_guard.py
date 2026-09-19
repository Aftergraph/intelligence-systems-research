"""Crash-safe pre-request cost guard for JAR-EXP-0014."""

from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen

from .state_projection import project_decision_state


class CostGuardError(RuntimeError):
    pass


class PricingDriftError(CostGuardError):
    pass


class BudgetExceededError(CostGuardError):
    pass


class BudgetReplayError(CostGuardError):
    pass


@dataclass(frozen=True)
class PricingSpec:
    model_id: str
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal
    conservative_max_input_tokens_per_request: int
    source_url: str
    required_source_markers: tuple[str, ...]
    canonical_sha256: str

    @property
    def max_request_cost_microusd(self) -> int:
        value = (
            Decimal(self.conservative_max_input_tokens_per_request)
            * self.input_usd_per_million_tokens
        )
        return int(value.to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True)
class CostReservation:
    request_id: str
    request_sha256: str
    reserved_microusd: int
    projected_state: dict[str, Any]
    contract: dict[str, Any]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


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


def load_pricing_spec(path: Path) -> PricingSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "jar-exp-0014.typesafe-pricing/0.1":
        raise CostGuardError("pricing spec schema invalid")
    if data.get("experiment_id") != "JAR-EXP-0014":
        raise CostGuardError("pricing spec experiment mismatch")
    if data.get("status") != "FROZEN_PRECALIBRATION":
        raise CostGuardError("pricing spec is not frozen")

    model_id = data.get("model_id")
    if not isinstance(model_id, str) or not re.fullmatch(
        r"jev-\d+\.\d+\.\d+", model_id
    ):
        raise CostGuardError("pricing spec model is not a concrete Jev version")

    try:
        input_price = Decimal(data["input_usd_per_million_tokens"])
        output_price = Decimal(data["output_usd_per_million_tokens"])
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise CostGuardError("pricing spec token price invalid") from exc
    if input_price <= 0 or output_price != 0:
        raise CostGuardError("pricing spec price assumptions invalid")

    max_tokens = data.get("conservative_max_input_tokens_per_request")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 65536:
        raise CostGuardError("pricing spec context bound is not conservative")

    source_url = data.get("source_url")
    markers = data.get("required_source_markers")
    if (
        not isinstance(source_url, str)
        or not source_url.startswith("https://docs.typesafe.ai/")
        or not isinstance(markers, list)
        or not markers
        or not all(isinstance(item, str) and item.strip() for item in markers)
    ):
        raise CostGuardError("pricing spec provenance invalid")

    return PricingSpec(
        model_id=model_id,
        input_usd_per_million_tokens=input_price,
        output_usd_per_million_tokens=output_price,
        conservative_max_input_tokens_per_request=max_tokens,
        source_url=source_url,
        required_source_markers=tuple(markers),
        canonical_sha256=_canonical_sha256(data),
    )


def _default_pricing_fetcher(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Aftergraph-JAR-EXP-0014/0.1"})
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="strict")


def verify_live_pricing(
    spec: PricingSpec, fetcher: Callable[[str], str] | None = None
) -> None:
    fetch = fetcher or _default_pricing_fetcher
    try:
        raw = fetch(spec.source_url)
    except Exception as exc:
        raise PricingDriftError("provider pricing source unavailable") from exc

    parser = _TextExtractor()
    try:
        parser.feed(raw)
        visible_text = " ".join(parser.parts)
    except Exception as exc:
        raise PricingDriftError("provider pricing source unreadable") from exc
    normalized = re.sub(r"\s+", " ", visible_text if visible_text.strip() else raw)
    missing = [marker for marker in spec.required_source_markers if marker not in normalized]
    if missing:
        raise PricingDriftError(
            "provider pricing/context markers drifted: " + ", ".join(missing)
        )


class BudgetLedger:
    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        approved_budget_microusd: int,
        pricing_spec_sha256: str,
    ) -> None:
        if approved_budget_microusd <= 0:
            raise ValueError("approved budget must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.approved_budget_microusd = approved_budget_microusd
        self.pricing_spec_sha256 = pricing_spec_sha256
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS budget_runs (
                    run_id TEXT PRIMARY KEY,
                    approved_budget_microusd INTEGER NOT NULL,
                    pricing_spec_sha256 TEXT NOT NULL
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS reservations (
                    run_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    reserved_microusd INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    actual_input_tokens INTEGER,
                    actual_cost_microusd INTEGER,
                    PRIMARY KEY (run_id, request_id)
                )"""
            )
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT approved_budget_microusd, pricing_spec_sha256 "
                "FROM budget_runs WHERE run_id = ?",
                (self.run_id,),
            ).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO budget_runs VALUES (?, ?, ?)",
                    (
                        self.run_id,
                        self.approved_budget_microusd,
                        self.pricing_spec_sha256,
                    ),
                )
            elif row != (
                self.approved_budget_microusd,
                self.pricing_spec_sha256,
            ):
                db.execute("ROLLBACK")
                raise CostGuardError("budget ledger run configuration drift")
            db.execute("COMMIT")

    def used_microusd(self) -> int:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT COALESCE(SUM(reserved_microusd), 0) "
                "FROM reservations WHERE run_id = ?",
                (self.run_id,),
            ).fetchone()
            return int(row[0])

    def reserve(
        self, *, request_id: str, request_sha256: str, reserved_microusd: int
    ) -> None:
        if not request_id or not re.fullmatch(r"[a-f0-9]{64}", request_sha256):
            raise CostGuardError("invalid reservation identity")
        if reserved_microusd <= 0:
            raise CostGuardError("invalid reservation amount")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT request_sha256 FROM reservations "
                "WHERE run_id = ? AND request_id = ?",
                (self.run_id, request_id),
            ).fetchone()
            if existing is not None:
                db.execute("ROLLBACK")
                raise BudgetReplayError("request id already reserved; replay denied")
            used = int(
                db.execute(
                    "SELECT COALESCE(SUM(reserved_microusd), 0) "
                    "FROM reservations WHERE run_id = ?",
                    (self.run_id,),
                ).fetchone()[0]
            )
            if used + reserved_microusd > self.approved_budget_microusd:
                db.execute("ROLLBACK")
                raise BudgetExceededError("insufficient pre-request budget")
            db.execute(
                "INSERT INTO reservations "
                "(run_id, request_id, request_sha256, reserved_microusd, status) "
                "VALUES (?, ?, ?, ?, 'RESERVED')",
                (self.run_id, request_id, request_sha256, reserved_microusd),
            )
            db.execute("COMMIT")

    def complete(
        self,
        *,
        request_id: str,
        request_sha256: str,
        actual_input_tokens: int,
        actual_cost_microusd: int,
    ) -> None:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT request_sha256, reserved_microusd, status "
                "FROM reservations WHERE run_id = ? AND request_id = ?",
                (self.run_id, request_id),
            ).fetchone()
            if row is None or row[0] != request_sha256:
                db.execute("ROLLBACK")
                raise CostGuardError("reservation binding mismatch")
            if row[2] != "RESERVED":
                db.execute("ROLLBACK")
                raise BudgetReplayError("reservation already completed")
            if actual_cost_microusd > int(row[1]):
                db.execute("ROLLBACK")
                raise CostGuardError("actual cost exceeded pre-request reservation")
            db.execute(
                "UPDATE reservations SET status='COMPLETED', "
                "actual_input_tokens=?, actual_cost_microusd=? "
                "WHERE run_id=? AND request_id=?",
                (actual_input_tokens, actual_cost_microusd, self.run_id, request_id),
            )
            db.execute("COMMIT")


class PreRequestCostGuard:
    def __init__(
        self,
        *,
        spec: PricingSpec,
        ledger: BudgetLedger,
        pricing_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.spec = spec
        self.ledger = ledger
        self.pricing_fetcher = pricing_fetcher

    def reserve_request(
        self,
        *,
        request_id: str,
        decision_type: str,
        state: Mapping[str, Any],
        contract: Mapping[str, Any],
        requested_model: str,
    ) -> CostReservation:
        if requested_model != self.spec.model_id:
            raise CostGuardError("request model does not match frozen pricing model")
        verify_live_pricing(self.spec, self.pricing_fetcher)
        projected_state = project_decision_state(
            decision_type=decision_type, state=state
        )
        projected_state = json.loads(_canonical_json(projected_state))
        frozen_contract = json.loads(_canonical_json(dict(contract)))
        payload = {
            "model": requested_model,
            "state": projected_state,
            "questions": {decision_type: frozen_contract},
        }
        request_sha = _canonical_sha256(payload)
        reserved = self.spec.max_request_cost_microusd
        self.ledger.reserve(
            request_id=request_id,
            request_sha256=request_sha,
            reserved_microusd=reserved,
        )
        return CostReservation(
            request_id=request_id,
            request_sha256=request_sha,
            reserved_microusd=reserved,
            projected_state=projected_state,
            contract=frozen_contract,
        )

    def complete_request(
        self, reservation: CostReservation, *, actual_input_tokens: int
    ) -> None:
        if (
            isinstance(actual_input_tokens, bool)
            or not isinstance(actual_input_tokens, int)
            or actual_input_tokens < 0
        ):
            raise CostGuardError("provider input-token usage invalid")
        if actual_input_tokens > self.spec.conservative_max_input_tokens_per_request:
            raise CostGuardError("provider usage exceeded frozen context-cost bound")
        actual_cost = int(
            (
                Decimal(actual_input_tokens)
                * self.spec.input_usd_per_million_tokens
            ).to_integral_value(rounding=ROUND_CEILING)
        )
        self.ledger.complete(
            request_id=reservation.request_id,
            request_sha256=reservation.request_sha256,
            actual_input_tokens=actual_input_tokens,
            actual_cost_microusd=actual_cost,
        )


def calibration_budget_ledger_path() -> Path:
    """Canonical durable ledger path shared across checkouts for this user."""
    return (
        Path.home()
        / ".aftergraph"
        / "research"
        / "jar-exp-0014"
        / "calibration-budget-v01.sqlite"
    )


def build_calibration_cost_guard(
    *,
    root: Path,
    ledger_path: Path,
    approved_budget_usd: float,
    pricing_fetcher: Callable[[str], str] | None = None,
) -> PreRequestCostGuard:
    spec = load_pricing_spec(
        Path(root) / "data" / "jar_exp_0014_typesafe_pricing_v01.json"
    )
    approved_microusd = int(
        (
            Decimal(str(approved_budget_usd)) * Decimal(1_000_000)
        ).to_integral_value(rounding=ROUND_FLOOR)
    )
    ledger = BudgetLedger(
        ledger_path,
        run_id="JAR-EXP-0014-calibration-v01",
        approved_budget_microusd=approved_microusd,
        pricing_spec_sha256=spec.canonical_sha256,
    )
    return PreRequestCostGuard(
        spec=spec, ledger=ledger, pricing_fetcher=pricing_fetcher
    )
