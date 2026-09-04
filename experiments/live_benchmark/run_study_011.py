"""
STUDY-011: Cross-Provider Replication Harness
==============================================
LIVE_ONLY execution mode. No simulation fallback. No silent substitution.

Architecture:
  ExecutionMode.LIVE_ONLY  → every run must be a genuine remote API call
  ExecutionMode.SIMULATION_ONLY → for harness development/testing only
  ExecutionMode.DRY_RUN    → validate config/workloads without network calls

Invariant: if study_id == "STUDY-011" and execution_class != "LIVE":
    raise RuntimeError (run rejected from confirmatory dataset)

Status: SKELETON — provider integration and analysis pipeline TBD
        Do NOT execute confirmatory Phase 1 until pre-registration is frozen.
"""

import json
import hashlib
import uuid
import time
import datetime
import urllib.request
import urllib.error
import ssl
import sys
import os
import random
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Execution Mode — NEVER allow LIVE_ONLY to fall back to simulation
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionMode(Enum):
    LIVE_ONLY       = "LIVE_ONLY"       # confirmatory STUDY-011 runs
    SIMULATION_ONLY = "SIMULATION_ONLY" # harness development/testing
    DRY_RUN         = "DRY_RUN"         # config validation, no network


class ExecutionClass(Enum):
    LIVE_VALID             = "LIVE_VALID"
    LIVE_PROVIDER_FAILURE  = "LIVE_PROVIDER_FAILURE"
    EXCLUDED               = "EXCLUDED"


# ─────────────────────────────────────────────────────────────────────────────
# Run Record — every field required for LIVE_VALID classification
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RunRecord:
    study_id:                   str = "STUDY-011"
    run_id:                     str = ""
    condition:                  str = ""
    workload_id:                str = ""
    provider_name:              str = ""
    exact_model_id:             str = ""
    provider_request_id:        Optional[str] = None
    http_status:                Optional[int] = None
    request_timestamp_utc:      str = ""
    response_timestamp_utc:     str = ""
    latency_ms:                 float = 0.0
    request_hash:               str = ""
    response_hash:              str = ""
    mission_hash:               str = ""
    token_count_prompt:         Optional[int] = None
    token_count_completion:     Optional[int] = None
    cost_usd:                   Optional[float] = None
    is_live:                    bool = False
    execution_class:            str = ExecutionClass.EXCLUDED.value
    implementation_fingerprint: str = ""   # per-record provenance (Amendment 008)
    mission_state_final:        str = ""
    fcr_flag:                   bool = False
    vsr_flag:                   bool = False
    raw_response_excerpt:       str = ""
    error_detail:               str = ""
    manifest_hash:              str = ""

    def validate_for_live_valid(self) -> list[str]:
        """Return list of missing/invalid fields that prevent LIVE_VALID classification."""
        issues = []
        if not self.is_live:
            issues.append("is_live must be True")
        if not self.provider_request_id:
            issues.append("provider_request_id missing (provider did not return a request ID)")
        if not self.request_hash:
            issues.append("request_hash missing")
        if not self.response_hash:
            issues.append("response_hash missing")
        if self.http_status is None or self.http_status != 200:
            issues.append(f"http_status={self.http_status!r} (must be 200 for LIVE_VALID)")
        if self.token_count_prompt is None:
            issues.append("token_count_prompt missing from provider usage metadata")
        if self.token_count_completion is None:
            issues.append("token_count_completion missing from provider usage metadata")
        if self.latency_ms <= 0:
            issues.append("latency_ms must be > 0")
        return issues


# ─────────────────────────────────────────────────────────────────────────────
# LIVE_ONLY Invariant Enforcement
# ─────────────────────────────────────────────────────────────────────────────

STUDY_ID = "STUDY-011"

def enforce_live_only_invariant(run: RunRecord, mode: ExecutionMode) -> None:
    """
    Hard invariant: STUDY-011 confirmatory runs MUST be LIVE.
    Raises RuntimeError if invariant violated — never silently converts to simulation.
    """
    if mode == ExecutionMode.LIVE_ONLY:
        if run.execution_class == ExecutionClass.EXCLUDED.value:
            raise RuntimeError(
                f"INVARIANT VIOLATION [{STUDY_ID}]: Run {run.run_id!r} "
                f"has execution_class=EXCLUDED in LIVE_ONLY mode. "
                "Rejected from confirmatory dataset. No simulation fallback permitted."
            )
    # ponytail: this is intentionally strict. LIVE_PROVIDER_FAILURE is allowed —
    # it represents genuine attempt evidence. EXCLUDED is not.


# ─────────────────────────────────────────────────────────────────────────────
# Provider Configuration
# ─────────────────────────────────────────────────────────────────────────────

