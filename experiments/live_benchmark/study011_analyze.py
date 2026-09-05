"""
STUDY-011 confirmatory analysis pipeline (PRE-DATA, OFFLINE ONLY).
==================================================================

Consumes ONLY raw run records / normalized data (JSONL/JSON dir).
Performs NO live calls, NO network, NO API keys. Stdlib only.

Pipeline stages:
  raw runs
    -> integrity validation (duplicate run_id, workload version, condition,
       provider/model, provenance, LIVE_ONLY invariant)
    -> execution classification
       (LIVE_VALID / LIVE_PROVIDER_FAILURE / LIVE_PROTOCOL_FAILURE /
        INVALID_PROTOCOL / EXCLUDED)
    -> normalized dataset
    -> paired dataset construction via deterministic keys
       (provider_stratum, model, workload_id, replicate_id) linking A/C/F/G
    -> statistics (per-cell counts, Wilson 95% CI, Cohen h, McNemar with
       continuity correction for H1 A-vs-G FCR and H2 C-vs-F VSR,
       provider-stratified inference, Bonferroni note)
    -> tables -> machine-readable results JSON.

Cell structure (MINIMUM VALID SAMPLE vs PLANNED MAXIMUM ATTEMPTS):
  - MINIMUM VALID SAMPLE (mathematically mandatory for confirmatory inference):
      4 conditions (A, C, F, G) x 2 Phase-1 strata (dialagram, openrouter)
      x 58 LIVE_VALID per cell = 464 LIVE_VALID minimum.
      No confirmatory claim may be made with fewer LIVE_VALID per cell
      unless the preregistration is amended (STUDY-011-AMENDMENTS.md).
  - PLANNED MAXIMUM ATTEMPTS (operational oversampling, NOT mandatory):
      619 planned attempts @ 75% expected LIVE_VALID yield
      (464 / 0.75 = 618.67 -> 619). This is a budgeting/operations number.
      If yield exceeds 75%, fewer attempts are needed. If yield is lower,
      additional attempts up to the approved budget are permitted, but the
      confirmatory bar remains 464 LIVE_VALID, not 619 attempts.
      Do NOT report "619/619 attempts" as success; report LIVE_VALID counts.

Power-assumption audit (from scripts/study011_power_analysis.py):
  - Two-sided test, per-hypothesis alpha = 0.01, Bonferroni /3 -> alpha_adj
    = 0.00333 (default; overridable via --alpha-adj).
  - Target power 1-beta = 0.8.
  - Smallest effect of interest (SEOI): Cohen h = 0.5 (conservative, ~1/3 of
    STUDY-008 simulated h=1.671; below h=0.5 practical significance doubtful).
  - Formula: N_cell = ceil((z_{1-alpha_adj/2} + z_{1-beta})^2 / h^2) = 58.
  - Paired McNemar discordant-pair note: the normal approximation above is a
    planning approximation. True McNemar power depends on the number of
    DISCORDANT pairs (b+c), not total N. If concordance is high (most pairs
    agree), effective power is lower than nominal even at N=58. This pipeline
    reports b, c, and b+c for every McNemar test so reviewers can audit
    whether the discordant-pair count supports the claimed power. Cells with
    b+c < 10 are flagged LOW_DISCORDANT (interpret with caution).
  - Provider-stratified: inference is performed SEPARATELY within each
    provider stratum (dialagram, openrouter, ...). Strata are never pooled
    for confirmatory decisions. A pooled estimate is reported as exploratory
    only, with an explicit warning.
  - Mixed-effects logistic note: the protocol (§8) lists a mixed-effects
    logistic model (outcome ~ condition + provider + model + (1|workload)) as
    a secondary analysis. That model requires an iterative solver (lme4 /
    statsmodels) and is INTENTIONALLY NOT implemented in this stdlib-only
    pipeline. The primary confirmatory test is the within-stratum paired
    McNemar (which respects the workload blocking factor by pairing). If a
    mixed-effects fit is later run, it must be versioned separately and must
    not overwrite this pipeline's outputs.

Replication codes (STUDY-011 §4, defined BEFORE data):
  SUPPORTED / PARTIALLY_SUPPORTED / FAILED_TO_REPLICATE / REVERSED.
  See classify_replication_*() docstrings for exact gates.

Assumptions documented (pre-data, frozen here):
  A1. Pairing key uses EXACT model id (exact_model_id), not family. Cross-model
      pairs are never formed, even within the same provider stratum.
  A2. replicate_id: explicit field (replicate_id|replica|replicate) wins; else
      parsed from run_id via /[-_]r(\\d+)\\s*$/ (case-insensitive); else "0".
      Duplicate (stratum, model, workload, replicate, condition) is an
      integrity violation (would silently collapse distinct attempts).
  A3. FCR denominator: declared-complete runs (reported), matching STUDY-008
      (fc_count / reported_count). FCR among LIVE_VALID is also reported as
      fcr_among_valid for transparency. H1 McNemar uses per-run fcr_flag
      paired A-vs-G (binary per pair member), so denominator choice does not
      affect the paired test, only the descriptive rate.
  A4. VSR denominator: LIVE_VALID runs in the cell.
  A5. CPVO (cost per verified outcome) = sum(total_cost) / verified_count.
      If verified_count == 0, CPVO is null (JSON) / empty (CSV), never 0.
  A6. TVO (time to verified outcome): per-run time_to_verified_outcome if
      present else latency_ms when verified else 0; reported as mean over
      verified runs (mean_tvo_ms) and sum (total_tvo_ms).
  A7. Control-plane tax: control_plane_cost / total_cost per run where both
      fields exist, else 0.0. Mean tax reported per cell. If source records
      lack cost decomposition, tax is 0.0 and flagged costs_decomposed=False.
  A8. H2 tradeoff gate: SUPPORTED requires VSR(F) > VSR(C) on effect+evidence
      AND no false-completion inflation (FCR(F) <= FCR(C) + 0.02 tolerance).
      If FCR inflates beyond tolerance, the best possible code is
      PARTIALLY_SUPPORTED even if the VSR effect is large and significant.
  A9. H3 joint gate: SUPPORTED requires, in >= 2 strata, BOTH
      CPVO(G) <= 2.0 * CPVO(A) AND FCR(G) <= 0.05 with correct direction
      (FCR(G) < FCR(A)). H3 is a descriptive joint gate, not a p-value gate;
      the FCR McNemar p-value is reported alongside but does not alone decide
      H3. Any stratum with reversed direction (FCR(G) > FCR(A)) and
      n_pairs >= MIN_PAIRS_FOR_REVERSAL (5) forces overall REVERSED.
  A10. REVERSED rule (H1/H2): any stratum with opposite direction and
      n_pairs >= 5 forces overall REVERSED (conservative stopping rule per
      §3). Strata with n_pairs < 5 and opposite direction yield a
      reversal_warning but do not alone force REVERSED (noise guard).
  A11. LIVE_ONLY invariant: ANY simulation marker (is_live False with
      confirmatory condition, execution_class SIMULATED, raw markers
      "[Dialagram Sim:" / "[Sim:") in the confirmatory input set is a hard
      integrity violation -> IntegrityError -> CLI exit 2. Simulation records
      are NEVER silently reclassified; they abort the run.
  A12. Provenance for LIVE_VALID: is_live True, http_status == 200,
      provider_request_id present, request_hash + response_hash present,
      token_count_prompt + token_count_completion present (int >= 0),
      latency_ms > 0. Genuine attempts failing transport (http != 200,
      timeout, 429 with is_live True) -> LIVE_PROVIDER_FAILURE (data, not a
      violation). Live transport OK but condition-isolation breach
      (F/G without assurance, A/C with assurance) or mission ERROR/TIMEOUT
      with http 200 -> LIVE_PROTOCOL_FAILURE. Structural protocol problems
      (unknown condition, missing workload_id, bad provenance shape with
      http 200) -> INVALID_PROTOCOL. Anything else explicitly excluded ->
      EXCLUDED.

Exit codes: 0 success; 2 integrity violation; 1 other error.
Outputs (in --output-dir): summary.md, results.json, tables.csv.
"""

import argparse
import csv
import glob
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ── Frozen design constants ──────────────────────────────────────────────────
STUDY_ID = "STUDY-011"
CONFIRMATORY_CONDITIONS = ("A", "C", "F", "G")
PHASE1_STRATA = ("dialagram", "openrouter")
N_PER_CELL_MIN = 58
PHASE1_MIN_LIVE_VALID = 464  # 4 conds x 2 strata x 58
PLANNED_MAX_ATTEMPTS_P1 = 619  # ceil(464/0.75); operational only, NOT a bar
EXPECTED_SUCCESS_RATE = 0.75
DEFAULT_ALPHA_ADJ = 0.01 / 3.0  # 0.00333...
DEFAULT_SEOI_H = 0.5
MIN_PAIRS_FOR_REVERSAL = 5
H3_CPVO_RATIO_MAX = 2.0
H3_FCR_G_MAX = 0.05
H2_FCR_TOLERANCE = 0.02

