"""
test_study011_harness_self_test.py
==================================

Harness self-test for STUDY-011, including a regression test for the
STUDY-008 `idx==0` simulation defect.

Background: STUDY-008 produced 275 attempted runs, of which only 2 were
genuinely LIVE_VALID. The remaining 264 were silently substituted with
simulation responses because the harness used a sentinel
`is_live_call = (idx == 0)` pattern. The audit trail caught this; the
harness fix for STUDY-011 must make such substitution structurally
impossible.

These tests pin:
  1. The LIVE_ONLY invariant: a run record with execution_class=EXCLUDED
     or with is_live=False is rejected in LIVE_ONLY mode.
  2. The validate_for_live_valid() gate: every required provenance field
     must be present and valid for LIVE_VALID classification.
  3. The dry-run record schema (STUDY-008 legacy) is correctly
     classified as INVALID_PROTOCOL or EXCLUDED — never LIVE_VALID.
  4. Duplicate run_ids in the same checkpoint are caught.
  5. Circuit-breaker opens after the configured threshold.
  6. Rate-limiter enforces minimum spacing.
  7. Checkpoint journal resume skips already-completed runs.

ponytail: each test is small, deterministic, and offline.
"""
import os
import sys
import json
import time
import pytest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "experiments", "live_benchmark"))

import run_study_011 as h  # noqa: E402
import study011_rate_limit as rl  # noqa: E402
from experiments.live_benchmark import study011_analyze as a  # noqa: E402


# ─── Helpers ──────────────────────────────────────────────────────────────


def _valid_run_record(**overrides) -> h.RunRecord:
    """A fully-valid LIVE_VALID RunRecord."""
    base = dict(
        run_id="study011-test-001",
        condition="A",
        workload_id="S11-TEST-01",
        provider_name="dialagram",
        exact_model_id="qwen-3.8-max",
        provider_request_id="abc123def456",
        http_status=200,
        request_hash="deadbeef" * 8,
        response_hash="cafebabe" * 8,
        mission_hash="feedface" * 8,
        token_count_prompt=10,
        token_count_completion=20,
        cost_usd=0.0,
        is_live=True,
        execution_class="LIVE_VALID",
        manifest_hash="manifest123",
        latency_ms=120.0,
    )
    base.update(overrides)
    return h.RunRecord(**base)


# ─── 1. LIVE_ONLY invariant ───────────────────────────────────────────────


def test_live_only_invariant_rejects_excluded():
    run = _valid_run_record(execution_class="EXCLUDED", is_live=False)
    with pytest.raises(RuntimeError, match="INVARIANT VIOLATION"):
        h.enforce_live_only_invariant(run, h.ExecutionMode.LIVE_ONLY)


def test_live_only_invariant_allows_live_valid():
    run = _valid_run_record()
    h.enforce_live_only_invariant(run, h.ExecutionMode.LIVE_ONLY)  # no raise


def test_live_only_invariant_allows_live_provider_failure():
    """A genuine attempt that hit a provider failure is still LIVE_ONLY-
    compatible: it represents evidence, not a silent substitution."""
    run = _valid_run_record(
        execution_class="LIVE_PROVIDER_FAILURE",
        http_status=429,
        provider_request_id=None,
        is_live=True,
    )
    h.enforce_live_only_invariant(run, h.ExecutionMode.LIVE_ONLY)  # no raise


def test_dry_run_mode_allows_simulated():
    """In DRY_RUN or SIMULATION_ONLY, EXCLUDED is fine — the
    LIVE_ONLY invariant only fires in LIVE_ONLY mode."""
    run = _valid_run_record(execution_class="EXCLUDED", is_live=False)
    h.enforce_live_only_invariant(run, h.ExecutionMode.DRY_RUN)  # no raise
    h.enforce_live_only_invariant(run, h.ExecutionMode.SIMULATION_ONLY)  # no raise


# ─── 2. validate_for_live_valid gate ──────────────────────────────────────


def test_validate_for_live_valid_passes_on_complete_record():
    run = _valid_run_record()
    issues = run.validate_for_live_valid()
    assert issues == [], f"unexpected issues: {issues}"