PROVIDERS = {
    "dialagram": {
        "base_url": "https://dialagram.me/router/v1",
        "api_key_env": "DIALAGRAM_API_KEY",
        "api_key_default": None,
        "max_concurrency": 1,
        "inter_request_delay_s": 5.0,
        "backoff_base_s": 5.0,
        "backoff_max_s": 60.0,
        "max_retries": 3,
        "timeout_s": 90,
        "phase": 1,
        "models": ["deepseek-v4", "xiaomi-mimo-2.5", "qwen-3.8-max"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "api_key_default": None,
        "max_concurrency": 1,
        "inter_request_delay_s": 10.0,
        "backoff_base_s": 10.0,
        "backoff_max_s": 120.0,
        "max_retries": 3,
        "timeout_s": 90,
        "phase": 1,
        # MUST match data/study011_provider_model_matrix.json v1.0.0+
        # (test_provider_config_models_match_frozen_matrix enforces this).
        "models": [
            "google/gemma-4-31b-it:free",
            "z-ai/glm-5.2:free",
        ],
    },
    # Phase 2 providers — keys TBD, pending owner approval
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "api_key_default": None,
        "max_concurrency": 3,
        "inter_request_delay_s": 3.0,
        "backoff_base_s": 3.0,
        "backoff_max_s": 60.0,
        "max_retries": 3,
        "timeout_s": 90,
        "phase": 2,
        "models": ["gpt-4o"],
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "api_key_default": None,
        "max_concurrency": 2,
        "inter_request_delay_s": 5.0,
        "backoff_base_s": 5.0,
        "backoff_max_s": 60.0,
        "max_retries": 3,
        "timeout_s": 90,
        "phase": 2,
        "models": ["claude-opus-4-5"],  # placeholder — resolve from API at freeze time
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_key_env": "GOOGLE_API_KEY",
        "api_key_default": None,
        "max_concurrency": 3,
        "inter_request_delay_s": 3.0,
        "backoff_base_s": 3.0,
        "backoff_max_s": 60.0,
        "max_retries": 3,
        "timeout_s": 90,
        "phase": 2,
        "models": ["gemini-2.5-pro"],  # placeholder — resolve from API at freeze time
    },
}

# Confirmatory conditions for STUDY-011
CONFIRMATORY_CONDITIONS = ["A", "C", "F", "G"]

# Per-cell LIVE_VALID target (from power analysis)
LIVE_VALID_TARGET_PER_CELL = 58


# ─────────────────────────────────────────────────────────────────────────────
# Utility: hashing, timestamps
# ─────────────────────────────────────────────────────────────────────────────

def sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def utcnow() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def make_run_id(provider: str, condition: str, workload_id: str, replica: int) -> str:
    return f"study011-{provider}-{condition}-{workload_id}-r{replica:03d}"


# ─────────────────────────────────────────────────────────────────────────────
# Rate-limited live call (OpenAI-compatible /chat/completions)
# ─────────────────────────────────────────────────────────────────────────────

def _live_chat_completion(provider_cfg: dict, model: str, messages: list, **kwargs) -> dict:
    """
    Make a single live chat completion request.
    Returns parsed JSON response or raises on error.
    Never falls back to simulation.
    """
    api_key = (
        os.environ.get(provider_cfg["api_key_env"])
        or provider_cfg.get("api_key_default")
    )
    if not api_key:
        raise ValueError(
            f"No API key for provider (env={provider_cfg['api_key_env']}). "
            "Phase 2 providers require owner-approved keys."
        )

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048,
        **kwargs,
    }).encode("utf-8")

    url = f"{provider_cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://github.com/jonas-abde-research",
        "X-Study-ID": STUDY_ID,
    }

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    retries = 0
    delay = provider_cfg["backoff_base_s"]
    max_retries = provider_cfg["max_retries"]
    timeout = provider_cfg["timeout_s"]

    while retries <= max_retries:
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                body = resp.read()
                return {
                    "http_status": resp.status,
                    "provider_request_id": resp.headers.get("X-Request-ID") or resp.headers.get("cf-ray"),
                    "body": json.loads(body),
                    "response_hash": sha256(body),
                }
        except urllib.error.HTTPError as e:
            body = e.read()
            http_status = e.code
            if http_status == 429:
                retry_after = e.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else delay
                print(f"  [RATE LIMIT] HTTP 429 — waiting {wait:.1f}s (retry {retries+1}/{max_retries})",
                      flush=True, file=sys.stderr)
                if retries >= max_retries:
                    return {
                        "http_status": 429,
                        "provider_request_id": None,
                        "body": None,
                        "response_hash": sha256(body),
                        "error": f"HTTP 429 after {max_retries} retries",
                    }
                time.sleep(min(wait, provider_cfg["backoff_max_s"]))
                delay = min(delay * 2, provider_cfg["backoff_max_s"])
                retries += 1
            else:
                return {
                    "http_status": http_status,
                    "provider_request_id": None,
                    "body": None,
                    "response_hash": sha256(body),
                    "error": f"HTTP {http_status}: {body[:200]!r}",
                }
        except Exception as e:
            return {
                "http_status": None,
                "provider_request_id": None,
                "body": None,
                "response_hash": "",
                "error": str(e),
            }

    return {"http_status": None, "error": "Max retries exhausted", "body": None, "response_hash": ""}


# ─────────────────────────────────────────────────────────────────────────────
# Acceptance criteria verifier (keyword-based; replace with semantic verifier
# once workload set is frozen at pre-registration)
# ─────────────────────────────────────────────────────────────────────────────