REPLICATION_CODES = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "FAILED_TO_REPLICATE",
    "REVERSED",
)

EXECUTION_CLASSES = (
    "LIVE_VALID",
    "LIVE_PROVIDER_FAILURE",
    "LIVE_PROTOCOL_FAILURE",
    "INVALID_PROTOCOL",
    "EXCLUDED",
)

SIMULATION_MARKERS = ("[Dialagram Sim:", "[Sim:", "[Simulation:")



# ── 3-Block Segregation ─────────────────────────────────────────────────────
# Block definitions for 3-block integrity boundary (post-Amendment-009)
# Block 1 (ORIGINAL CONFIRMATORY): fp starts with b6b7c2d0 (dialagram, Amendments 1-8 era)
# Block 2 (NON-VIABLE): fp starts with 0c588022 (openrouter 429-burn, 0 valid)
# Block 3 (POST-AMENDMENT-010): fp starts with dfe3513c (openrouter paid models)


def block_of(record: Dict[str, Any]) -> int:
    """Assign a record to block 1, 2, or 3 based on implementation_fingerprint + provider.

    Block 1: fp starts with b6b7c2d0 (ORIGINAL CONFIRMATORY, dialagram, Amendments 1-8)
    Block 2: fp starts with 0c588022 (NON-VIABLE, openrouter 429-burn, 0 valid)
    Block 3: fp starts with dfe3513c (POST-AMENDMENT-010, openrouter paid models)

    Amendment 009 fingerprint (0c588022) from DIALAGRAM provider is Block 1 (breaker-path fix).
    """
    fp = record.get("implementation_fingerprint", "")
    provider = record.get("provider_name", "").lower()
    # Block 1: original confirmatory (dialagram era)
    if fp.startswith("b6b7c2d0") or (fp.startswith("0c588022") and provider == "dialagram"):
        return 1
    # Block 2: non-viable (openrouter 429-burn)
    if fp.startswith("0c588022"):
        return 2
    # Block 3: post-amendment-010 (paid models)
    if fp.startswith("dfe3513c"):
        return 3
    # Unknown fingerprints default to 0 (excluded from analysis)
    return 0


# ── Errors ───────────────────────────────────────────────────────────────────
class IntegrityError(Exception):
    """Hard integrity violation: caller must exit non-zero."""


# ── Statistics (same formulas as STUDY-008 normalize_and_analyze.py) ─────────
def wilson_ci(pos: int, total: int, conf: float = 0.95) -> Tuple[float, float]:
    """95% Wilson score interval, returned as percentages rounded to 2dp."""
    if total == 0:
        return (0.0, 0.0)
    z = 1.95996
    p = pos / total
    denom = 1.0 + (z ** 2) / total
    centre = (p + (z ** 2) / (2.0 * total)) / denom
    spread = (z / denom) * math.sqrt((p * (1.0 - p) / total) + (z ** 2) / (4.0 * (total ** 2)))
    return (round(max(0.0, centre - spread) * 100.0, 2),
            round(min(1.0, centre + spread) * 100.0, 2))


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h between two proportions (absolute value, rounded 3dp)."""
    p1 = max(0.0001, min(0.9999, p1))
    p2 = max(0.0001, min(0.9999, p2))
    phi1 = 2.0 * math.asin(math.sqrt(p1))
    phi2 = 2.0 * math.asin(math.sqrt(p2))
    return round(abs(phi1 - phi2), 3)


def mcnemar_test(b: int, c: int) -> Tuple[float, float]:
    """McNemar chi-square with continuity correction + two-sided p-value.

    chi2 = (|b-c|-1)^2 / (b+c); p from chi-square(1) survival via erfc.
    Returns (chi2 rounded 3dp, p rounded 6dp). (0.0, 1.0) when b+c == 0.
    """
    total = b + c
    if total == 0:
        return (0.0, 1.0)
    chi2 = ((abs(b - c) - 1.0) ** 2) / total
    p_val = math.erfc(math.sqrt(chi2) / math.sqrt(2.0))
    return (round(chi2, 3), round(p_val, 6))


# ── Input loading ────────────────────────────────────────────────────────────
def load_raw_runs(input_dir: str) -> List[Dict[str, Any]]:
    """Load raw run records from a directory of .json / .jsonl files.

    Each .json file holds one record (object) or a list of records.
    Each .jsonl file holds one record per non-blank line.
    Returns records in sorted-file, line order (deterministic).
    """
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input dir not found: {input_dir}")
    paths = sorted(glob.glob(os.path.join(input_dir, "*.json")) +
                   glob.glob(os.path.join(input_dir, "*.jsonl")))
    if not paths:
        raise FileNotFoundError(f"no .json/.jsonl files in input dir: {input_dir}")
    runs: List[Dict[str, Any]] = []
    for path in paths:
        if path.endswith(".jsonl"):
            with open(path, "r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise IntegrityError(
                            f"unparseable JSONL {os.path.basename(path)}:{lineno}: {exc}"
                        )
                    if not isinstance(rec, dict):
                        raise IntegrityError(
                            f"JSONL record must be an object: {os.path.basename(path)}:{lineno}"
                        )
                    rec.setdefault("_source_file", os.path.basename(path))
                    rec.setdefault("_source_line", lineno)
                    runs.append(rec)
        else:
            with open(path, "r", encoding="utf-8") as fh:
                try:
                    payload = json.load(fh)
                except json.JSONDecodeError as exc:
                    raise IntegrityError(f"unparseable JSON {os.path.basename(path)}: {exc}")
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    raise IntegrityError(
                        f"JSON record must be an object in {os.path.basename(path)}"
                    )
                item.setdefault("_source_file", os.path.basename(path))
                runs.append(item)
    return runs


# ── Helpers: field access tolerant to both RunRecord and STUDY-008 namings ───
def _str_field(rec: Dict[str, Any], *names: str, default: str = "") -> str:
    for name in names:
        val = rec.get(name)
        if val is not None and str(val).strip() != "":
            return str(val)
    return default


def _bool_field(rec: Dict[str, Any], *names: str, default: bool = False) -> bool:
    for name in names:
        if name in rec and rec[name] is not None:
            val = rec[name]
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                low = val.strip().lower()
                if low in ("true", "1", "yes", "y"):
                    return True
                if low in ("false", "0", "no", "n", ""):
                    return False
                return default
            return bool(val)
    return default


def _num_field(rec: Dict[str, Any], *names: str, default: float = 0.0) -> float:
    for name in names:
        if name in rec and rec[name] is not None:
            try:
                return float(rec[name])
            except (TypeError, ValueError):
                continue
    return default


def _int_field(rec: Dict[str, Any], *names: str, default: int = 0) -> int:
    return int(_num_field(rec, *names, default=float(default)))


def provider_stratum_of(rec: Dict[str, Any]) -> str:
    raw = _str_field(rec, "provider_stratum", "provider_name", "provider",
                     default="unknown").strip().lower()
    return raw if raw else "unknown"


def model_of(rec: Dict[str, Any]) -> str:
    return _str_field(rec, "exact_model_id", "model", default="unknown")


def workload_of(rec: Dict[str, Any]) -> str:
    return _str_field(rec, "workload_id", "workload", default="")


def condition_of(rec: Dict[str, Any]) -> str:
    return _str_field(rec, "condition", default="").strip().upper()


_REPLICATE_RE = re.compile(r"[-_]r(\d+)\s*$", re.IGNORECASE)


def replicate_of(rec: Dict[str, Any]) -> str:
    for key in ("replicate_id", "replica", "replicate", "replication_id"):
        if rec.get(key) is not None and str(rec.get(key)).strip() != "":
            return str(rec.get(key)).strip()
    run_id = _str_field(rec, "run_id", default="")
    match = _REPLICATE_RE.search(run_id)
    if match:
        return str(int(match.group(1)))  # normalize "001" -> "1"
    return "0"


def pairing_key(rec: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Deterministic pairing key: (provider_stratum, model, workload_id, replicate_id)."""
    return (provider_stratum_of(rec), model_of(rec), workload_of(rec), replicate_of(rec))


def _has_simulation_marker(rec: Dict[str, Any]) -> bool:
    for key in ("raw_response", "raw_response_excerpt", "raw_response_text",
                "response_text", "candidate_text"):
        val = rec.get(key)
        if isinstance(val, str) and any(m in val for m in SIMULATION_MARKERS):
            return True
    cls = str(rec.get("execution_class", "") or "").upper()
    if cls == "SIMULATED" or cls == "SIMULATION":
        return True
    if _str_field(rec, "execution_mode", default="").upper() == "SIMULATION_ONLY":
        return True
    return False


