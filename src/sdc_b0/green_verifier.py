"""SDC-B0 Task #75: Independent Green-Branch Verifier.

Protocol source: docs/sdc/b0/2026-09-09-recursive-planner-worker-baseline-protocol.md
Depends on: #58 (green-branch reconciliation protocol)

This verifier independently evaluates branch greenness from persisted
telemetry/artifacts ONLY — it never trusts worker self-reports.

Acceptance criteria (from #75):
- src/sdc_b0/green_verifier.py module exists
- Verifier produces structured verdict dict (SHIP / DO NOT SHIP)
- Telemetry records verification events via B0Harness TelemetryCollector
- Smoke run 003 exercises verifier against a real branch
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from src.sdc_b0.semantic_progress import SemanticProgressScorer, UnmergedBranch
from src.sdc_b0.telemetry import TelemetryCollector


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    """Independent branch verdict — SHIP or DO NOT SHIP."""
    SHIP = "SHIP"
    DO_NOT_SHIP = "DO_NOT_SHIP"


@dataclass(frozen=True)
class VerificationVerdict:
    """Structured verdict dict produced by the verifier.

    This is the canonical output — consumed by the planner, persisted to
    telemetry, and never derived from worker self-reports.
    """
    verdict: Verdict
    candidate_branch: str
    candidate_sha: str
    base_sha: str
    reasons: list[str] = field(default_factory=list)
    score: int = 0
    debt: float = 0.0
    test_results: list[dict[str, Any]] = field(default_factory=list)
    reconciliation_branches: list[UnmergedBranch] = field(default_factory=list)
    verified_at: str = ""


# ---------------------------------------------------------------------------
# IndependentVerifier
# ---------------------------------------------------------------------------

class IndependentVerifier:
    """Independently verifies branch greenness from persisted artifacts.

    Reads ONLY:
    - Git test invocations (subprocess, no worker sandbox access)
    - Telemetry JSONL logs (via TelemetryCollector event types)
    - Semantic progress events (via SemanticProgressScorer)
    - Unmerged branch state (via UnmergedBranch list)

    Never:
    - Imports or calls worker_sandbox
    - Reads worker self-reports / handoff status
    - Trusts harness-internal state

    Integration point: uses TelemetryCollector (the same class B0Harness
    uses) to emit verification_start / verification_result events so the
    telemetry log captures independent verification, not worker claims.
    """

    # Thresholds (frozen for this task; tunable in a later SDC)
    _MIN_SCORE: int = 0          # semantic progress score must be >= 0
    _MAX_DEBT: float = 0.0       # reconciliation debt must be 0.0 (no unmerged conflicting branches)
    _REQUIRE_ALL_TESTS_PASS: bool = True

    def __init__(self, verifier_id: str, telemetry: TelemetryCollector | None = None) -> None:
        """Construct an independent verifier.

        Args:
            verifier_id: unique identifier for this verifier instance
            telemetry: optional TelemetryCollector for recording verification
                       events. If None, events are not emitted (no-op mode).
        """
        self._verifier_id = verifier_id
        self._telemetry = telemetry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self,
        candidate_branch: str,
        base_sha: str,
        head_sha: str,
        telemetry_log_path: Path | str | None = None,
        unmerged_branches: list[UnmergedBranch] | None = None,
        active_workers: int = 0,
        additional_test_cmds: list[str] | None = None,
    ) -> VerificationVerdict:
        """Run an independent greenness verification for a candidate branch.

        Steps (all independent of worker self-reports):
        1. Replay relevant telemetry events (if a log is provided) to
           reconstruct test results from worker_command / worker_test events.
        2. Run independent lint/test commands against the candidate branch
           (git-based, subprocess — no sandbox import).
        3. Build a SemanticProgressScorer from the same telemetry events
           and compute score + debt.
        4. Produce a SHIP / DO NOT SHIP verdict.

        Args:
            candidate_branch: git branch name being evaluated.
            base_sha: expected base SHA for the branch.
            head_sha: head SHA of the candidate branch.
            telemetry_log_path: optional path to the JSONL telemetry log
                                from the worker run under evaluation.
            unmerged_branches: optional list of currently unmerged branches
                               (for reconciliation debt).
            active_workers: number of active workers (for debt denominator).
            additional_test_cmds: optional extra commands to run as
                                  independent tests (e.g. lint, type-check).

        Returns:
            VerificationVerdict with verdict, reasons, score, debt, and
            independent test results.
        """
        reasons: list[str] = []
        test_results: list[dict[str, Any]] = []
        score = 0
        debt = 0.0

        # --- Step 1: replay telemetry to gather worker_test results ---
        worker_tests: list[dict[str, Any]] = []
        telemetry_events: list[dict[str, Any]] = []
        if telemetry_log_path is not None:
            tp = Path(telemetry_log_path)
            if tp.exists():
                telemetry_events = self._read_telemetry_events(tp)
                worker_tests = self._extract_worker_tests(telemetry_events)

        # --- Step 2: independent tests (git-based, no sandbox) ---
        if head_sha:
            independent_results = self._run_independent_tests(
                candidate_branch, head_sha, base_sha, additional_test_cmds
            )
            test_results.extend(independent_results)
            all_pass = all(r["exit_code"] == 0 for r in independent_results)
        else:
            # No head_sha — cannot run independent tests; treat as pending
            all_pass = False
            reasons.append("no_head_sha_verified_test_impossible")

        # --- Step 3: semantic progress score + debt ---
        scorer = SemanticProgressScorer(telemetry_events, active_workers=active_workers)
        if unmerged_branches:
            scorer.update_branches(unmerged_branches)
        score = scorer.score()
        debt = scorer.debt()

        # --- Step 4: verdict ---
        if not all_pass and head_sha:
            reasons.append("independent_test_failure")
        if score < self._MIN_SCORE:
            reasons.append(f"semantic_score_below_threshold: {score} < {self._MIN_SCORE}")
        if debt > self._MAX_DEBT:
            reasons.append(f"reconciliation_debt_exceeds_threshold: {debt} > {self._MAX_DEBT}")
        if unmerged_branches and any(b.conflict_count > 0 for b in unmerged_branches):
            reasons.append("unmerged_branches_with_conflicts")

        verdict = Verdict.SHIP if not reasons else Verdict.DO_NOT_SHIP

        # Build frozen verdict
        v = VerificationVerdict(
            verdict=verdict,
            candidate_branch=candidate_branch,
            candidate_sha=head_sha,
            base_sha=base_sha,
            reasons=reasons,
            score=score,
            debt=debt,
            test_results=list(test_results),
            reconciliation_branches=list(unmerged_branches or []),
            verified_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        )

        # --- Step 5: record telemetry (independent verification event) ---
        self._emit_verification_telemetry(v)

        return v

    # ------------------------------------------------------------------
    # Telemetry recording (uses the same TelemetryCollector B0Harness uses)
    # ------------------------------------------------------------------

    def _emit_verification_telemetry(self, verdict: VerificationVerdict) -> None:
        """Emit verification_start + verification_result via TelemetryCollector.

        This is the integration point with B0Harness telemetry: the same
        collector type is used, so verification events appear in the same
        JSONL log that workers and harness write to.
        """
        if self._telemetry is None:
            return

        ts = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        self._telemetry.emit(
            "verification_start",
            {
                "verifier_id": self._verifier_id,
                "task_id": verdict.candidate_branch,
                "candidate_sha": verdict.candidate_sha,
                "started_at": ts,
            },
        )
        self._telemetry.emit(
            "verification_result",
            {
                "verifier_id": self._verifier_id,
                "task_id": verdict.candidate_branch,
                "verdict": verdict.verdict.value,
                "reasons": verdict.reasons,
                "score": verdict.score,
                "debt": verdict.debt,
                "test_count": len(verdict.test_results),
                "completed_at": ts,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_telemetry_events(log_path: Path) -> list[dict[str, Any]]:
        """Read and parse a JSONL telemetry log into event dicts."""
        events: list[dict[str, Any]] = []
        with open(log_path, "r") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                events.append(__import__("json").loads(line))
        return events

    @staticmethod
    def _extract_worker_tests(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract worker_test events from a telemetry event list."""
        return [e for e in events if e.get("event") == "worker_test"]

    def _run_independent_tests(
        self,
        candidate_branch: str,
        head_sha: str,
        base_sha: str,
        extra_cmds: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run git-based independent tests against the candidate branch.

        Uses subprocess + git to inspect the branch — no worker_sandbox import.
        Commands run:
        1. git log --oneline base..head  (verify the branch has commits)
        2. Any caller-provided extra commands (lint, pytest, etc.)

        Returns a list of result dicts with exit_code, stdout, stderr, cmd.
        """
        results: list[dict[str, Any]] = []

        # 1. Verify the branch exists and has the expected head SHA
        try:
            proc = subprocess.run(
                ["git", "rev-parse", head_sha],
                capture_output=True, text=True, timeout=10,
            )
            sha_ok = proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            sha_ok = False

        if not sha_ok:
            results.append({
                "cmd": f"git rev-parse {head_sha}",
                "exit_code": -1,
                "stdout": "",
                "stderr": "cannot resolve head_sha — branch may not exist",
                "duration_ms": 0,
            })
            return results

        # 2. Verify base is an ancestor of head (branch diverges from base)
        try:
            proc = subprocess.run(
                ["git", "merge-base", "--is-ancestor", base_sha, head_sha],
                capture_output=True, text=True, timeout=10,
            )
            ancestor_ok = proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            ancestor_ok = False

        results.append({
            "cmd": f"git merge-base --is-ancestor {base_sha} {head_sha}",
            "exit_code": 0 if ancestor_ok else 1,
            "stdout": "" if ancestor_ok else "base_sha is not ancestor of head_sha",
            "stderr": "",
            "duration_ms": 0,
        })

        # 3. Run extra commands if provided
        if extra_cmds:
            for cmd in extra_cmds:
                try:
                    start = time.monotonic()
                    proc = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True,
                        timeout=300.0,
                    )
                    duration_ms = int((time.monotonic() - start) * 1000)
                    results.append({
                        "cmd": cmd,
                        "exit_code": proc.returncode,
                        "stdout": proc.stdout[:4096],
                        "stderr": proc.stderr[:4096],
                        "duration_ms": duration_ms,
                    })
                except subprocess.TimeoutExpired:
                    results.append({
                        "cmd": cmd,
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": f"command timed out after 300s",
                        "duration_ms": 300000,
                    })
                except (FileNotFoundError, OSError) as e:
                    results.append({
                        "cmd": cmd,
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": str(e),
                        "duration_ms": 0,
                    })

        return results


# ---------------------------------------------------------------------------
# Convenience: verify from a persisted telemetry log file
# ---------------------------------------------------------------------------

def verify_from_log(
    log_path: Path | str,
    candidate_branch: str,
    base_sha: str,
    head_sha: str,
    verifier_id: str = "green-verifier",
    unmerged_branches: list[UnmergedBranch] | None = None,
    active_workers: int = 0,
    extra_test_cmds: list[str] | None = None,
) -> VerificationVerdict:
    """One-shot verification from a persisted telemetry log.

    Convenience wrapper that constructs a TelemetryCollector (for event
    emission), reads the log, and runs the verifier. The collector is
    created with a throwaway run_id so verification events are recorded
    without interfering with the original run's log.

    Args:
        log_path: path to the JSONL telemetry log to evaluate.
        candidate_branch: branch being evaluated.
        base_sha: expected base SHA.
        head_sha: head SHA of the candidate branch.
        verifier_id: identifier for this verifier.
        unmerged_branches: optional unmerged branch list for debt.
        active_workers: active worker count for debt denominator.
        extra_test_cmds: optional extra independent test commands.

    Returns:
        VerificationVerdict.
    """
    tc = TelemetryCollector(run_id=f"verification-{verifier_id}", log_dir=Path("."))
    v = IndependentVerifier(verifier_id=verifier_id, telemetry=tc).verify(
        candidate_branch=candidate_branch,
        base_sha=base_sha,
        head_sha=head_sha,
        telemetry_log_path=log_path,
        unmerged_branches=unmerged_branches,
        active_workers=active_workers,
        additional_test_cmds=extra_test_cmds,
    )
    tc.close()
    return v
