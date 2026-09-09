# SDC-B0 Baseline Protocol: Recursive Planner/Worker Architecture

**Status:** FROZEN BASELINE
**Date:** 2026-09-09
**Parent Track:** #54
**Task:** #55
**Evidence Class:** Engineering protocol baseline only. Not STUDY-012 evidence.

## 1. Purpose

Define the minimal recursive planner/subplanner/worker execution architecture
for Aftergraph governed self-driving codebases. This baseline (B0) measures
the execution architecture itself WITHOUT any Aftergraph governance treatments
(G1-G5). Later treatment comparisons require this uncontaminated baseline.

Source hypothesis: Cursor Research "Towards Self-Driving Codebases" (Wilson Lin,
2026-02-05). We test these principles independently; we do not copy them blindly.

## 2. Topology

```
ROOT PLANNER
|
+---- SUBPLANNER
|        |
|        +---- WORKER
|        +---- WORKER
|
+---- SUBPLANNER
         |
         +---- WORKER
         +---- WORKER
```

### 2.1 Root Planner

**Owns:**
- Overall user mission
- System state understanding (repository states, active tasks, blockers)
- Task decomposition and prioritization
- Task generation and assignment to subplanners
- Continuous replanning based on handoffs and verification results
- Bounded current-state artifact (rewrite, not append)

**Must NOT:**
- Edit implementation files directly
- Become a worker (no coding)
- Self-certify completion of any task
- Hold unbounded diary-style state

### 2.2 Subplanner

**Owns:**
- Bounded delegated scope from root planner or parent subplanner
- Full planning authority within that scope
- Recursive subdivision into child subplanners or workers
- Scope-local replanning

**Must NOT:**
- Widen delegated mission beyond assigned scope
- Edit files outside delegated scope
- Communicate directly with peer subplanners
- Self-certify completion

### 2.3 Worker

**Owns:**
- One narrow task
- Isolated filesystem/repository context (worktree)
- Execution of assigned commands, tests, builds
- Single structured handoff upward

**Must NOT:**
- Communicate directly with peer workers
- Edit another worker's worktree
- Merge protected branches
- Declare own work institutionally verified
- Access credentials/secrets beyond task scope

## 3. Task Schema

```json
{
  "task_id": "string (immutable, unique)",
  "parent_task_id": "string | null",
  "assigned_to": "planner_id | subplanner_id | worker_id",
  "mission": "string (natural language scope description)",
  "repo": "string (repository identifier)",
  "base_sha": "string (exact commit SHA)",
  "allowed_scope": {
    "files": ["glob patterns"],
    "directories": ["paths"],
    "excluded": ["patterns"]
  },
  "expected_evidence": ["test results", "lint output", "build artifacts"],
  "status": "pending | dispatched | running | complete_candidate | verified | failed | stale | cancelled",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "metadata": {}
}
```

## 4. Handoff Schema

Workers and subplanners return exactly one structured handoff per task:

```json
{
  "run_id": "string",
  "task_id": "string",
  "parent_task_id": "string | null",
  "worker_id": "string",
  "repo": "string",
  "base_sha": "string",
  "head_sha": "string",
  "branch": "string",
  "worktree_identity": "string (path or container ID)",
  "mission": "string",
  "scope": {"files_allowed": [], "files_changed": []},
  "sender_type": "worker | subplanner",\n  "commands_executed": [{"cmd": "string", "exit_code": 0, "duration_ms": 0, "stdout_ref": "string | null", "stderr_ref": "string | null"}],\n  "tests_executed": [{"name": "string", "result": "pass|fail|skip", "duration_ms": 0, "output_ref": "string | null"}],
  "deviations": ["string"],
  "discoveries": ["string"],
  "concerns": ["string"],
  "blockers": ["string"],
  "known_failures": ["string"],
  "resource_summary": {"cpu_seconds": 0, "peak_ram_mb": 0, "disk_mb": 0},
  "recommended_follow_up": ["string"],
  "completed_at": "ISO8601"
}
```

Completion is derived from repository/evidence state in the handoff,
NOT from worker prose claims alone.

## 5. Freshness Rule

Planner state MUST be periodically rewritten from durable evidence:

- Current mission
- Exact repository states (SHA per repo)
- Active task tree with statuses
- Blocked tasks with reasons
- Latest handoffs received
- Known conflicts
- Recent failures
- Current priorities
- Resource pressure indicators
- Open verification queue
- Unresolved decisions

Planner scratchpad is NOT canonical truth. Durable task/evidence state
is authoritative. When context grows large: summarize, re-read ledger,
invalidate stale assumptions, continue.

## 6. Completion Semantics

A task is `complete_candidate` ONLY when the worker/subplanner submits a handoff
that satisfies ALL of the following:
- All expected_evidence items are present in the handoff
- No blockers or known_failures are listed
- head_sha differs from base_sha (work was actually performed)
- The handoff passes structural validation (all required fields present)

Tasks where the worker is blocked, stale, failed, or produced no changes MUST
NOT be promoted to `complete_candidate`. They remain in their terminal status
(`failed`, `stale`, `cancelled`) with a descriptive handoff explaining why.

A task is `verified` ONLY when an independent verifier confirms:

- Requested outcome exists in repository
- Acceptance criteria pass
- Required gates for the velocity track pass
- Evidence is bound to exact SHA
- No critical continuation items remain open

Commit count, lines changed, and token usage are NOT success metrics.
Semantic progress = independently accepted semantic movement.

## 7. B0 Boundaries

This baseline includes ONLY:
- Recursive planning topology
- Isolated worker contexts
- Structured handoffs
- Continuous replanning
- Basic observability (timestamps, commands, outputs)
- Stale-base detection

This baseline EXCLUDES (reserved for G1-G5):
- Mission binding / delegated authority
- Authority attenuation / budgets
- Revocation / freshness watermarks
- Independent outcome verification protocol (see note below)
- Green-branch reconciliation
- Release authority separation
- SHIP / DO NOT SHIP verdicts

**Note on verification fields in B0:** Independent outcome verification as an
institutional gate is excluded from B0. However, the handoff schema (§4) retains
verification-related fields (`tests_executed`, `known_failures`) so that B0
handoffs remain structurally comparable with G3+ treatment handoffs. B0 workers
report test results as evidence; they do not produce institutional verification
verdicts.

## 8. Falsifiers

B0 is invalidated if:
- Workers can edit each other's worktrees without detection
- Planner state grows unboundedly without refresh
- Handoffs lack required fields
- Completion is declared without evidence
- A failed worker kills the entire run
- Stale-base work is silently accepted
- Peer-to-peer worker coordination occurs

## 9. Source Attribution

Baseline hypothesis derived from:
- Cursor Research, "Towards Self-Driving Codebases", Wilson Lin, 2026-02-05
  (NOTE: cursor.com/research/self-driving-codebases returned 404 on 2026-09-09;
   principles extracted from secondary references and public summaries)
- OpenAI Agents SDK Sandbox Agents documentation (accessed 2026-09-09)
- @gippp69 X post 2097768380803510598 (accessed 2026-09-09)

Aftergraph-specific additions (governance separation, evidence honesty,
completion semantics) are original to this protocol.