# ── Integrity validation ─────────────────────────────────────────────────────
def validate_integrity(raw_runs: List[Dict[str, Any]]) -> None:
    """Hard integrity checks. Raises IntegrityError on violation.

    - missing/blank run_id -> violation (cannot pair or audit).
    - duplicate run_id -> violation.
    - duplicate pairing key within the SAME condition -> violation (would
      silently collapse distinct attempts into one pair slot).
    - ANY simulation marker in a confirmatory-condition record, or any
      confirmatory record with is_live explicitly False, or any confirmatory
      record with execution_class SIMULATED -> LIVE_ONLY violation.
    Other per-record problems (unknown condition, missing workload_id,
    incomplete provenance) do NOT raise here; they route to INVALID_PROTOCOL
    / EXCLUDED classification so attempt accounting stays complete.
    """
    if not raw_runs:
        raise IntegrityError("empty input: no raw run records found")
    seen_ids: Dict[str, str] = {}
    seen_pair_cond: Dict[Tuple[str, str, str, str, str], str] = {}
    for idx, rec in enumerate(raw_runs):
        run_id = rec.get("run_id")
        where = f"{rec.get('_source_file', '?')}#{idx}"
        if run_id is None or str(run_id).strip() == "":
            raise IntegrityError(f"missing run_id at {where}: every record needs a run_id")
        run_id = str(run_id)
        if run_id in seen_ids:
            raise IntegrityError(
                f"duplicate run_id {run_id!r} (first in {seen_ids[run_id]}, again at {where})"
            )
        seen_ids[run_id] = str(rec.get("_source_file", "?"))
        cond = condition_of(rec)
        if cond in CONFIRMATORY_CONDITIONS:
            if _has_simulation_marker(rec):
                raise IntegrityError(
                    f"LIVE_ONLY violation: simulation marker in confirmatory record "
                    f"{run_id!r} (condition {cond}). Rejecting confirmatory set; "
                    f"no simulation fallback permitted."
                )
            if "is_live" in rec and rec["is_live"] is False:
                # Explicit False in a confirmatory record = non-live in LIVE_ONLY set.
                raise IntegrityError(
                    f"LIVE_ONLY violation: is_live=False in confirmatory record "
                    f"{run_id!r} (condition {cond})."
                )
            key = pairing_key(rec) + (cond,)
            if key in seen_pair_cond:
                raise IntegrityError(
                    f"duplicate pairing key {key} for run {run_id!r} "
                    f"(first run {seen_pair_cond[key]!r}). Distinct attempts must "
                    f"carry distinct replicate_id values."
                )
            seen_pair_cond[key] = run_id


# ── Execution classification ─────────────────────────────────────────────────
def classify_execution(rec: Dict[str, Any]) -> str:
    """Classify one raw record into the 5-class taxonomy (see module docstring A12)."""
    cond = condition_of(rec)
    explicit = str(rec.get("execution_class", "") or "").strip().upper()
    if explicit == "EXCLUDED":
        return "EXCLUDED"
    if cond not in CONFIRMATORY_CONDITIONS:
        # Exploratory / unknown conditions never enter the confirmatory set.
        return "EXCLUDED"
    workload_id = workload_of(rec)
    if not workload_id:
        return "INVALID_PROTOCOL"
    is_live = rec.get("is_live", True)
    if is_live is False:
        # Non-confirmatory False would have raised already only for
        # confirmatory conditions; reaching here means tolerant path — but per
        # A11 confirmatory False always raises, so this is defensive.
        return "EXCLUDED"
    http_status = rec.get("http_status", rec.get("httpStatus", 200))
    try:
        http_int = int(http_status) if http_status is not None else 200
    except (TypeError, ValueError):
        return "INVALID_PROTOCOL"
    if http_int != 200:
        # Genuine attempt evidence with transport failure (429/5xx/timeout/None).
        return "LIVE_PROVIDER_FAILURE"
    # Transport OK (200): check provenance completeness for LIVE_VALID.
    missing_provenance = []
    if not _str_field(rec, "provider_request_id", "providerRequestId", "request_id"):
        missing_provenance.append("provider_request_id")
    if not _str_field(rec, "request_hash", "requestHash"):
        missing_provenance.append("request_hash")
    if not _str_field(rec, "response_hash", "responseHash"):
        missing_provenance.append("response_hash")
    if rec.get("token_count_prompt", rec.get("tokenCountPrompt",
                rec.get("input_tokens", rec.get("prompt_tokens")))) is None:
        missing_provenance.append("token_count_prompt")
    if rec.get("token_count_completion", rec.get("tokenCountCompletion",
                rec.get("output_tokens", rec.get("completion_tokens")))) is None:
        missing_provenance.append("token_count_completion")
    try:
        latency = float(rec.get("latency_ms", rec.get("latencyMs", 0.0)) or 0.0)
    except (TypeError, ValueError):
        latency = 0.0
    if latency <= 0:
        missing_provenance.append("latency_ms>0")
    if missing_provenance:
        return "INVALID_PROTOCOL"
    # Condition-isolation / mission-protocol checks -> LIVE_PROTOCOL_FAILURE.
    assurance_keys = ("assurance_invoked", "assuranceInvoked", "assurance_used")
    assurance_present = any(k in rec for k in assurance_keys)
    if assurance_present:
        invoked = _bool_field(rec, *assurance_keys, default=False)
        if cond in ("F", "G") and not invoked:
            return "LIVE_PROTOCOL_FAILURE"
        if cond in ("A", "C") and invoked:
            return "LIVE_PROTOCOL_FAILURE"
    mission_state = _str_field(rec, "mission_state_final", "missionStateFinal",
                               "final_mission_state", "final_state", default="").upper()
    if mission_state in ("ERROR", "TIMEOUT") and http_int == 200:
        return "LIVE_PROTOCOL_FAILURE"
    return "LIVE_VALID"


# ── Normalization ────────────────────────────────────────────────────────────
def _declared_complete(rec: Dict[str, Any], norm: Dict[str, Any]) -> bool:
    if "declared_complete" in rec and rec["declared_complete"] is not None:
        return _bool_field(rec, "declared_complete")
    if "reported_complete" in rec and rec["reported_complete"] is not None:
        return _bool_field(rec, "reported_complete")
    # Fall back: VERIFIED implies declaration; FAILED/TIMEOUT implies none.
    state = str(norm.get("mission_state_final", "")).upper()
    if state == "VERIFIED":
        return True
    if state in ("FAILED", "TIMEOUT", "ERROR", "ABSTAINED"):
        return False
    return _bool_field(rec, "declaredComplete", default=False)


