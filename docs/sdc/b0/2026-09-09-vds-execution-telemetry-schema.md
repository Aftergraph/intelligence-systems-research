# SDC-B0 Telemetry Schema: Hermes VDS Execution Replay Evidence

**Status:** FROZEN BASELINE
**Date:** 2026-09-09
**Parent Track:** #54
**Task:** #56
**Evidence Class:** Engineering telemetry schema only. Not STUDY-012 evidence.

## 1. Purpose

Define the mandatory telemetry events and fields required to reconstruct
a complete SDC-B0 execution run externally. Every planner/subplanner/worker
transition must be inspectable and replayable for causal analysis.

Telemetry is OBSERVABILITY ONLY. It does not grant authority, alter task
outcomes, or substitute for independent verification.

## 2. Event Types

All events are timestamped ISO8601 UTC with nanosecond precision where available.

### 2.1 Run Lifecycle
```json
{"event": "run_start", "run_id": "string", "mission": "string", "started_at": "ISO8601", "vds_fingerprint": "string"}
{"event": "run_end", "run_id": "string", "ended_at": "ISO8601", "outcome": "completed|failed|aborted", "summary": {}}
```

### 2.2 Planner Events
```json
{"event": "planner_spawn", "planner_id": "string", "parent_planner_id": "string|null", "scope": "string", "spawned_at": "ISO8601"}
{"event": "planner_replan", "planner_id": "string", "reason": "string", "task_tree_snapshot": {}, "replanned_at": "ISO8601"}
{"event": "planner_state_refresh", "planner_id": "string", "source": "ledger|handoff|verification", "refreshed_at": "ISO8601"}
```

### 2.3 Worker Events
```json
{"event": "worker_spawn", "worker_id": "string", "task_id": "string", "parent_task_id": "string|null", "worktree_path": "string", "base_sha": "string", "spawned_at": "ISO8601", "process_fingerprint": "string"}
{"event": "worker_command", "worker_id": "string", "process_fingerprint": "string", "cmd": "string", "exit_code": 0, "duration_ms": 0, "stdout_bytes": 0, "stderr_bytes": 0, "executed_at": "ISO8601"}
{"event": "worker_test", "worker_id": "string", "process_fingerprint": "string", "test_name": "string", "result": "pass|fail|skip", "duration_ms": 0, "base_sha": "string", "head_sha": "string", "executed_at": "ISO8601"}
{"event": "worker_handoff", "worker_id": "string", "task_id": "string", "head_sha": "string", "files_changed": [], "handoff_hash": "string", "submitted_at": "ISO8601"}
{"event": "worker_end", "worker_id": "string", "outcome": "complete_candidate|failed|timeout|crash", "ended_at": "ISO8601", "resource_summary": {}}
```

### 2.4 Git Events
```json
{"event": "git_merge", "target_branch": "string", "merge_commit": "string", "merged_at": "ISO8601"}
{"event": "git_rebase", "branch": "string", "old_base": "string", "new_base": "string", "conflicts": [], "rebased_at": "ISO8601"}
{"event": "git_stale_base", "branch": "string", "expected_base": "string", "actual_base": "string", "detected_at": "ISO8601", "action": "discard|rebase"}
```

### 2.5 Verification Events
```json
{"event": "verification_start", "verifier_id": "string", "task_id": "string", "candidate_sha": "string", "started_at": "ISO8601"}
{"event": "verification_result", "verifier_id": "string", "task_id": "string", "verdict": "verified|rejected", "reasons": [], "completed_at": "ISO8601"}
```

### 2.6 Human Intervention
```json
{"event": "human_intervention", "actor": "string", "action": "approve|reject|override|unblock", "target": "string", "reason": "string", "timestamp": "ISO8601"}
```

### 2.7 Resource Metrics
```json
{"event": "resource_snapshot", "cpu_percent": 0, "ram_used_mb": 0, "disk_io_wait_percent": 0, "active_workers": 0, "active_worktrees": 0, "snapshot_at": "ISO8601"}
```

## 3. Identity Requirements

- **Worker identity** = worker_id + process_fingerprint (NOT PID alone)
- **Process fingerprint** = hash of (binary_path + start_time + parent_pid + cgroup_id)
- **Run ID** = globally unique per continuous execution session
- **Task ID** = immutable once assigned; never reused

## 4. Redaction Rules

Before persisting any event:
- Replace credential values with `[REDACTED]`
- Truncate stdout/stderr to configurable bound (default 64KB)
- Strip environment variables except allowlisted safe set
- Never log API keys, tokens, passwords, or private keys

## 5. Evidence Survival

Telemetry MUST survive:
- Worker crash (write-ahead logging REQUIRED; periodic flush alone is insufficient)
- Session termination (final flush on shutdown signal)
- Disk pressure (rotate/compress old events)

**Durability requirement:** Every event MUST be persisted synchronously or via
write-ahead log before the emitting process continues. Periodic-only flush strategies
that can lose events on crash are NOT acceptable for B0 telemetry.

Storage: append-only JSONL files under `/var/log/sdc/<run_id>/` or equivalent.

## 6. Reconstruction Contract

Given a complete telemetry log for a run, an external tool MUST be able to:
1. Reconstruct the full task delegation graph (parent-child edges)
2. Identify which exact worktree/SHA produced each handoff
3. List every command executed per worker with exit codes
4. Correlate test results to specific workers and SHAs
5. Detect stale-base invalidations and their resolution
6. Compute resource pressure timeline
7. Identify all human interventions and their targets

## 7. Non-Authority

Telemetry events are OBSERVED state. They do NOT constitute:
- Verification verdicts
- Release authority
- Research evidence
- Completion certification

Verification verdicts come from independent verifiers (Task #58).
Research evidence comes from frozen experimental protocols (STUDY-012).

## 8. B0 Scope

This schema covers B0 observability only. Post-B0 treatments (G1-G5) may
add event types for authority delegation, budget tracking, revocation
watermarks, and release gates.