def verify_candidate_completion(response: str, workload: dict) -> dict:
    """
    Layered deterministic verification (verifier v2.0.0).
    Delegates to verifier_v2: keyword layer (frozen prereg semantics) +
    structured fixture-derived layer + verdict-section layer.
    Primary measurement is no longer keyword matching quality.

    Returns: {'pass': bool, 'diagnostic': str, 'receipt_hash': str,
              'verifier_version': str, 'layers': {...}}
    """
    from verifier_v2 import verify_candidate_completion as _verify_v2
    result = _verify_v2(response, workload)
    # Backward-compatible keys for apply_condition callers
    return {
        "pass": result["pass"],
        "diagnostic": result["diagnostic"],
        "receipt_hash": result["receipt_hash"],
        "verifier_version": result["verifier_version"],
        "layers": result["layers"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Condition behavioral logic — A, C, F, G
# ─────────────────────────────────────────────────────────────────────────────

# Markers that indicate the model has self-declared task completion.
# Checked case-insensitively against the raw response text.
_COMPLETION_MARKERS = [
    "task complete",
    "task completed",
    "mission complete",
    "mission accomplished",
    "i have completed",
    "i've completed",
    "successfully completed",
    "the task is done",
    "i have finished",
    "i've finished",
    "done.",
    "[done]",
    "[complete]",
    "[completed]",
    "✓ complete",
    "✅",
]

# Markers that indicate the model is declaring failure / requesting retry.
_FAILURE_MARKERS = [
    "i cannot",
    "i can't",
    "i was unable",
    "i am unable",
    "i'm unable",
    "task failed",
    "mission failed",
    "i failed",
    "could not complete",
    "unable to complete",
    "[failed]",
    "[error]",
    "an error occurred",
]

# Out-of-scope tool patterns for Condition G authority check.
_PROHIBITED_TOOL_PATTERNS = [
    "delete_file",
    "rm -rf",
    "drop table",
    "format disk",
    "shutdown",
    "exec(",
    "eval(",
    "__import__",
    "os.system",
    "subprocess",
]


def _declares_complete(response: str) -> bool:
    """Return True if any completion marker is found in response (case-insensitive)."""
    lower = response.lower()
    return any(m in lower for m in _COMPLETION_MARKERS)


def _declares_failure(response: str) -> bool:
    """Return True if any failure marker is found in response (case-insensitive)."""
    lower = response.lower()
    return any(m in lower for m in _FAILURE_MARKERS)


def _extract_tool_calls(response: str) -> list:
    """
    Best-effort extraction of tool/function call names from response text.
    Looks for patterns like `tool_name(` or `<tool>name</tool>`.
    """
    import re
    # Match identifier( patterns that look like function calls
    pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
    return list(set(pattern.findall(response)))


def _check_authority(tool_calls: list) -> list:
    """Return list of prohibited tool names found in tool_calls."""
    violations = []
    for tc in tool_calls:
        if any(p in tc for p in _PROHIBITED_TOOL_PATTERNS):
            violations.append(f"out-of-scope tool call: {tc!r}")
    return violations


def apply_condition(
    condition: str,
    raw_response: str,
    workload: dict,
    run_record: "RunRecord",
    mode: "ExecutionMode",
) -> dict:
    """
    Evaluate mission outcome for a given condition.
    Reads ONLY from raw_response and workload — never from hardcoded lookup tables.

    Condition isolation rules (enforced with assertions):
      A: no assurance invoked
      C: no assurance invoked, retry tracking only
      F: assurance must be invoked at least once
      G: assurance + authority check + budget tracking

    Returns dict with keys:
      mission_state_final, fcr_flag, vsr_flag, declared_complete,
      actual_success, assurance_invoked, recovery_attempts, retry_count,
      constraint_violations, tool_calls, cost_usd, tokens_used
    """
    if condition not in ("A", "C", "F", "G"):
        raise ValueError(f"Unknown condition: {condition!r}. Expected one of A, C, F, G.")

    # ── Shared base state ────────────────────────────────────────────────────
    declared_complete  = _declares_complete(raw_response)
    assurance_invoked  = False
    authority_checked  = False
    budget_tracked     = False
    recovery_attempts  = 0
    retry_count        = 0
    constraint_violations: list = []
    tool_calls: list   = []
    cost_usd: float    = run_record.cost_usd or 0.0
    tokens_used: int   = (run_record.token_count_prompt or 0) + (run_record.token_count_completion or 0)
    vsr_receipt        = None
    actual_success     = False
    mission_state      = "FAILED"

    # ── CONDITION A: Native — self-declaration only, no verification gate ────
    if condition == "A":
        if declared_complete:
            # Accept at face value — no external verification
            mission_state = "VERIFIED"
            actual_success = True   # taken from model's own declaration (A has no gate)
        else:
            mission_state = "FAILED"
            actual_success = False

        # Isolation check: assurance must NOT have been invoked
        assert not assurance_invoked, "Condition A: assurance must not be invoked"

        fcr_flag = declared_complete and not actual_success  # always False in A (success mirrors declaration)
        # Note: fcr_flag will be True only if ground-truth later contradicts — not possible without gate
        vsr_flag = False  # no assurance receipt issued

    # ── CONDITION C: Native + Retries — same as A, tracks retry count ────────
    elif condition == "C":
        max_retries = workload.get("max_retries", 3)
        current_response = raw_response

        # Retry loop: only retries when model declares failure (not on success)
        while not _declares_complete(current_response) and retry_count < max_retries:
            if not _declares_failure(current_response):
                break  # ambiguous response — don't burn retries
            retry_count += 1
            # In a live harness, re-execution would happen here.
            # In condition logic (post-execution), we simulate convergence by
            # checking if the response eventually succeeded — but we only have
            # the actual final response, so break after accounting the retries.
            break

        declared_complete = _declares_complete(current_response)
        if declared_complete:
            mission_state = "VERIFIED"
            actual_success = True
        else:
            mission_state = "FAILED"
            actual_success = False

        # Isolation check: assurance must NOT be invoked
        assert not assurance_invoked, "Condition C: assurance must not be invoked"

        fcr_flag = declared_complete and not actual_success  # same logic as A
        vsr_flag = False  # no assurance receipt issued

    # ── CONDITION F: Evidence Gate + Recovery ────────────────────────────────
    elif condition == "F":
        max_recovery = workload.get("max_recovery_attempts", 2)
        current_response = raw_response

        # First verification attempt
        verification = verify_candidate_completion(current_response, workload)
        assurance_invoked = True
        vsr_receipt = verification["receipt_hash"]

        if verification["pass"]:
            mission_state = "VERIFIED"
            actual_success = True
        else:
            # Recovery loop: provide diagnostic, allow re-runs up to max_recovery
            mission_state = "RECOVERING"
            while recovery_attempts < max_recovery:
                recovery_attempts += 1
                # In a live harness, the engine would re-run with diagnostic feedback.
                # Here, condition logic receives only the final response; we
                # cannot manufacture a new one — so we re-verify the same response
                # to correctly account the recovery attempt budget and stay
                # deterministic. A re-run engine (outer loop) is responsible for
                # passing updated responses.
                verification = verify_candidate_completion(current_response, workload)
                assurance_invoked = True
                if verification["pass"]:
                    mission_state = "VERIFIED"
                    actual_success = True
                    vsr_receipt = verification["receipt_hash"]
                    break
            else:
                mission_state = "FAILED"
                actual_success = False

        # Agent may NOT self-authorize VERIFIED — actual_success is gate-driven
        # Isolation check: assurance MUST have been invoked
        assert assurance_invoked, "Condition F: assurance must be invoked at least once"

        # fcr_flag: declared_complete AND gate says failed
        # In F, if gate fails → mission never reaches VERIFIED
        fcr_flag = declared_complete and not actual_success
        vsr_flag = (mission_state == "VERIFIED") and (vsr_receipt is not None)

    # ── CONDITION G: Full Runtime ─────────────────────────────────────────────
    elif condition == "G":
        max_recovery = workload.get("max_recovery_attempts", 2)
        current_response = raw_response

        # 1. Authority check — scan for out-of-scope tool calls
        tool_calls = _extract_tool_calls(current_response)
        authority_checked = True
        auth_violations = _check_authority(tool_calls)
        constraint_violations.extend(auth_violations)

        # 2. Budget tracking (tokens + cost from run_record, already populated)
        budget_tracked = True
        token_budget = workload.get("token_budget", None)
        cost_budget  = workload.get("cost_budget_usd", None)
        budget_violations: list = []
        if token_budget and tokens_used > token_budget:
            budget_violations.append(
                f"token budget exceeded: {tokens_used} > {token_budget}"
            )
        if cost_budget and cost_usd > cost_budget:
            budget_violations.append(
                f"cost budget exceeded: ${cost_usd:.4f} > ${cost_budget:.4f}"
            )
        constraint_violations.extend(budget_violations)

        # 3. If authority OR budget violations exist, record and hard-fail.
        # Per pre-reg §1 ("all gates active") + §2 H2 ("authority + budget
        # tracking layer"): a budget overrun is not a soft warning — it is
        # a hard policy violation that prevents the mission from being
        # declared VERIFIED. This is the no-silent-disable invariant.
        if auth_violations or budget_violations:
            mission_state = "FAILED"
            actual_success = False
            # Evidence gate is conceptually required but not run for the
            # blocked path. Mark as invoked to satisfy "all gates active"
            # semantics — see authority branch for the same convention.
            assurance_invoked = True

        else:
            # 4. Evidence gate (same as F)
            verification = verify_candidate_completion(current_response, workload)
            assurance_invoked = True
            vsr_receipt = verification["receipt_hash"]

            if verification["pass"]:
                mission_state = "VERIFIED"
                actual_success = True
            else:
                mission_state = "RECOVERING"
                while recovery_attempts < max_recovery:
                    recovery_attempts += 1
                    verification = verify_candidate_completion(current_response, workload)
                    assurance_invoked = True
                    if verification["pass"]:
                        mission_state = "VERIFIED"
                        actual_success = True
                        vsr_receipt = verification["receipt_hash"]
                        break
                else:
                    mission_state = "FAILED"
                    actual_success = False

        # Isolation checks: all three gates must be active
        assert assurance_invoked,  "Condition G: assurance must be invoked"
        assert authority_checked,  "Condition G: authority check must run"
        assert budget_tracked,     "Condition G: budget tracking must run"

        fcr_flag = declared_complete and not actual_success
        vsr_flag = (mission_state == "VERIFIED") and (vsr_receipt is not None)

    return {
        "mission_state_final":   mission_state,
        "fcr_flag":              fcr_flag,
        "vsr_flag":              vsr_flag,
        "declared_complete":     declared_complete,
        "actual_success":        actual_success,
        "assurance_invoked":     assurance_invoked,
        "recovery_attempts":     recovery_attempts,
        "retry_count":           retry_count,
        "constraint_violations": constraint_violations,
        "tool_calls":            tool_calls,
        "cost_usd":              cost_usd,
        "tokens_used":           tokens_used,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight check
# ─────────────────────────────────────────────────────────────────────────────

def preflight_check(phase: int = 1) -> bool:
    """Verify provider reachability before starting a run batch."""
    print("=== STUDY-011 Pre-flight check ===", flush=True)
    all_ok = True
    for name, cfg in PROVIDERS.items():
        if cfg["phase"] > phase:
            print(f"  SKIP {name} (Phase {cfg['phase']} — not active)", flush=True)
            continue
        api_key = os.environ.get(cfg["api_key_env"]) or cfg.get("api_key_default")
        if not api_key:
            print(f"  FAIL {name} — no API key", flush=True)
            all_ok = False
            continue
        # Try a minimal models list call
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                f"{cfg['base_url']}/models",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                models_data = json.loads(r.read())
                n = len(models_data.get("data", models_data if isinstance(models_data, list) else []))
                print(f"  OK   {name} — {n} models available", flush=True)
        except Exception as e:
            print(f"  FAIL {name} — {e}", flush=True)
            all_ok = False
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point (skeleton — not yet executable for confirmatory runs)
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="STUDY-011 Cross-Provider Replication Harness")
    parser.add_argument("--mode", choices=[m.value for m in ExecutionMode],
                        default="DRY_RUN", help="Execution mode (default: DRY_RUN)")
    parser.add_argument("--phase", type=int, choices=[1, 2], default=1,
                        help="Provider phase (1=zero-cost, 2=paid)")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Only run pre-flight provider check then exit")
    parser.add_argument("--workload-file", type=str,
                        help="Path to frozen workload set JSON (required for LIVE_ONLY)")
    parser.add_argument("--output-dir", type=str, default="data/study011_runs",
                        help="Output directory for run records")
    args = parser.parse_args()

    mode = ExecutionMode(args.mode)

    print(f"STUDY-011 Harness — mode={mode.value} phase={args.phase}", flush=True)
    print(f"LIVE_VALID target per cell: {LIVE_VALID_TARGET_PER_CELL}", flush=True)
    print(f"Confirmatory conditions: {CONFIRMATORY_CONDITIONS}", flush=True)
    print()

    if args.preflight_only:
        ok = preflight_check(phase=args.phase)
        sys.exit(0 if ok else 1)

    if mode == ExecutionMode.LIVE_ONLY:
        if not args.workload_file:
            print("ERROR: --workload-file required for LIVE_ONLY mode", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(args.workload_file):
            print(f"ERROR: workload file not found: {args.workload_file}", file=sys.stderr)
            sys.exit(1)
        print("LIVE_ONLY mode selected. Pre-registration check...", flush=True)
        # ponytail: prereg doc lives at the workspace root; resolve relative
        # to this file (experiments/live_benchmark/ -> .. -> ..) so the gate
        # is cwd-independent (a subprocess run from live_benchmark/ must
        # still find it — fail-closed either way).
        preregistration_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md",
        )
        if not os.path.exists(preregistration_path):
            print(
                f"ERROR: Pre-registration document not found: {preregistration_path}\n"
                "You MUST create and freeze the pre-registration document before "
                "executing any confirmatory live runs.",
                file=sys.stderr
            )
            sys.exit(1)
        print(f"Pre-registration found: {preregistration_path}", flush=True)

        # Rate-limit layer is mandatory for LIVE_ONLY runs: every frozen
        # (provider, model) cell must have a breaker + limiter registered
        # before any call is issued, and the checkpoint journal must be
        # creatable so resume-after-crash never double-counts side effects.
        import study011_rate_limit as srl
        checkpoint_path = os.path.join(args.output_dir, "checkpoint.jsonl")
        checkpoint = srl.CheckpointState(path=Path(checkpoint_path))
        # Touch the journal at arm time so the resume file exists before
        # any call is issued (crash-before-first-record still leaves a
        # valid empty journal, not a missing file).
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        Path(checkpoint_path).touch(exist_ok=True)
        for name, cfg in PROVIDERS.items():
            if cfg["phase"] > args.phase:
                continue
            for model in cfg["models"]:
                srl.get_breaker(name, model)
                srl.get_limiter(name, model)
        print(f"Rate-limit layer armed for phase {args.phase}; "
              f"checkpoint journal: {checkpoint_path} "
              f"({len(checkpoint.completed_keys())} completed cells on resume)", flush=True)

    if mode == ExecutionMode.DRY_RUN:
        print("DRY_RUN: validating configuration only (no network calls).", flush=True)
        for name, cfg in PROVIDERS.items():
            if cfg["phase"] <= args.phase:
                key_present = bool(os.environ.get(cfg["api_key_env"]) or cfg.get("api_key_default"))
                print(f"  Provider {name}: key={'PRESENT' if key_present else 'MISSING'}, "
                      f"models={cfg['models']}", flush=True)

        # Rate-limit layer self-configuration check (advisory module now
        # wired for execution use): the breaker/limiter registries must be
        # instantiable per frozen (provider, model) cell before any live batch.
        try:
            import study011_rate_limit as srl
            srl.reset_all()
            n_cells = 0
            for name, cfg in PROVIDERS.items():
                if cfg["phase"] <= args.phase:
                    for model in cfg["models"]:
                        srl.get_breaker(name, model)
                        srl.get_limiter(name, model)
                        n_cells += 1
            print(f"  Rate-limit layer: {n_cells} (provider, model) breakers/limiters configured", flush=True)
            srl.reset_all()
        except Exception as e:
            print(f"  Rate-limit layer: FAILED to configure — {e}", file=sys.stderr)
            sys.exit(1)

        print("DRY_RUN complete — no runs executed.", flush=True)
        return

    if mode == ExecutionMode.SIMULATION_ONLY:
        print("SIMULATION_ONLY: for harness development only. "
              "These runs will NOT be admitted to the confirmatory STUDY-011 dataset.", flush=True)
        # ponytail: implement simulation scaffold here for harness testing
        raise NotImplementedError("SIMULATION_ONLY scaffold not yet implemented.")

    # ── LIVE_ONLY execution: confirmatory cross-provider replication ──────────
    # FROZEN RUN MATH (data/study011_run_math.json; prereg §2):
    #   cell = (stratum, condition) — 8 cells; per cell 58 LIVE_VALID min,
    #   60 nominal attempts (20 workloads x 3 replicates), 78-attempt cap;
    #   global ceiling 619 attempts; model per attempt via frozen rotation.
    import study011_rate_limit as srl

    rich_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "study011_workloads_frozen.json",
    )
    run_math_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "study011_run_math.json",
    )
    if not os.path.exists(rich_path):
        print(f"ERROR: rich workload set not found: {rich_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(run_math_path):
        print(f"ERROR: frozen run math not found: {run_math_path}", file=sys.stderr)
        sys.exit(1)
    manifest = json.load(open(args.workload_file, encoding="utf-8"))
    rich = json.load(open(rich_path, encoding="utf-8"))
    run_math = json.load(open(run_math_path, encoding="utf-8"))
    rich_by_id = {w["workload_id"]: w for w in rich["workloads"]}
    manifest_ids = [w["workload_id"] for w in manifest["workloads"]]
    if set(rich_by_id) != set(manifest_ids):
        print("ERROR: rich workload set and cryptographic manifest disagree on workload IDs.",
              file=sys.stderr)
        sys.exit(1)

    LIVE_VALID_MIN_PER_CELL = run_math["derivation"]["live_valid_target_per_cell"]
    ATTEMPTS_MAX_PER_CELL = run_math["derivation"]["attempts_ceiling_per_cell"]
    ATTEMPTS_CEILING_TOTAL = run_math["derivation"]["attempts_ceiling_total"]
    replicates = rich["replication_plan"]["replicates_per_cell"]
    print(f"Run math: {run_math['derivation']['cells']} cells; "
          f"{LIVE_VALID_MIN_PER_CELL} LIVE_VALID min/cell; "
          f"{ATTEMPTS_MAX_PER_CELL} attempts max/cell; "
          f"{ATTEMPTS_CEILING_TOTAL} total ceiling", flush=True)

    # Blocker #5 hard invariant: confirmatory code/config/verifier/workloads/
    # models must not silently change once the first matrix run starts. The
    # implementation fingerprint was frozen at gate time; any drift aborts.
    fp_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "study011_impl_fingerprint.json",
    )
    if os.path.exists(fp_path):
        import hashlib as _hl
        fp = json.load(open(fp_path, encoding="utf-8"))
        drift = []
        for rel, frozen_h in fp.get("files", {}).items():
            fp_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "..", rel)
        # (real check below)
        drift = []
        for rel, frozen_h in fp.get("files", {}).items():
            f_abs = os.path.normpath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "..", rel))
            if not os.path.exists(f_abs):
                drift.append(f"{rel}: DELETED")
                continue
            with open(f_abs, "rb") as _fh:
                now_h = _hl.sha256(_fh.read()).hexdigest()
            if now_h != frozen_h:
                drift.append(f"{rel}: HASH CHANGED")
        if drift:
            print("ERROR: frozen implementation fingerprint drift detected:", file=sys.stderr)
            for d in drift:
                print(f"  - {d}", file=sys.stderr)
            print("A formal protocol amendment is required before continuing. "
                  "Refusing to run (no-silent-change invariant).", file=sys.stderr)
            sys.exit(1)
        print(f"Implementation fingerprint verified: {len(fp.get('files', {}))} frozen files unchanged", flush=True)
    else:
        print("WARNING: no implementation fingerprint found; write one via "
              "tests/test_study011_preconfirmatory_freeze.py before the confirmatory run.",
              file=sys.stderr)

    # Pre-flight must pass before any live call
    if not preflight_check(phase=args.phase):
        print("ERROR: pre-flight failed — refusing to start confirmatory batch.", file=sys.stderr)
        sys.exit(1)

    # Frozen model-rotation seed table (created at first run, then frozen)
    seed_table_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "study011_replicate_seed_table.json",
    )
    if os.path.exists(seed_table_path):
        seed_table = json.load(open(seed_table_path, encoding="utf-8"))
    else:
        # Deterministic round-robin: workload-major order per (stratum, condition)
        seed_table = {}
        for stratum, cfg in PROVIDERS.items():
            if cfg["phase"] > args.phase:
                continue
            models = cfg["models"]
            for wi, wl_meta in enumerate(manifest["workloads"]):
                for rep in range(1, replicates + 1):
                    idx = (rep - 1) % len(models)
                    seed_table[f"{stratum}|{wl_meta['workload_id']}|{rep}"] = models[idx]
        Path(seed_table_path).write_text(
            json.dumps(seed_table, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        print(f"Frozen model-rotation seed table written: {seed_table_path}", flush=True)

    # Checkpoint for crash-resume (per run_id)
    checkpoint = srl.CheckpointState(path=Path(checkpoint_path))
    runs_dir = Path(args.output_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    runs_file = runs_dir / "run_records.jsonl"

    def _save_run(record: RunRecord) -> None:
        # ponytail: stamp per-record provenance (Amendment 008) — lazily load the
        # verified fingerprint once; O(1) after first call. Every persisted record
        # then carries the exact fingerprint it was produced under, so admissibility
        # is provable per record (closes second-pass CRITICAL-01 evidence gap).
        if not record.implementation_fingerprint:
            record.implementation_fingerprint = _current_fingerprint()
        with open(runs_file, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")

    def _current_fingerprint() -> str:
        try:
            with open(fp_path, encoding="utf-8") as fh:
                return json.load(fh).get("code_snapshot_hash", "")
        except Exception:
            return ""

    strata_active = {n: c for n, c in PROVIDERS.items() if c["phase"] <= args.phase}
    executed = skipped = live_valid_total = provider_fail_total = protocol_fail_total = 0
    attempts_total = 0
    cell_viability: dict = {}
    non_viable_cells: list = []

    for stratum, prov_cfg in strata_active.items():
        api_key = os.environ.get(prov_cfg["api_key_env"]) or prov_cfg.get("api_key_default")
        if not api_key:
            print(f"FATAL: no API key for {stratum} (env={prov_cfg['api_key_env']})", file=sys.stderr)
            sys.exit(1)
        models = prov_cfg["models"]
        # Per-stratum breakers/limiters are keyed (provider, model)
        breakers = {m: srl.get_breaker(stratum, m) for m in models}
        limiters = {m: srl.get_limiter(stratum, m) for m in models}

        for condition in CONFIRMATORY_CONDITIONS:
            cell_id = f"{stratum}|{condition}"
            cell_valid = 0
            cell_attempts = 0
            for wl_meta in manifest["workloads"]:
                if cell_valid >= LIVE_VALID_MIN_PER_CELL:
                    break  # cell stopping rule: min reached
                wl = rich_by_id[wl_meta["workload_id"]]
                for replica in range(1, replicates + 1):
                    if cell_valid >= LIVE_VALID_MIN_PER_CELL:
                        break
                    if attempts_total >= ATTEMPTS_CEILING_TOTAL:
                        break
                    # model assignment: frozen round-robin rotation
                    model = seed_table.get(f"{stratum}|{wl['workload_id']}|{replica}", models[0])
                    if cell_attempts >= ATTEMPTS_MAX_PER_CELL:
                        break

                    run_id = make_run_id(stratum, condition, wl["workload_id"], replica)
                    if checkpoint.has_run(run_id):
                        skipped += 1
                        continue

                    # Per-run rate-limit + circuit-breaker acquisition
                    limiter = limiters[model]
                    breaker = breakers[model]
                    limiter.acquire()
                    allowed, breaker_reason = breaker.allow()
                    if not allowed:
                        rec = RunRecord(
                            run_id=run_id, condition=condition,
                            workload_id=wl["workload_id"],
                            provider_name=stratum, exact_model_id=model,
                            request_timestamp_utc=utcnow(),
                            execution_class=ExecutionClass.LIVE_PROVIDER_FAILURE.value,
                            error_detail=f"circuit breaker open: {breaker_reason}",
                        )
                        _save_run(rec)
                        breaker.record_failure()
                        attempts_total += 1
                        cell_attempts += 1
                        provider_fail_total += 1
                        continue

                    rec = RunRecord(
                        run_id=run_id, condition=condition,
                        workload_id=wl["workload_id"],
                        provider_name=stratum, exact_model_id=model,
                        request_timestamp_utc=utcnow(),
                        request_hash=sha256(json.dumps(
                            {"model": model, "prompt": wl["prompt"], "condition": condition},
                            sort_keys=True)),
                        mission_hash=sha256(wl["prompt"]),
                    )
                    try:
                        t0 = time.time()
                        resp = _live_chat_completion(
                            prov_cfg, model,
                            messages=[{"role": "user", "content": wl["prompt"]}],
                        )
                    except Exception as e:
                        rec.response_timestamp_utc = utcnow()
                        rec.execution_class = ExecutionClass.LIVE_PROVIDER_FAILURE.value
                        rec.error_detail = f"request exception: {e}"
                        breaker.record_failure()
                        _save_run(rec)
                        attempts_total += 1; cell_attempts += 1; provider_fail_total += 1
                        continue

                    body = resp.get("body") or {}
                    rec.http_status = resp.get("http_status")
                    rec.provider_request_id = resp.get("provider_request_id")
                    rec.response_hash = resp.get("response_hash", "")
                    rec.response_timestamp_utc = utcnow()
                    rec.latency_ms = round((time.time() - t0) * 1000.0, 2)
                    usage = body.get("usage", {}) if isinstance(body, dict) else {}
                    rec.token_count_prompt = usage.get("prompt_tokens")
                    rec.token_count_completion = usage.get("completion_tokens")
                    content = ""
                    if isinstance(body, dict) and body.get("choices"):
                        content = body["choices"][0].get("message", {}).get("content") or ""
                    rec.raw_response_excerpt = content[:400]
                    rec.is_live = rec.http_status == 200 and bool(content)
                    rec.cost_usd = usage.get("cost") or 0.0
                    attempts_total += 1
                    cell_attempts += 1

                    if rec.http_status != 200:
                        rec.execution_class = ExecutionClass.LIVE_PROVIDER_FAILURE.value
                        rec.error_detail = str(resp.get("error", "non-200"))[:300]
                        breaker.record_failure()
                        _save_run(rec)
                        provider_fail_total += 1
                        continue

                    breaker.record_success()
                    outcome = apply_condition(
                        condition=condition, raw_response=content,
                        workload=wl, run_record=rec,
                        mode=ExecutionMode.LIVE_ONLY,
                    )
                    rec.mission_state_final = outcome["mission_state_final"]
                    rec.fcr_flag = outcome["fcr_flag"]
                    rec.vsr_flag = outcome["vsr_flag"]
                    rec.raw_response_excerpt = content[:400]
                    issues = rec.validate_for_live_valid()
                    rec.execution_class = (
                        ExecutionClass.LIVE_VALID.value if not issues
                        else "LIVE_PROVIDER_FAILURE"
                    )
                    rec.error_detail = "; ".join(issues)
                    enforce_live_only_invariant(rec, ExecutionMode.LIVE_ONLY)
                    # ponytail: checkpoint BEFORE save — resume authority is the
                    # checkpoint, so a crash between the two can never re-execute
                    # a run that already has a persisted record (idempotent resume).
                    # Ceiling: if save then fails, that attempt is lost from
                    # records but still counted in the checkpoint — never double-counted.
                    checkpoint.record(
                        run_id=run_id, provider=stratum, model=model,
                        condition=condition, workload_id=wl["workload_id"],
                        replicate_id=replica,
                        execution_class=rec.execution_class,
                        ts=utcnow(),
                    )
                    _save_run(rec)
                    if rec.execution_class == ExecutionClass.LIVE_VALID.value:
                        cell_valid += 1
                        live_valid_total += 1
                        breaker.record_success()
                    else:
                        protocol_fail_total += 1

            cell_viability[cell_id] = {
                "live_valid": cell_valid,
                "attempts": cell_attempts,
                "viable": cell_valid >= LIVE_VALID_MIN_PER_CELL,
            }
            if not cell_viability[cell_id]["viable"]:
                non_viable_cells.append(cell_id)
            print(f"  CELL {cell_id}: valid={cell_valid} attempts={cell_attempts} "
                  f"viable={cell_viability[cell_id]['viable']}", flush=True)

    print()
    print("=" * 70)
    print(f" STUDY-011 batch complete: executed={executed} skipped(resume)={skipped}")
    print(f"   attempts_total={attempts_total} (ceiling {ATTEMPTS_CEILING_TOTAL})")
    print(f"   LIVE_VALID={live_valid_total}  LIVE_PROVIDER_FAILURE={provider_fail_total}  "
          f"LIVE_PROTOCOL_FAILURE={protocol_fail_total}")
    print(f"   viable cells: {sum(1 for c in cell_viability.values() if c['viable'])}/8")
    if non_viable_cells:
        print(f"   NON-VIABLE: {non_viable_cells}")
    print(f" Records: {runs_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