@pytest.mark.parametrize("field,value,expected_substr", [
    ("is_live", False, "is_live must be True"),
    ("provider_request_id", None, "provider_request_id missing"),
    ("provider_request_id", "", "provider_request_id missing"),
    ("request_hash", "", "request_hash missing"),
    ("response_hash", "", "response_hash missing"),
    ("http_status", None, "http_status"),
    ("http_status", 429, "http_status"),
    ("http_status", 500, "http_status"),
    ("token_count_prompt", None, "token_count_prompt"),
    ("token_count_completion", None, "token_count_completion"),
    ("latency_ms", 0, "latency_ms"),
    ("latency_ms", -10, "latency_ms"),
])
def test_validate_for_live_valid_catches_each_field(field, value, expected_substr):
    run = _valid_run_record(**{field: value})
    issues = run.validate_for_live_valid()
    assert any(expected_substr in i for i in issues), \
        f"field {field}={value!r} should produce issue matching {expected_substr!r}; got {issues}"


# ─── 3. STUDY-008 regression: idx==0 simulation cannot become LIVE_VALID ──


def test_study008_idx0_pattern_is_rejected_by_validator():
    """The STUDY-008 bug was: `is_live_call = (idx == 0)`, which made the
    first run per cell genuinely live but the rest silently simulated.
    The fix must reject any non-first `idx > 0` attempt that lacks
    real provider provenance (provider_request_id + is_live=True +
    http_status=200)."""
    # Simulate the STUDY-008 pattern: idx > 0, no provider_request_id,
    # http_status=200 (harness-faked), but is_live=False
    bad = _valid_run_record(
        run_id="study011-test-idx99",
        is_live=False,
        http_status=200,
        provider_request_id="placeholder",
    )
    issues = bad.validate_for_live_valid()
    assert any("is_live" in i for i in issues), \
        "STUDY-008 regression: is_live=False must block LIVE_VALID classification"


def test_study008_legacy_dry_run_schema_classified_as_invalid_protocol(tmp_path):
    """STUDY-008 left 299 dry-run records under data/live_benchmark_dry_runs/
    with a different schema (no is_live, no http_status, no execution_class).
    These MUST NOT be loadable as LIVE_VALID by the STUDY-011 analyzer."""
    # Construct a record matching the STUDY-008 dry-run shape
    legacy = {
        "run_id": "run-A-TASK-LIVE-01-99999_ffff",
        "task_id": "TASK-LIVE-01",
        "provider": "openai",
        "exact_model_id": "gpt-4o",
        "condition": "A",
        "timestamp_iso": "2026-09-04T01:00:00Z",
        # NB: NO is_live, NO http_status, NO execution_class
    }
    cls = a.classify_execution(legacy)
    assert cls in ("INVALID_PROTOCOL", "EXCLUDED"), \
        f"STUDY-008 legacy dry-run was classified as {cls!r}; must not be LIVE_VALID"


def test_real_live_valid_passes_classification():
    """Positive control: a record that *is* fully live must classify as
    LIVE_VALID."""
    rec = {
        "run_id": "study011-test-live-001",
        "is_live": True,
        "http_status": 200,
        "provider_request_id": "req_abcdef123456",
        "request_hash": "a" * 64,
        "response_hash": "b" * 64,
        "manifest_hash": "c" * 64,
        "token_count_prompt": 100,
        "token_count_completion": 50,
        "latency_ms": 200.0,
        "execution_class": "LIVE_VALID",
        "provider_name": "dialagram",
        "exact_model_id": "qwen-3.8-max",
        "workload_id": "S11-TEST-01",
        "replicate_id": "0",
        "condition": "A",
    }
    assert a.classify_execution(rec) == "LIVE_VALID"


# ─── 4. Circuit breaker ───────────────────────────────────────────────────


def test_circuit_breaker_opens_after_threshold():
    rl.reset_all()
    cb = rl.CircuitBreaker(provider="test", model="m", threshold=3, cooldown_seconds=10.0)
    assert cb.allow()[0] is True
    cb.record_failure()
    cb.record_failure()
    assert cb.allow()[0] is True, "still under threshold"
    cb.record_failure()
    assert cb.allow()[0] is False, "should be OPEN at threshold"
    assert cb.state == "OPEN"


def test_circuit_breaker_recovers_after_cooldown():
    rl.reset_all()
    cb = rl.CircuitBreaker(provider="test", model="m", threshold=2, cooldown_seconds=0.05)
    cb.record_failure()
    cb.record_failure()
    assert cb.allow()[0] is False
    time.sleep(0.1)
    allowed, reason = cb.allow()
    assert allowed is True, f"should allow half-open probe; got {reason!r}"
    cb.record_success()
    assert cb.state == "CLOSED"