def normalize_record(rec: Dict[str, Any], execution_class: str) -> Dict[str, Any]:
    """Project one raw record onto the canonical normalized schema."""
    stratum = provider_stratum_of(rec)
    model = model_of(rec)
    workload_id = workload_of(rec)
    cond = condition_of(rec)
    replicate_id = replicate_of(rec)
    run_id = str(rec.get("run_id", ""))
    seed = rec.get("randomization_seed", rec.get("randomizationSeed",
                   rec.get("seed", rec.get("random_seed"))))
    try:
        seed_preserved: Optional[str] = None if seed is None else str(seed)
    except Exception:
        seed_preserved = None

    latency_ms = float(_num_field(rec, "latency_ms", "latencyMs", "latency", default=0.0))
    prompt_tok = _int_field(rec, "token_count_prompt", "tokenCountPrompt",
                            "input_tokens", "prompt_tokens", "tokens_prompt", default=0)
    completion_tok = _int_field(rec, "token_count_completion", "tokenCountCompletion",
                                "output_tokens", "completion_tokens",
                                "tokens_completion", default=0)
    total_tok = rec.get("token_count_total", rec.get("total_tokens",
                rec.get("tokens_total", rec.get("tokens_used"))))
    try:
        total_tok_int = int(float(total_tok)) if total_tok is not None else prompt_tok + completion_tok
    except (TypeError, ValueError):
        total_tok_int = prompt_tok + completion_tok

    total_cost = float(_num_field(rec, "cost_usd", "costUsd", "total_cost",
                                  "provider_cost", default=0.0))
    control_plane_cost = float(_num_field(rec, "control_plane_cost",
                                          "controlPlaneCost", default=0.0))
    verification_cost = float(_num_field(rec, "verification_cost",
                                         "verificationCost", default=0.0))
    costs_decomposed = any(k in rec for k in ("control_plane_cost", "controlPlaneCost",
                                              "verification_cost", "verificationCost",
                                              "provider_cost"))

    mission_state = _str_field(rec, "mission_state_final", "missionStateFinal",
                               "final_mission_state", "final_state", default="")
    fcr_flag = _bool_field(rec, "fcr_flag", "fcrFlag", "false_completion",
                           "falseCompletion", default=False)
    vsr_flag = _bool_field(rec, "vsr_flag", "vsrFlag", "verified_success",
                           "verifiedSuccess", default=False)
    actual_success = _bool_field(rec, "actual_success", "actualSuccess",
                                 "ground_truth_pass", "groundTruthPass",
                                 default=vsr_flag)

    norm: Dict[str, Any] = {
        "run_id": run_id,
        "study_id": _str_field(rec, "study_id", "studyId", default=STUDY_ID),
        "provider_stratum": stratum,
        "provider_name": _str_field(rec, "provider_name", "provider", default=stratum),
        "model": model,
        "workload_id": workload_id,
        "workload_version": _str_field(rec, "workload_version", "workloadVersion",
                                       "mission_hash", "missionHash", default=""),
        "replicate_id": replicate_id,
        "condition": cond,
        "randomization_seed": seed_preserved,
        "execution_class": execution_class,
        "is_live": bool(rec.get("is_live", True)),
        "http_status": rec.get("http_status", rec.get("httpStatus")),
        "latency_ms": round(latency_ms, 2),
        "tokens_prompt": prompt_tok,
        "tokens_completion": completion_tok,
        "tokens_total": total_tok_int,
        "cost_usd": round(total_cost, 6),
        "control_plane_cost": round(control_plane_cost, 6),
        "verification_cost": round(verification_cost, 6),
        "costs_decomposed": costs_decomposed,
        "mission_state_final": mission_state,
        "fcr_flag": bool(fcr_flag),
        "vsr_flag": bool(vsr_flag),
        "actual_success": bool(actual_success),
    }
    declared = _declared_complete(rec, norm)
    norm["declared_complete"] = bool(declared)
    # Abstention / non-completion: ran live but never declared complete.
    norm["abstained"] = (not declared) and execution_class == "LIVE_VALID"
    # Recovery accounting (tolerant to both namings).
    rec_attempted = _bool_field(rec, "recovery_attempted", "recoveryAttempted", default=False)
    if "recovery_attempts" in rec or "recoveryAttempts" in rec or "retry_count" in rec:
        attempts_n = _int_field(rec, "recovery_attempts", "recoveryAttempts",
                                "retry_count", "retryCount", default=0)
        rec_attempted = rec_attempted or attempts_n > 0
    else:
        attempts_n = 1 if rec_attempted else 0
    rec_succeeded = _bool_field(rec, "recovery_succeeded", "recoverySucceeded", default=False)
    if rec_attempted and rec_succeeded is False:
        # Recovery counts as succeeded only if the run ultimately verified.
        rec_succeeded = bool(vsr_flag and actual_success)
    norm["recovery_attempted"] = bool(rec_attempted)
    norm["recovery_attempts"] = int(attempts_n)
    norm["recovery_succeeded"] = bool(rec_succeeded)
    # Constraint / authority accounting.
    if "constraint_retained" in rec or "constraintRetained" in rec:
        retained = _bool_field(rec, "constraint_retained", "constraintRetained", default=True)
    else:
        violations = rec.get("constraint_violations", rec.get("constraintViolations", []))
        retained = (not violations) if isinstance(violations, list) else True
    norm["constraint_retained"] = bool(retained)
    if "unauthorized_action" in rec or "unauthorizedAction" in rec:
        unauth = _bool_field(rec, "unauthorized_action", "unauthorizedAction", default=False)
    else:
        violations = rec.get("constraint_violations", rec.get("constraintViolations", []))
        unauth = any("out-of-scope" in str(v) or "unauthor" in str(v).lower()
                     for v in violations) if isinstance(violations, list) else False
    norm["unauthorized_action"] = bool(unauth)
    # TVO: time to verified outcome.
    tvo = _num_field(rec, "time_to_verified_outcome", "timeToVerifiedOutcome", default=0.0)
    if tvo <= 0 and vsr_flag:
        tvo = latency_ms
    norm["time_to_verified_outcome_ms"] = round(float(tvo), 2)
    # Control-plane tax share.
    tax = (control_plane_cost / total_cost) if total_cost > 0 else 0.0
    norm["control_plane_tax"] = round(max(0.0, min(1.0, tax)), 4)
    norm["pairing_key"] = "|".join(pairing_key(rec))
    return norm


# ── Cell statistics ──────────────────────────────────────────────────────────
def _rate(count: int, denom: int) -> float:
    return round((count / denom) * 100.0, 1) if denom else 0.0