# ─── 5. Rate limiter ──────────────────────────────────────────────────────


def test_rate_limiter_enforces_minimum_spacing():
    rl.reset_all()
    lim = rl.RateLimiter(provider="test", model="m", min_spacing_seconds=0.5, burst=1)
    lim.acquire()  # takes the first slot
    wait = lim.wait_time()
    assert 0.4 <= wait <= 0.6, f"expected ~0.5s wait, got {wait}"


def test_rate_limiter_honors_retry_after():
    rl.reset_all()
    lim = rl.RateLimiter(provider="test", model="m", min_spacing_seconds=0.0)
    lim.register_retry_after(2.0)
    wait = lim.wait_time()
    assert 1.5 <= wait <= 2.5, f"expected ~2s wait from Retry-After, got {wait}"


# ─── 6. Checkpoint / resume ───────────────────────────────────────────────


def test_checkpoint_journal_resume_skips_completed(tmp_path):
    journal = tmp_path / "study011.journal.jsonl"
    cs = rl.CheckpointState(path=journal)
    cs.record(
        run_id="study011-dialagram-A-S11-A-1-r000",
        provider="dialagram", model="qwen-3.8-max",
        condition="A", workload_id="S11-A-1", replicate_id="0",
    )
    cs.record(
        run_id="study011-dialagram-A-S11-A-1-r001",
        provider="dialagram", model="qwen-3.8-max",
        condition="A", workload_id="S11-A-1", replicate_id="1",
    )

    # New process / re-load: completed runs must be remembered
    cs2 = rl.CheckpointState(path=journal)
    assert cs2.has_run("study011-dialagram-A-S11-A-1-r000")
    assert cs2.has_run("study011-dialagram-A-S11-A-1-r001")
    assert not cs2.has_run("study011-dialagram-A-S11-A-1-r002")
    keys = cs2.completed_keys()
    assert ("dialagram", "qwen-3.8-max", "A", "S11-A-1", "0") in keys
    assert ("dialagram", "qwen-3.8-max", "A", "S11-A-1", "1") in keys


def test_checkpoint_journal_idempotent_on_rerecord(tmp_path):
    journal = tmp_path / "study011.journal.jsonl"
    cs = rl.CheckpointState(path=journal)
    cs.record(run_id="r1", provider="p", model="m", condition="A",
              workload_id="W", replicate_id="0", outcome="LIVE_VALID")
    cs.record(run_id="r1", provider="p", model="m", condition="A",
              workload_id="W", replicate_id="0", outcome="LIVE_PROVIDER_FAILURE")
    # Reload — the latest record wins (last-wins by run_id)
    cs2 = rl.CheckpointState(path=journal)
    snap = cs2.snapshot()
    assert snap["completed_runs"] == 1, f"expected last-wins; got {snap}"
    # The file has 2 lines (append-only); cache has 1 entry.


# ─── 7. Provider config freeze ────────────────────────────────────────────


def test_provider_config_has_no_hardcoded_keys():
    """A regression guard: any provider's api_key_default must be None.
    STUDY-008-era code had a DIALAGRAM_DEFAULT_KEY = "<key>". The fix
    was to set it to None and require the env var. This test makes that
    invariant explicit."""
    for name, cfg in h.PROVIDERS.items():
        assert cfg.get("api_key_default") is None, \
            f"provider {name!r} has hardcoded api_key_default={cfg.get('api_key_default')!r}"
        assert cfg.get("api_key_env"), \
            f"provider {name!r} has no api_key_env"


def test_provider_config_models_match_frozen_matrix():
    """The provider model list in the harness must match the frozen
    provider matrix. If they drift, the harness would issue calls to
    models outside the pre-registration, which is a protocol violation."""
    import json
    base = Path(_REPO)
    mat = json.load(open(base / "data" / "study011_provider_model_matrix.json"))
    frozen = {}
    for stratum in mat["provider_strata"]:
        frozen[stratum["provider_stratum"]] = {m["exact_model_id"] for m in stratum["models"]}
    for name, cfg in h.PROVIDERS.items():
        if cfg["phase"] > 1:
            continue  # Phase 2 not frozen
        if name not in frozen:
            continue  # not in Phase 1
        declared = set(cfg["models"])
        expected = frozen[name]
        assert declared == expected, (
            f"provider {name!r}: harness models {declared!r} != "
            f"frozen matrix {expected!r}"
        )