def compute_cell_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Descriptive stats for one cell (already filtered to LIVE_VALID unless noted)."""
    n = len(rows)
    declared = sum(1 for r in rows if r["declared_complete"])
    vs = sum(1 for r in rows if r["vsr_flag"])
    fc = sum(1 for r in rows if r["fcr_flag"])
    actual = sum(1 for r in rows if r["actual_success"])
    abst = sum(1 for r in rows if r["abstained"])
    rec_att = sum(1 for r in rows if r["recovery_attempted"])
    rec_succ = sum(1 for r in rows if r["recovery_succeeded"])
    retained = sum(1 for r in rows if r["constraint_retained"])
    unauth = sum(1 for r in rows if r["unauthorized_action"])
    tot_cost = sum(float(r["cost_usd"]) for r in rows)
    tot_lat = sum(float(r["latency_ms"]) for r in rows)
    tot_tok = sum(int(r["tokens_total"]) for r in rows)
    tot_tvo = sum(float(r["time_to_verified_outcome_ms"]) for r in rows if r["vsr_flag"])
    tot_tax = sum(float(r["control_plane_tax"]) for r in rows)
    cpvo = (tot_cost / vs) if vs else None
    return {
        "n": n,
        "declared_complete": declared,
        "vs_count": vs,
        "vsr": _rate(vs, n),
        "vsr_ci": list(wilson_ci(vs, n)),
        "fc_count": fc,
        "fcr_reported": _rate(fc, declared),
        "fcr_reported_ci": list(wilson_ci(fc, declared)),
        "fcr_among_valid": _rate(fc, n),
        "fcr_among_valid_ci": list(wilson_ci(fc, n)),
        "actual_success_count": actual,
        "actual_success_rate": _rate(actual, n),
        "actual_success_ci": list(wilson_ci(actual, n)),
        "abstained_count": abst,
        "abstention_rate": _rate(abst, n),
        "abstention_ci": list(wilson_ci(abst, n)),
        "recovery_attempted": rec_att,
        "recovery_succeeded": rec_succ,
        "recovery_rate": _rate(rec_succ, rec_att),
        "recovery_ci": list(wilson_ci(rec_succ, rec_att)),
        "constraint_retention_rate": _rate(retained, n),
        "constraint_retention_ci": list(wilson_ci(retained, n)),
        "unauthorized_action_rate": _rate(unauth, n),
        "unauthorized_action_ci": list(wilson_ci(unauth, n)),
        "total_cost_usd": round(tot_cost, 4),
        "cpvo_usd": (round(cpvo, 4) if cpvo is not None else None),
        "mean_latency_ms": round(tot_lat / n, 1) if n else 0.0,
        "mean_tokens": round(tot_tok / n, 1) if n else 0.0,
        "total_tokens": tot_tok,
        "mean_tvo_ms": round(tot_tvo / vs, 1) if vs else 0.0,
        "mean_control_plane_tax": round(tot_tax / n, 4) if n else 0.0,
    }


# ── Paired dataset ───────────────────────────────────────────────────────────
def build_paired_dataset(
    normalized: List[Dict[str, Any]],
    cond_x: str,
    cond_y: str,
) -> Dict[str, Any]:
    """Build paired dataset for conditions (cond_x, cond_y).

    Groups LIVE_VALID rows by pairing key; keeps only keys present in BOTH
    conditions (rejects unpaired comparisons). If both members carry a
    randomization_seed and the seeds differ, the pair is excluded as
    seed_mismatch (broken randomization) and counted separately.
    Returns {pairs, unpaired_x, unpaired_y, seed_mismatches}.
    """
    by_key_x: Dict[str, Dict[str, Any]] = {}
    by_key_y: Dict[str, Dict[str, Any]] = {}
    for row in normalized:
        if row["execution_class"] != "LIVE_VALID":
            continue
        if row["condition"] == cond_x:
            by_key_x[row["pairing_key"]] = row
        elif row["condition"] == cond_y:
            by_key_y[row["pairing_key"]] = row
    pairs: List[Dict[str, Any]] = []
    seed_mismatches: List[str] = []
    for key in sorted(set(by_key_x) & set(by_key_y)):
        rx, ry = by_key_x[key], by_key_y[key]
        sx, sy = rx.get("randomization_seed"), ry.get("randomization_seed")
        if sx is not None and sy is not None and str(sx) != str(sy):
            seed_mismatches.append(key)
            continue
        pairs.append({"key": key, "x": rx, "y": ry})
    return {
        "cond_x": cond_x,
        "cond_y": cond_y,
        "pairs": pairs,
        "n_pairs": len(pairs),
        "unpaired_x": sorted(set(by_key_x) - set(by_key_y)),
        "unpaired_y": sorted(set(by_key_y) - set(by_key_x)),
        "seed_mismatches": seed_mismatches,
    }


def mcnemar_from_pairs(
    pairs: List[Dict[str, Any]],
    flag: str,
    favor_y_when: str = "y_eq_1_x_eq_0",
) -> Dict[str, Any]:
    """McNemar table on a binary flag across paired members.

    flag: per-run boolean field name (e.g. "fcr_flag", "vsr_flag").
    b = x=1,y=0 count; c = x=0,y=1 count (with x=cond_x, y=cond_y).
    favor_y_when documents which discordant direction favors cond_y.
    """
    b = sum(1 for p in pairs if p["x"].get(flag) and not p["y"].get(flag))
    c = sum(1 for p in pairs if (not p["x"].get(flag)) and p["y"].get(flag))
    n00 = sum(1 for p in pairs if (not p["x"].get(flag)) and (not p["y"].get(flag)))
    n11 = sum(1 for p in pairs if p["x"].get(flag) and p["y"].get(flag))
    chi2, p_val = mcnemar_test(b, c)
    discordant = b + c
    return {
        "flag": flag,
        "b_x_only": b,
        "c_y_only": c,
        "n00": n00,
        "n11": n11,
        "discordant": discordant,
        "low_discordant": discordant < 10,
        "chi2": chi2,
        "p_value": p_val,
        "favor_y_when": favor_y_when,
    }


# ── Replication classification (pre-data gates) ──────────────────────────────
def _direction_and_h(
    stat_x: Dict[str, Any],
    stat_y: Dict[str, Any],
    metric: str,
    higher_is_better_for_y: bool,
) -> Tuple[bool, float]:
    """Return (direction_correct, cohens_h) for y-vs-x on a percentage metric."""
    px = stat_x[metric] / 100.0
    py = stat_y[metric] / 100.0
    h = cohens_h(px, py)
    if higher_is_better_for_y:
        direction = py > px
    else:
        direction = py < px
    return direction, h


def classify_stratum_effect(
    direction_correct: bool,
    h: float,
    p_value: float,
    alpha_adj: float,
    seoi_h: float,
) -> str:
    """Classify ONE stratum's effect (helper; overall codes need >=1 strata).

    - direction wrong -> "REVERSED" (candidate; caller applies n_pairs guard).
    - direction right + h >= seoi + p <= alpha -> "SUPPORTING".
    - direction right otherwise -> "WEAK".
    - direction right + negligible (h < 0.2 and p > alpha) -> "NEGLIGIBLE".
    """
    if not direction_correct:
        return "REVERSED"
    if h >= seoi_h and p_value <= alpha_adj:
        return "SUPPORTING"
    if h < 0.2 and p_value > alpha_adj:
        return "NEGLIGIBLE"
    return "WEAK"


def classify_replication_h1(
    stratum_results: List[Dict[str, Any]],
    alpha_adj: float = DEFAULT_ALPHA_ADJ,
    seoi_h: float = DEFAULT_SEOI_H,
) -> Dict[str, Any]:
    """H1 (FCR reduction, G vs A): classify SUPPORTED/.../REVERSED.

    stratum_results: list of {stratum, n_pairs, direction_correct (FCR_G<FCR_A),
      h (Cohen h on FCR), p_value (McNemar A-vs-G on fcr_flag)}.
    Gates (§4 + A10):
      REVERSED if any stratum with n_pairs >= MIN_PAIRS_FOR_REVERSAL has
        direction_correct False.
      SUPPORTED if direction correct + h>=seoi + p<=alpha in >= 2 strata.
      PARTIALLY_SUPPORTED if direction correct in >= 1 stratum but magnitude
        < seoi or p > alpha, or only 1 stratum fully supporting.
      FAILED_TO_REPLICATE if direction correct everywhere counted but no
        stratum reaches (h>=seoi and p<=alpha) and all h negligible/weak.
    """
    supporting = [s for s in stratum_results
                  if s.get("direction_correct") and s.get("h", 0.0) >= seoi_h
                  and s.get("p_value", 1.0) <= alpha_adj]
    reversals = [s for s in stratum_results
                 if not s.get("direction_correct")
                 and int(s.get("n_pairs", 0)) >= MIN_PAIRS_FOR_REVERSAL]
    weak_warnings = [s for s in stratum_results
                     if not s.get("direction_correct")
                     and int(s.get("n_pairs", 0)) < MIN_PAIRS_FOR_REVERSAL]
    if reversals:
        code = "REVERSED"
    elif len(supporting) >= 2:
        code = "SUPPORTED"
    elif len(supporting) == 1 or any(s.get("direction_correct") for s in stratum_results):
        code = "PARTIALLY_SUPPORTED"
    else:
        code = "FAILED_TO_REPLICATE"
    # Edge: direction correct everywhere but all negligible -> FAILED.
    if code == "PARTIALLY_SUPPORTED":
        if stratum_results and all(
            s.get("direction_correct") and s.get("h", 0.0) < 0.2
            and s.get("p_value", 1.0) > alpha_adj for s in stratum_results
        ):
            code = "FAILED_TO_REPLICATE"
    return {"hypothesis": "H1", "code": code,
            "n_supporting_strata": len(supporting),
            "reversed_strata": [s.get("stratum") for s in reversals],
            "reversal_warnings_low_n": [s.get("stratum") for s in weak_warnings]}


def classify_replication_h2(
    stratum_results: List[Dict[str, Any]],
    fcr_tradeoff: Optional[Dict[str, float]] = None,
    alpha_adj: float = DEFAULT_ALPHA_ADJ,
    seoi_h: float = DEFAULT_SEOI_H,
) -> Dict[str, Any]:
    """H2 (VSR recovery, F vs C + false-completion tradeoff): classify.

    stratum_results: list of {stratum, n_pairs, direction_correct
      (VSR_F>VSR_C), h (Cohen h on VSR), p_value (McNemar C-vs-F on vsr_flag)}.
    fcr_tradeoff: optional {stratum: (FCR_F - FCR_C)} in percentage points.
      Per A8, if FCR inflates beyond H2_FCR_TOLERANCE (2pp) in a supporting
      stratum, that stratum is demoted to WEAK (caps overall at PARTIALLY).
    Otherwise gates mirror H1 with the VSR direction.
    """
    demoted: List[str] = []
    adjusted: List[Dict[str, Any]] = []
    for s in stratum_results:
        s2 = dict(s)
        if (fcr_tradeoff is not None and s.get("stratum") in fcr_tradeoff
                and s.get("direction_correct")):
            inflation = fcr_tradeoff[s["stratum"]]
            if inflation > H2_FCR_TOLERANCE * 100.0:
                demoted.append(s["stratum"])
                s2["tradeoff_violated"] = True
                # Demote: pretend evidence failed so it cannot count as supporting.
                s2["p_value"] = 1.0
        adjusted.append(s2)
    supporting = [s for s in adjusted
                  if s.get("direction_correct") and s.get("h", 0.0) >= seoi_h
                  and s.get("p_value", 1.0) <= alpha_adj
                  and not s.get("tradeoff_violated")]
    reversals = [s for s in adjusted
                 if not s.get("direction_correct")
                 and int(s.get("n_pairs", 0)) >= MIN_PAIRS_FOR_REVERSAL]
    warnings = [s for s in adjusted
                if not s.get("direction_correct")
                and int(s.get("n_pairs", 0)) < MIN_PAIRS_FOR_REVERSAL]
    if reversals:
        code = "REVERSED"
    elif len(supporting) >= 2 and not demoted:
        code = "SUPPORTED"
    elif len(supporting) >= 2 and demoted:
        # Effect holds but tradeoff violated somewhere -> cap.
        code = "PARTIALLY_SUPPORTED"
    elif len(supporting) == 1 or any(s.get("direction_correct") for s in adjusted):
        code = "PARTIALLY_SUPPORTED"
    else:
        code = "FAILED_TO_REPLICATE"
    if code == "PARTIALLY_SUPPORTED" and adjusted and all(
        s.get("direction_correct") and s.get("h", 0.0) < 0.2
        and s.get("p_value", 1.0) > alpha_adj for s in adjusted
    ):
        code = "FAILED_TO_REPLICATE"
    return {"hypothesis": "H2", "code": code,
            "n_supporting_strata": len(supporting),
            "reversed_strata": [s.get("stratum") for s in reversals],
            "reversal_warnings_low_n": [s.get("stratum") for s in warnings],
            "tradeoff_demoted_strata": demoted}


def classify_replication_h3(
    stratum_gates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """H3 (G vs A reliability + cost/latency tradeoff): classify.

    stratum_gates: list of {stratum, n_pairs, fcr_a, fcr_g (percent),
      cpvo_a, cpvo_g (usd or None), direction_correct (FCR_G < FCR_A)}.
    Per-stratum PASS requires ALL of:
      direction_correct True, fcr_g <= H3_FCR_G_MAX*100 (5%),
      cpvo_g is not None and cpvo_a is not None and cpvo_a > 0 and
      cpvo_g <= H3_CPVO_RATIO_MAX * cpvo_a.
    Overall (A9):
      REVERSED if any stratum with n_pairs >= 5 has direction_correct False.
      SUPPORTED if >= 2 strata PASS.
      PARTIALLY_SUPPORTED if exactly 1 stratum PASSES.
      FAILED_TO_REPLICATE otherwise.
    """
    passing: List[str] = []
    failing: List[str] = []
    reversals: List[str] = []
    warnings: List[str] = []
    for s in stratum_gates:
        stratum = s.get("stratum")
        n_pairs = int(s.get("n_pairs", 0))
        if not s.get("direction_correct"):
            if n_pairs >= MIN_PAIRS_FOR_REVERSAL:
                reversals.append(stratum)
            else:
                warnings.append(stratum)
            failing.append(stratum)
            continue
        fcr_g = float(s.get("fcr_g", 100.0))
        cpvo_a = s.get("cpvo_a")
        cpvo_g = s.get("cpvo_g")
        cost_ok = (cpvo_a is not None and cpvo_g is not None
                   and float(cpvo_a) > 0
                   and float(cpvo_g) <= H3_CPVO_RATIO_MAX * float(cpvo_a))
        rel_ok = fcr_g <= H3_FCR_G_MAX * 100.0
        if cost_ok and rel_ok:
            passing.append(stratum)
        else:
            failing.append(stratum)
    if reversals:
        code = "REVERSED"
    elif len(passing) >= 2:
        code = "SUPPORTED"
    elif len(passing) == 1:
        code = "PARTIALLY_SUPPORTED"
    else:
        code = "FAILED_TO_REPLICATE"
    return {"hypothesis": "H3", "code": code,
            "passing_strata": passing, "failing_strata": failing,
            "reversed_strata": reversals,
            "reversal_warnings_low_n": warnings}


# ── Full analysis driver ─────────────────────────────────────────────────────
def analyze(
    raw_runs: List[Dict[str, Any]],
    alpha_adj: float = DEFAULT_ALPHA_ADJ,
    seoi_h: float = DEFAULT_SEOI_H,
) -> Dict[str, Any]:
    """Run the full pipeline on in-memory raw records. Returns results dict."""
    validate_integrity(raw_runs)
    # Classification + normalization.
    normalized: List[Dict[str, Any]] = []
    class_counts: Dict[str, int] = {k: 0 for k in EXECUTION_CLASSES}
    attempt_counts: Dict[str, Dict[str, Dict[str, int]]] = {}
    for rec in raw_runs:
        cls = classify_execution(rec)
        class_counts[cls] = class_counts.get(cls, 0) + 1
        norm = normalize_record(rec, cls)
        normalized.append(norm)
        stratum, model, cond = norm["provider_stratum"], norm["model"], norm["condition"]
        wid = norm["workload_id"] or "(missing)"
        attempt_counts.setdefault(stratum, {}).setdefault(model, {}).setdefault(cond, 0)
        attempt_counts[stratum][model][cond] += 1
    live_valid = [r for r in normalized if r["execution_class"] == "LIVE_VALID"]
    # Per-cell stats keyed "stratum|condition".
    cells: Dict[str, Dict[str, Any]] = {}
    strata = sorted({r["provider_stratum"] for r in normalized})
    for stratum in strata:
        for cond in CONFIRMATORY_CONDITIONS:
            key = f"{stratum}|{cond}"
            rows = [r for r in live_valid
                    if r["provider_stratum"] == stratum and r["condition"] == cond]
            cells[key] = compute_cell_stats(rows)
            cells[key]["stratum"] = stratum
            cells[key]["condition"] = cond
    # Per-model and per-workload breakdowns (LIVE_VALID only).
    by_model: Dict[str, Dict[str, Any]] = {}
    for (stratum, model, cond) in sorted({(r["provider_stratum"], r["model"], r["condition"])
                                          for r in live_valid}):
        rows = [r for r in live_valid if r["provider_stratum"] == stratum
                and r["model"] == model and r["condition"] == cond]
        by_model[f"{stratum}|{model}|{cond}"] = compute_cell_stats(rows)
    by_workload: Dict[str, Dict[str, Any]] = {}
    for (stratum, wid, cond) in sorted({(r["provider_stratum"], r["workload_id"], r["condition"])
                                        for r in live_valid}):
        rows = [r for r in live_valid if r["provider_stratum"] == stratum
                and r["workload_id"] == wid and r["condition"] == cond]
        by_workload[f"{stratum}|{wid}|{cond}"] = compute_cell_stats(rows)

    # Paired tests, stratified by provider.
    h1_strata: List[Dict[str, Any]] = []
    h2_strata: List[Dict[str, Any]] = []
    h3_gates: List[Dict[str, Any]] = []
    paired_detail: Dict[str, Any] = {}
    for stratum in strata:
        s_rows = [r for r in live_valid if r["provider_stratum"] == stratum]
        # H1: A-vs-G on fcr_flag (reduction favors G).
        paired_ag = build_paired_dataset(s_rows, "A", "G")
        mc_h1 = mcnemar_from_pairs(paired_ag["pairs"], "fcr_flag",
                                   favor_y_when="G=0,A=1 (reduction favors G)")
        ca, cg = cells[f"{stratum}|A"], cells[f"{stratum}|G"]
        # Direction from descriptive FCR(reported): G < A.
        dir_h1 = cg["fcr_reported"] < ca["fcr_reported"]
        # h on FCR proportions (among reported; guard div0 via cohens_h clamp).
        denom_a = max(1, ca["declared_complete"])
        denom_g = max(1, cg["declared_complete"])
        h_h1 = cohens_h(ca["fc_count"] / denom_a, cg["fc_count"] / denom_g)
        h1_strata.append({"stratum": stratum, "n_pairs": paired_ag["n_pairs"],
                          "b_A_only": mc_h1["b_x_only"], "c_G_only": mc_h1["c_y_only"],
                          "discordant": mc_h1["discordant"],
                          "low_discordant": mc_h1["low_discordant"],
                          "chi2": mc_h1["chi2"], "p_value": mc_h1["p_value"],
                          "direction_correct": bool(dir_h1), "h": h_h1,
                          "fcr_a": ca["fcr_reported"], "fcr_g": cg["fcr_reported"]})
        # H2: C-vs-F on vsr_flag (increase favors F) + tradeoff on FCR.
        paired_cf = build_paired_dataset(s_rows, "C", "F")
        mc_h2 = mcnemar_from_pairs(paired_cf["pairs"], "vsr_flag",
                                   favor_y_when="F=1,C=0 (recovery favors F)")
        cc, cf = cells[f"{stratum}|C"], cells[f"{stratum}|F"]
        dir_h2 = cf["vsr"] > cc["vsr"]
        h_h2 = cohens_h(cc["vsr"] / 100.0, cf["vsr"] / 100.0)
        h2_strata.append({"stratum": stratum, "n_pairs": paired_cf["n_pairs"],
                          "b_C_only": mc_h2["b_x_only"], "c_F_only": mc_h2["c_y_only"],
                          "discordant": mc_h2["discordant"],
                          "low_discordant": mc_h2["low_discordant"],
                          "chi2": mc_h2["chi2"], "p_value": mc_h2["p_value"],
                          "direction_correct": bool(dir_h2), "h": h_h2,
                          "vsr_c": cc["vsr"], "vsr_f": cf["vsr"],
                          "fcr_c": cc["fcr_reported"], "fcr_f": cf["fcr_reported"]})
        h3_gates.append({"stratum": stratum, "n_pairs": paired_ag["n_pairs"],
                         "fcr_a": ca["fcr_reported"], "fcr_g": cg["fcr_reported"],
                         "cpvo_a": ca["cpvo_usd"], "cpvo_g": cg["cpvo_usd"],
                         "direction_correct": bool(dir_h1)})
        paired_detail[stratum] = {
            "H1_A_vs_G": {**mc_h1, "n_pairs": paired_ag["n_pairs"],
                          "unpaired_A": len(paired_ag["unpaired_x"]),
                          "unpaired_G": len(paired_ag["unpaired_y"]),
                          "seed_mismatches": len(paired_ag["seed_mismatches"])},
            "H2_C_vs_F": {**mc_h2, "n_pairs": paired_cf["n_pairs"],
                          "unpaired_C": len(paired_cf["unpaired_x"]),
                          "unpaired_F": len(paired_cf["unpaired_y"]),
                          "seed_mismatches": len(paired_cf["seed_mismatches"])},
        }

        # ── Block-segregated analysis (3-block integrity boundary) ─────────────
        # Block 1: ORIGINAL CONFIRMATORY (b6b7c2d0 fp, dialagram)
        # Block 2: NON-VIABLE (0c588022 fp, openrouter 429-burn)
        # Block 3: POST-AMENDMENT-010 (dfe3513c fp, openrouter paid)
        block1_rows = [r for r in s_rows if block_of(r) == 1]
        block2_rows = [r for r in s_rows if block_of(r) == 2]
        block3_rows = [r for r in s_rows if block_of(r) == 3]
        block_results = {}
        for blk, rows in [(1, block1_rows), (2, block2_rows), (3, block3_rows)]:
            blk_stratum = f"{stratum}_block{blk}"
            # H1 for this block
            if rows:
                blk_paired_ag = build_paired_dataset(rows, "A", "G")
                blk_h1 = mcnemar_from_pairs(blk_paired_ag["pairs"], "fcr_flag",
                                           favor_y_when="G=0,A=1 (reduction favors G)")
                blk_ca = cells[f"{stratum}|A"] if f"{stratum}|A" in cells else {"declared_complete": 1, "fc_count": 0}
                blk_cg = cells[f"{stratum}|G"] if f"{stratum}|G" in cells else {"declared_complete": 1, "fc_count": 0}
                blk_dir_h1 = blk_cg["fcr_reported"] < blk_ca["fcr_reported"]
                blk_denom_a = max(1, blk_ca.get("declared_complete", 1))
                blk_denom_g = max(1, blk_cg.get("declared_complete", 1))
                blk_h_h1 = cohens_h(blk_ca["fc_count"] / blk_denom_a, blk_cg["fc_count"] / blk_denom_g)
                block_results[f"h1_{blk_stratum}"] = {
                    "stratum": blk_stratum, "n_pairs": blk_paired_ag["n_pairs"],
                    "b_A_only": blk_h1["b_x_only"], "c_G_only": blk_h1["c_y_only"],
                    "discordant": blk_h1["discordant"], "low_discordant": blk_h1["low_discordant"],
                    "chi2": blk_h1["chi2"], "p_value": blk_h1["p_value"],
                    "direction_correct": bool(blk_dir_h1), "h": blk_h_h1,
                    "fcr_a": blk_ca["fcr_reported"], "fcr_g": blk_cg["fcr_reported"]}
            else:
                block_results[f"h1_{blk_stratum}"] = {
                    "stratum": blk_stratum, "n_pairs": 0, "b_A_only": 0, "c_G_only": 0,
                    "discordant": 0, "low_discordant": False, "chi2": 0.0, "p_value": 1.0,
                    "direction_correct": False, "h": 0.0, "fcr_a": 0.0, "fcr_g": 0.0,
                    "status": "NO_OBSERVATIONS" if blk == 2 else "EMPTY"}
            # H2 for this block
            if rows:
                blk_paired_cf = build_paired_dataset(rows, "C", "F")
                blk_h2 = mcnemar_from_pairs(blk_paired_cf["pairs"], "vsr_flag",
                                           favor_y_when="F=1,C=0 (recovery favors F)")
                blk_cc = cells[f"{stratum}|C"] if f"{stratum}|C" in cells else {"vsr": 0}
                blk_cf = cells[f"{stratum}|F"] if f"{stratum}|F" in cells else {"vsr": 0}
                blk_dir_h2 = blk_cf["vsr"] > blk_cc["vsr"]
                blk_h_h2 = cohens_h(blk_cc["vsr"] / 100.0, blk_cf["vsr"] / 100.0)
                block_results[f"h2_{blk_stratum}"] = {
                    "stratum": blk_stratum, "n_pairs": blk_paired_cf["n_pairs"],
                    "b_C_only": blk_h2["b_x_only"], "c_F_only": blk_h2["c_y_only"],
                    "discordant": blk_h2["discordant"], "low_discordant": blk_h2["low_discordant"],
                    "chi2": blk_h2["chi2"], "p_value": blk_h2["p_value"],
                    "direction_correct": bool(blk_dir_h2), "h": blk_h_h2,
                    "vsr_c": blk_cc["vsr"], "vsr_f": blk_cf["vsr"],
                    "fcr_c": blk_cc.get("fcr_reported", 0.0), "fcr_f": blk_cf.get("fcr_reported", 0.0)}
            else:
                block_results[f"h2_{blk_stratum}"] = {
                    "stratum": blk_stratum, "n_pairs": 0, "b_C_only": 0, "c_F_only": 0,
                    "discordant": 0, "low_discordant": False, "chi2": 0.0, "p_value": 1.0,
                    "direction_correct": False, "h": 0.0, "vsr_c": 0.0, "vsr_f": 0.0,
                    "fcr_c": 0.0, "fcr_f": 0.0, "status": "NO_OBSERVATIONS" if blk == 2 else "EMPTY"}
            block_results[f"h3_{blk_stratum}"] = {
                "stratum": blk_stratum, "n_pairs": block_results.get(f"h1_{blk_stratum}", {}).get("n_pairs", 0),
                "fcr_a": block_results.get(f"h1_{blk_stratum}", {}).get("fcr_a", 0.0),
                "fcr_g": block_results.get(f"h1_{blk_stratum}", {}).get("fcr_g", 0.0),
                "cpvo_a": None, "cpvo_g": None,
                "direction_correct": block_results.get(f"h1_{blk_stratum}", {}).get("direction_correct", False)}

    fcr_tradeoff = {s["stratum"]: (s["fcr_f"] - s["fcr_c"]) for s in h2_strata}
    rep_h1 = classify_replication_h1(h1_strata, alpha_adj, seoi_h)
    rep_h2 = classify_replication_h2(h2_strata, fcr_tradeoff, alpha_adj, seoi_h)
    rep_h3 = classify_replication_h3(h3_gates)

    # Sample-size audit vs 464 minimum.
    min_per_cell = N_PER_CELL_MIN
    cell_audit = {}
    for key, stat in cells.items():
        cell_audit[key] = {"n_live_valid": stat["n"], "target": min_per_cell,
                           "met": stat["n"] >= min_per_cell,
                           "shortfall": max(0, min_per_cell - stat["n"])}
    total_live_valid = len(live_valid)
    results: Dict[str, Any] = {
        "study_id": STUDY_ID,
        "alpha_adj": alpha_adj,
        "seoi_h": seoi_h,
        "design": {
            "confirmatory_conditions": list(CONFIRMATORY_CONDITIONS),
            "phase1_strata": list(PHASE1_STRATA),
            "min_live_valid_per_cell": N_PER_CELL_MIN,
            "phase1_min_live_valid": PHASE1_MIN_LIVE_VALID,
            "planned_max_attempts_p1_operational_only": PLANNED_MAX_ATTEMPTS_P1,
            "expected_success_rate_assumption": EXPECTED_SUCCESS_RATE,
            "note": ("619 is PLANNED MAXIMUM ATTEMPTS at 75% yield (operational "
                     "oversampling), NOT a success bar. The confirmatory bar is "
                     "464 LIVE_VALID (58/cell)."),
            "bonferroni_note": ("Primary McNemar p-values are compared against "
                                "alpha_adj (Bonferroni over 3 confirmatory hypotheses). "
                                "Mixed-effects logistic is out of scope for this "
                                "stdlib pipeline; see module docstring."),
        },
        "attempt_accounting": {
            "attempted_total": len(raw_runs),
            "by_class": dict(class_counts),
            "live_valid_total": total_live_valid,
            "per_stratum_model_condition_attempts": attempt_counts,
        },
        "cells": cells,
        "by_model": by_model,
        "by_workload": by_workload,
        "cell_audit_vs_58": cell_audit,
        "all_cells_met": all(v["met"] for v in cell_audit.values()) if cell_audit else False,
        "paired": paired_detail,
        "H1_strata": h1_strata,
        "H2_strata": h2_strata,
        "H3_gates": h3_gates,
        "replication": {"H1": rep_h1, "H2": rep_h2, "H3": rep_h3},
        "block_results": block_results,
        "normalized_n": len(normalized),
    }
    return results


# ── Output writers ───────────────────────────────────────────────────────────
def write_results_json(results: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=True)


def write_tables_csv(results: Dict[str, Any], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["table", "stratum", "condition_or_model", "metric", "value"])
        for key, stat in sorted(results.get("cells", {}).items()):
            stratum, cond = key.split("|", 1)
            for metric in ("n", "vsr", "fcr_reported", "fcr_among_valid",
                           "actual_success_rate", "abstention_rate", "recovery_rate",
                           "constraint_retention_rate", "unauthorized_action_rate",
                           "total_cost_usd", "cpvo_usd", "mean_latency_ms",
                           "mean_tokens", "mean_tvo_ms", "mean_control_plane_tax"):
                writer.writerow(["cell", stratum, cond, metric, stat.get(metric)])
            writer.writerow(["cell", stratum, cond, "vsr_ci", stat.get("vsr_ci")])
            writer.writerow(["cell", stratum, cond, "fcr_reported_ci",
                             stat.get("fcr_reported_ci")])
        for s in results.get("H1_strata", []):
            for metric in ("n_pairs", "b_A_only", "c_G_only", "discordant",
                           "chi2", "p_value", "h", "fcr_a", "fcr_g",
                           "direction_correct", "low_discordant"):
                writer.writerow(["H1_McNemar_FCR_A_vs_G", s["stratum"], "", metric, s[metric]])
        for s in results.get("H2_strata", []):
            for metric in ("n_pairs", "b_C_only", "c_F_only", "discordant",
                           "chi2", "p_value", "h", "vsr_c", "vsr_f",
                           "fcr_c", "fcr_f", "direction_correct", "low_discordant"):
                writer.writerow(["H2_McNemar_VSR_C_vs_F", s["stratum"], "", metric, s[metric]])
        for s in results.get("H3_gates", []):
            for metric in ("n_pairs", "fcr_a", "fcr_g", "cpvo_a", "cpvo_g",
                           "direction_correct"):
                writer.writerow(["H3_G_vs_A_tradeoff", s["stratum"], "", metric, s[metric]])
        for hyp, rep in results.get("replication", {}).items():
            writer.writerow(["replication", "", hyp, "code", rep.get("code")])


def write_summary_md(results: Dict[str, Any], path: str) -> None:
    lines: List[str] = []
    lines.append(f"# {STUDY_ID} Confirmatory Analysis Summary (pre-data pipeline)")
    lines.append("")
    lines.append(f"alpha_adj={results['alpha_adj']:.5f}, seoi_h={results['seoi_h']}")
    lines.append("")
    acc = results["attempt_accounting"]
    lines.append("## Attempt accounting")
    lines.append("")
    lines.append(f"- Attempted: {acc['attempted_total']}")
    lines.append(f"- By class: {json.dumps(acc['by_class'], sort_keys=True)}")
    lines.append(f"- LIVE_VALID total: {acc['live_valid_total']} "
                 f"(minimum {PHASE1_MIN_LIVE_VALID}; planned max attempts "
                 f"{PLANNED_MAX_ATTEMPTS_P1} operational only)")
    lines.append(f"- All cells >= {N_PER_CELL_MIN} LIVE_VALID: {results['all_cells_met']}")
    lines.append("")
    lines.append("## Per-cell LIVE_VALID (stratum | condition)")
    lines.append("")
    lines.append("| Cell | n | VSR% [95% CI] | FCR%(reported) [95% CI] | CPVO$ | mean_lat_ms |")
    lines.append("|---|---|---|---|---|---|")
    for key in sorted(results.get("cells", {})):
        stat = results["cells"][key]
        lines.append(f"| {key} | {stat['n']} | {stat['vsr']} {stat['vsr_ci']} | "
                     f"{stat['fcr_reported']} {stat['fcr_reported_ci']} | "
                     f"{stat['cpvo_usd']} | {stat['mean_latency_ms']} |")
    lines.append("")
    lines.append("## Paired McNemar (within-stratum, continuity-corrected)")
    lines.append("")
    for s in results.get("H1_strata", []):
        lines.append(f"- H1 {s['stratum']}: A-vs-G FCR b={s['b_A_only']} c={s['c_G_only']} "
                     f"discordant={s['discordant']}{' LOW_DISCORDANT' if s['low_discordant'] else ''} "
                     f"chi2={s['chi2']} p={s['p_value']} h={s['h']} "
                     f"direction_correct={s['direction_correct']}")
    for s in results.get("H2_strata", []):
        lines.append(f"- H2 {s['stratum']}: C-vs-F VSR b_C={s['b_C_only']} c_F={s['c_F_only']} "
                     f"discordant={s['discordant']}{' LOW_DISCORDANT' if s['low_discordant'] else ''} "
                     f"chi2={s['chi2']} p={s['p_value']} h={s['h']} "
                     f"direction_correct={s['direction_correct']} "
                     f"(FCR_C={s['fcr_c']} FCR_F={s['fcr_f']})")
    lines.append("")
    lines.append("## Replication codes (pre-registered gates)")
    lines.append("")
    for hyp, rep in results.get("replication", {}).items():
        lines.append(f"- {hyp}: {rep.get('code')} ({json.dumps(rep, sort_keys=True)})")
    lines.append("")
    lines.append("")
    lines.append("## Block-segregated McNemar (3-block integrity boundary)")
    lines.append("")
    lines.append("Block 1 = ORIGINAL CONFIRMATORY (b6b7c2d0 fp, dialagram)")
    lines.append("Block 2 = NON-VIABLE (0c588022 fp, openrouter 429-burn, 0 valid)")
    lines.append("Block 3 = POST-AMENDMENT-010 (dfe3513c fp, openrouter paid)")
    lines.append("")
    for key in sorted(results.get("block_results", {}).keys()):
        br = results["block_results"][key]
        status = br.get("status", "")
        if status:
            lines.append(f"- {key}: {status}")
        else:
            lines.append(f"- {key}: n_pairs={br['n_pairs']} b={br.get('b_A_only', br.get('b_C_only', 0))} c={br.get('c_G_only', br.get('c_F_only', 0))} "
                       f"chi2={br.get('chi2')} p={br.get('p_value')} h={br.get('h')} direction_correct={br.get('direction_correct')} (status={br.get('status','OK')})")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Provider-stratified inference only; pooled estimates are exploratory "
                 "and not reported as confirmatory here.")
    lines.append("- Mixed-effects logistic (outcome ~ condition + provider + model + "
                 "(1|workload)) is out of scope for this stdlib pipeline.")
    lines.append("- Unpaired pair slots are rejected from McNemar (counts in results.json "
                 "paired detail). Seed mismatches excluded and counted.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="STUDY-011 confirmatory analysis pipeline (offline, stdlib only).")
    parser.add_argument("--input-dir", required=True,
                        help="Directory of raw run .json/.jsonl records.")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for summary.md + results.json + tables.csv.")
    parser.add_argument("--alpha-adj", type=float, default=DEFAULT_ALPHA_ADJ,
                        help=f"Bonferroni-adjusted alpha (default {DEFAULT_ALPHA_ADJ:.5f}).")
    parser.add_argument("--seoi-h", type=float, default=DEFAULT_SEOI_H,
                        help=f"Smallest effect of interest, Cohen h (default {DEFAULT_SEOI_H}).")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (0 < args.alpha_adj < 1):
        print(f"ERROR: --alpha-adj must be in (0,1), got {args.alpha_adj}",
              file=sys.stderr)
        return 1
    if not (args.seoi_h > 0):
        print(f"ERROR: --seoi-h must be > 0, got {args.seoi_h}", file=sys.stderr)
        return 1
    try:
        raw_runs = load_raw_runs(args.input_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except IntegrityError as exc:
        print(f"INTEGRITY VIOLATION: {exc}", file=sys.stderr)
        return 2
    try:
        results = analyze(raw_runs, alpha_adj=args.alpha_adj, seoi_h=args.seoi_h)
    except IntegrityError as exc:
        print(f"INTEGRITY VIOLATION: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # defensive: never silently succeed
        print(f"ERROR: analysis failed: {exc}", file=sys.stderr)
        return 1
    os.makedirs(args.output_dir, exist_ok=True)
    write_results_json(results, os.path.join(args.output_dir, "results.json"))
    write_tables_csv(results, os.path.join(args.output_dir, "tables.csv"))
    write_summary_md(results, os.path.join(args.output_dir, "summary.md"))
    print(f"Wrote summary.md + results.json + tables.csv to {args.output_dir}")
    print(f"Attempted={results['attempt_accounting']['attempted_total']} "
          f"LIVE_VALID={results['attempt_accounting']['live_valid_total']} "
          f"H1={results['replication']['H1']['code']} "
          f"H2={results['replication']['H2']['code']} "
          f"H3={results['replication']['H3']['code']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
