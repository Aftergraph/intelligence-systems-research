# Owner-Authority Agent — Design (spec v1)

- **Date:** 2026-09-20
- **Status:** Draft — awaiting owner read before implementation planning
- **Origin:** owner brainstorming session, JAR-EXP-0015 Gate B close-out
- **One line:** Give the owner a standing, revocable, cryptically-rooted proxy that can sign JAR-EXP gates and other owner acts with truthful provenance — while making it mechanically impossible for the agent to *mint* the owner's authority.

---

## 0. Problem statement and the invariant that must survive

JAR-EXP-0015 reached its correct fail-closed boundary: the calibration execution path and the cross-repo TypeSafe evidence package are complete, and the only thing standing between `NO_GO` and `READY_TO_CALIBRATE` is the owner's Gate B signature (owner approval + network authorization). The executing agent refused, twice, to fabricate that signature — correctly, because the standing rule is *"the assistant must never fabricate approval or semantic-review records."*

The owner wants an agent that can legitimately act as their hand: hold the owner identity + assistant role, carry standing approvals, sign records, delegate to and converse with other agents. The integrity-critical requirement is that this be the owner's *instrument*, never a *forgery machine*.

**Invariant (load-bearing, non-negotiable):** every signature carries truthful provenance — *whose authority*, *whose hand*, *under which delegation* — and the delegation itself originates in an authentic owner act that the agent's own hand cannot produce. The agent may **use** authority; it must never be able to **mint** it.

This spec institutionalizes that invariant rather than routing around it.

### Provenance history that motivates the design

- Gate A (independent semantic falsification review) is **closed** by isolated CI run `35473954572` / commit `1a2dc7f`, record `data/jar_exp_0015_semantic_review_20260919.json`, pin `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762`.
- Gate B (owner approval + network authorization) is **open by design**; template `data/jar_exp_0015_calibration_approval_PENDING.json` is pristine (`record_status: PENDING_OWNER_SIGNATURE`, `approved_by: ""`).
- An errant agent tool call once wrote a Gate B record by hand (`approved_by: "JonasAbde"`). It was detected, never committed, never pushed, and fully reverted. That incident is the precise failure mode this agent exists to make structurally impossible: a *delegated* signature must be labeled as delegated, and the delegation must trace to a root the agent cannot reach.

---

## 1. Locked decisions (six)

These were settled one at a time during brainstorming; the rest of the spec is a transcription of them.

| # | Decision | Choice | Why it matters |
|---|----------|--------|----------------|
| 1 | **Form** | Standing owner-authority agent | Revocable mandate, not per-gate ceremony; covers 0015 Gate B, future holdout gate, 0016+. |
| 2 | **Root of trust** | Out-of-band detached-signed `DelegationRecord` | The agent verifies the owner's signature but can never produce one. |
| 3 | **Mandate** | General owner proxy | Covers gates, ratifications, escalations, dispatch — "all kinds of stuff." |
| 4 | **Fence** | Two-tier + reserved list | Routine acts under the standing mandate; reserved matters need a per-act live owner confirm. A power of attorney with reserved matters. |
| 5 | **Key custody** | Hardware token (ed25519-sk / GPG smartcard) | The private key never leaves the token; touch-to-sign. The only custody that is a real root on a box where every software key is agent-reachable. |
| 6 | **Approach** | Hybrid: code spine + persona face | Forgery-resistance lives in cryptography (spine), not in a prompt (face). Delete the face and the spine still fails closed. |

**Consistency check:** decisions 2 + 5 fix *where* authority comes from (a hardware root the agent cannot hold); 3 + 4 fix *how much* (general scope, fenced at the seals); 1 + 6 fix *what enforces it* (a standing object, enforced by code). No contradictions among them.

---

## 2. Architecture — hybrid spine + face

Two layers, deliberately unequal.

- **The spine is code** (`authority/`, a new small package at the repo root). Every authority check lives here: signature verification, scope, expiry, revocation, the routine-vs-reserved tier, the ledger, and the single operation that writes an approval record. It fails closed — if anything about the mandate is wrong, it refuses and writes nothing.
- **The face is a persona** (an `owner-authority` skill). It carries the mandate narrative and knows *when* to reach for the spine. It holds **zero authority of its own**: delete the face and the spine still refuses an unverified signature. A persona can be manipulated by prompt injection; a verifier cannot. That asymmetry is the whole point of decision 6.

The spine implements the contract already written in `08-IDENTITY-AUTHORITY-DELEGATION.md` (who delegates, the delegate, re-delegation, what proof binds the delegation) and inherits the five invariants from `24-AFTER-GRAPH-ARCHITECTURE-AND-ROADMAP.md`:

1. fail-closed admission
2. tamper-evident audit chain
3. evidence-before-execution
4. monotonic delegation attenuation (Invariant 3; `create_subdelegation()` / `validate_subdelegation()`)
5. human-in-the-loop

It is the AIE `DelegationRecord` track made executable — a continuation of the repo's normative-authority line (ADR-008 RFC 8693 mission-delegation token chain, ISR `DelegationManager`), **not** a parallel scheme.

---

## 3. Components

### Spine — `authority/`

| Module | Responsibility |
|--------|----------------|
| `delegation_record.py` | The record schema + canonical serialization (JSON `sort_keys=True, separators=(",",":"), ensure_ascii=False`, then SHA-256). Defines `delegation_ref = sha256(canonical_record)`. |
| `signature.py` | Verifies the detached GPG signature of the record against a committed public key. Returns `(ok: bool, reason: str)`. gpg-only in v1 (SSH `-Y` deferred). |
| `mandate.py` | `evaluate(record, action, bindings, now) -> ALLOW_ROUTINE \| REFUSE_RESERVED \| REFUSE_INVALID(reason)`. Checks expiry, revocation, scope, and that the action's real bindings match what the mandate permits. |
| `revocation.py` | Loads owner-signed revocation records; a revocation poisons its `delegation_ref` from the revocation's timestamp forward. Checked live on every act; never cached. |
| `ledger.py` | Append-only hash-chained JSONL at `data/delegation_ledger.jsonl`. One row per signing act. See §7. |
| `sign_gate.py` | The orchestrator and the **only** writer of an approval record. verify root → evaluate mandate → write record → wire gate → append ledger, all-or-nothing (rollback if any step after the record write fails). See §5. |
| `keys/` | Committed, agent-read-only: `delegation_record.json`, `delegation_record.sig`, `owner.pub.asc`, and any `revocation_*.json`. **The private key never enters the repo, never enters this machine's filesystem in software form.** |

### Face — `.agents/skills/owner-authority/SKILL.md`

Repo-local so it is versioned with the spine (the AGENTS.md convention; the dir does not yet exist and is created by implementation). Instructs: to sign / ratify / dispatch, call the spine; **never** hand-write an approval record; reserved matters go to the per-act confirm path. Carries the mandate narrative (scope, expiry, reserved list) as *description only* — the authoritative terms live in the signed record (§4).

### CI audit — `scripts/verify_delegation_ledger.py` + a new `ci.yml` job

Every approval record on a protected path must have a matching verified ledger entry whose delegation root verifies, is unexpired and unrevoked at the entry timestamp. Hand-forging a record around the spine becomes a **detectable** act, not a silent one. The audit excludes the test-only fixture pubkey (§9).

---

## 4. Integrity catch: the signed record is the single source of truth for the mandate's own terms

**The reserved-matters list, the expiry, the scope and the budget ceiling all live *inside* the owner-signed `DelegationRecord`, never in a mutable config file.**

If the spine read "what's reserved" from a plain file on disk, the agent could move a seal from the reserved tier to the routine tier by editing that file — the fence would sit inside the reach of the thing it fences. So:

- The signed record is the only source for: `scope`, `reserved_matters[]`, `budget_ceiling_usd`, `expires_at`, `not_before`, `redelegate_allowed`, `max_depth`.
- The spine reads these **only** from the verified record. Any edit to the record invalidates the signature (§8, `record_tampered`).
- Revocations are likewise owner-signed, committed, agent-read-only.
- The action taxonomy (e.g. `SIGN_CALIBRATION_GATE`, `RATIFY_ADR`, `MERGE_BRANCH`, `DISPATCH`) is defined in the spine as code; the signed record's `scope` is an **allowlist** of permitted action classes and `reserved_matters[]` carves out denies within it. An action the spine does not recognize, or one outside `scope`, is `REFUSE_INVALID(out_of_scope)` — fail-closed by default. This is what keeps "general proxy" from silently becoming "unbounded."

This is the detail that makes decision 4 (the fence) real rather than decorative.

### The frozen preflight is untouched

The 0015 preflight (`experiments/system_one_acceleration/jar15_calibration_preflight.py:351-386`) reads the approval record by **named key only** — it never enumerates or rejects unknown fields. So the provenance block (§6) rides alongside the 17 normative fields without touching frozen code and without moving the pin `dc5d7a94…`. Both the approval record and the gate file sit **outside** the 30-path content-addressed manifest, so Gate A stays valid and the calibration manifest pin is stable.

---

## 5. Data flow — the two acts

### Routine act — signing Gate B (calibration)

```
owner (one-time, hardware token)     agent face                spine (authority/)
  touch-to-sign DelegationRecord  -->  "sign Gate B"  -------->  sign_gate
  commit record + sig + pubkey                                   1. signature.verify(sig, record, owner.pub)
                                                                 2. mandate.evaluate(SIGN_CALIBRATION_GATE,
                                                                      bindings={pin=dc5d7a94…, model=jev-1.13.0,
                                                                                calls=1952, cost_usd=5.38})
                                                                      -> ALLOW_ROUTINE
                                                                 3. write approval record (17 fields + provenance)
                                                                 4. wire gate owner_approval_ref + flip network bool
                                                                 5. append ledger row  <-- COMMIT POINT
                                                                 (any failure in 3-5 -> roll back in reverse;
                                                                  tree restored byte-identically)
                                                                    |
                                                                    v
                                                              preflight: READY_TO_CALIBRATE (exit 0)
```

Signing calibration and its network authorization within the preregistered $5.38 / 1952-call ceiling breaks no seal: holdout stays a separate protected gate (`LOCKED_PENDING_FROZEN_POLICY` / `CALIBRATION_NOT_RUN`), and retries are frozen off (`RetryPolicy(max_retries=0)`).

After this, expect CI verifier **check 33 to go red** — it is a *pre-authorization snapshot* (asserts `NO_GO` with blockers ⊆ human gates). That is the snapshot doing its job; checks 1–32 and 34–38 stay green. Documented in commit `2416e00`.

### Reserved act — e.g. a branch merge, or a budget raise above the preregistered ceiling

```
agent face --> spine: mandate.evaluate(MERGE_BRANCH, ...) -> REFUSE_RESERVED
           <-- face tells owner: "reserved matter; touch the token to confirm this one act"
owner (token) signs a per-act confirmation bound to a digest of the proposed action
           --> spine verifies the confirmation as a FRESH root (not the standing mandate)
           --> proceeds, logs tier:"reserved-confirmed" with the confirmation's signature
```

The reserved path **reuses the same hardware root** — no separate nonce channel; the token *is* the channel. Reserved matters (the initial list, editable only by re-signing the record): manifest pins, holdout-before-calibration ordering, branch merges (the `war-room-typesafe-bridge @ 6be6d80` do-not-merge tree), budget raises above the preregistered ceiling, frozen 0014 records (`cost_guard.py`, `durable_calibration.py`, etc., under 0014's pin `6a29bc8e…`).

---

## 6. Truthful-provenance block

Written by `sign_gate` alongside the 17 normative fields the preflight checks. `approved_by` names the **authority**; `signed_by_hand` names the **hand**. That separation is the whole integrity point, made mechanical.

```json
{
  "approved_by":      "JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
  "approved_at":      "2026-09-20T14:03:11+00:00",
  "signed_by_hand":   "agent:owner-authority",
  "delegation_ref":   "<sha256 of canonical DelegationRecord>",
  "owner_signature":  "<gpg sig digest>",
  "authority_basis":  "owner-signed standing mandate, verified at sign time",
  "ledger_entry":     "<ledger row id>"
}
```

Constraints the frozen preflight enforces on the normative subset (all satisfied by the spine):

- `approved_at` must be **timezone-aware** ISO 8601 (`_valid_attribution`: `timestamp_not_timezone_aware` otherwise).
- `requested_typesafe_model`, `calibration_manifest_sha256`, `max_provider_calls`, `max_cost_usd` must byte-match the gate (else `*_mismatch` blockers).
- `approved is True` and the record-level `network_calls_authorized is True` (distinct from the gate-level boolean → `jar15_network_calls_not_authorized`).

**Principal note:** the approval principal is `JonasAbde <147070826+JonasAbde@users.noreply.github.com>`, which differs from the clone's git identity `Jonas ABde <empire1266@gmail.com>`. This is exactly why the ledger records an explicit `actor` / `principal` and never relies on git-author attribution — an agent commit is not the owner's authentic hand.

---

## 7. Ledger format (append-only, hash-chained)

`data/delegation_ledger.jsonl`, one JSON object per line:

```json
{
  "seq": 1,
  "prev_sha256": null,
  "entry_sha256": "<sha256 of canonical(row minus entry_sha256)>",
  "ts": "2026-09-20T14:03:11+00:00",
  "actor": "agent:owner-authority",
  "principal": "JonasAbde <147070826+JonasAbde@users.noreply.github.com>",
  "delegation_ref": "<sha256 of DelegationRecord>",
  "action": "SIGN_CALIBRATION_GATE",
  "tier": "routine",
  "target": "data/jar_exp_0015_calibration_gate_v01.json",
  "approval_record": "data/jar_exp_0015_calibration_approval_20260920.json",
  "bindings": {
    "manifest": "dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762",
    "model": "jev-1.13.0",
    "calls": 1952,
    "cost_usd": 5.38
  }
}
```

- `prev_sha256` → `entry_sha256` chaining makes truncation/insertion/reordering detectable; the CI audit recomputes the chain.
- The ledger append is the **commit point**: no ledger row means the act did not happen.
- Binds to the repo's existing convention (`data/decision_log.csv` DEC-001..034, with DEC-030 already recording owner-delegated approvals; the 27 `study012_owner_approval_*.json` records) as the precedent for the row shape — but v1 audits **new** records only (no backfill; §10).
- The ledger path is new and sits outside the 30-path manifest, so appending never moves the pin `dc5d7a94…` — the same independence §4 guarantees for the approval record.

---

## 8. Error handling — fail closed on every axis

The spine's only two outcomes are *refuse and write nothing*, or *act atomically*. No partial-success path.

- **Signature** — `signature_missing`, `signature_malformed`, `signature_key_mismatch` (valid sig, wrong key), `record_tampered` (sig valid over a different byte-string), `pubkey_unknown` (committed key not in the trust set). Any one → refuse.
- **Mandate validity** — `mandate_expired`, `mandate_not_yet_valid`, `mandate_revoked`, `out_of_scope`. Revocation poisons its `delegation_ref` from its timestamp forward; checked live, never cached.
- **Binding drift** — `binding_manifest_mismatch`, `binding_model_mismatch`, `binding_call_ceiling`, `binding_cost_ceiling`. Stops a valid mandate for *this* gate from signing *that* gate.
- **Atomicity** — write approval record to temp → fsync → rename; wire gate; append ledger. A failure at any step after the record write rolls back in reverse (unwire gate, delete record) and restores the tree byte-identically.
- **Ledger integrity** — corrupt line, broken chain, or truncation → refuse to sign *and* refuse to append. Fail closed rather than write onto a damaged chain.
- **Clock** — `evaluate(..., now)` takes `now` as a parameter (tests pin it); production cross-checks `now` against the newest ledger-entry timestamp (when the ledger is non-empty — the first act has no prior timestamp) and refuses if the system clock moved backwards. Closes "set the clock back to un-expire the mandate."
- **Bypass** — hand-writing an approval record without the spine is *not* caught by the spine (it isn't in the loop); it is caught by the CI audit, which fails loudly. The design's answer to bypass is **detection**, not prevention — and the detection is tamper-evident because the ledger chain and the signature both have to line up.

---

## 9. Testing — proving it is a verifier, not a forgery machine

- **Truth-table units** on `mandate.evaluate` — every combination of (scope, tier, expiry, revocation, bindings) → expected verdict. Pure, deterministic, no crypto.
- **Signature round-trips with a fixture key** — generate an ed25519/gpg test key in a temp dir; sign → verify passes; tamper one byte → fails; swap pubkey → fails. **These tests never touch the owner's real key or token.** The fixture pubkey is committed as a clearly-labelled test-only trust anchor and excluded from the CI audit's production trust set.
- **Negative / forgery tests** — each refused: record with no sig; valid record+sig with one binding field altered; a revoked `delegation_ref`; a reserved-tier action under the standing mandate; a clock rolled back past expiry; a hand-written approval record with no ledger row (caught by the CI-audit fixture).
- **Atomicity injection** — mock a failure at each post-write step; assert byte-identical restoration. Reuses the repo's own proof-5 methodology (throwaway temp tree, flip things, assert the real tree is untouched) — a pattern the evidence package already trusts.
- **Integration dry-run** — extend `verify_gate_plumbing_dry_run.py`: with a valid fixture-key mandate the spine reaches `READY_TO_CALIBRATE`; with each defect it stays `NO_GO` with the exact expected blocker. Same harness, now also exercising the spine.
- **Invariant tests** — one per `24-AFTER-GRAPH` invariant: fail-closed (no write without a verified pass); tamper-evident (every act has a chained ledger row); evidence-before-execution (ledger row precedes the gate wire); monotonic attenuation (sub-delegation scope ⊆ parent, depth decrements); human-in-the-loop (reserved tier always demands a fresh confirmation).

**Limitation on the record, not in a footnote:** the executing agent has no hardware token, so it **cannot test the real signing path.** Every automated test uses the fixture key. The owner's actual first act — touching the token to sign the `DelegationRecord` — is by construction outside the agent's reach, so it is verified by inspection plus the CI audit, not by an automated test. That is the design working, not a gap: the root-of-trust act is untestable by the agent precisely because the agent cannot perform it.

---

## 10. Scope boundary (v1 — YAGNI)

**In v1:**
- the `authority/` spine (record schema + canonical serialization, gpg detached-sig verify, mandate evaluator, revocation, hash-chained ledger, atomic `sign_gate`);
- the `owner-authority` skill face;
- the CI audit job;
- closing 0015 Gate B as the first real act, to dogfood it.

**Explicitly deferred (named so nobody thinks it is silently included):**
- *Orchestration powers* — dispatching subagents, answering `ResolveWorkflowQuestion`, shepherding CI runs, the periodic owner report. That is the chief-of-staff face; the ledger and registry are shaped so it grows in, but v1 signs and ratifies only.
- *SSH-signature verification* (`ssh-keygen -Y`) as a second crypto path — gpg first; one verifier is enough for v1.
- *Sub-delegation issuance* — v1 enforces attenuation on verification but does not mint sub-delegations.
- *Networked / live revocation distribution* — revocation is a committed signed record the spine polls; no push infra.
- *Multi-owner or threshold signatures* — single owner principal.
- *Backfilling the 27 existing `study012_owner_approval_*` records* — they predate the spine; v1 audits new records only.

**Boundary that matters:** v1 does **not** retroactively legitimize anything. The spine governs only records written after it exists. The 0015 Gate B signature is act zero.

---

## 11. Non-goals

- Not a way for the agent to sign Gate B *before* the owner signs the root. The root must exist first; the agent cannot mint it.
- Not a replacement for the frozen preflight, the 30-path manifest, or any preregistration seal. It sits upstream of the approval record and obeys every seal.
- Not a general-purpose secrets manager or PKI. One owner principal, one hardware root, one ledger.

---

## 12. Open items for the owner (resolve at spec review or in planning)

1. **Token specifics** — which hardware (YubiKey / GPG smartcard), which slot, and the owner's procedure for the one-time `DelegationRecord` signing + committing `owner.pub.asc`. For v1 the token must operate in **GPG mode** (the SSH `-Y` path is deferred, §10).
2. **Mandate terms** — the concrete `expires_at` (proposal: 90 days), `budget_ceiling_usd` (must be ≥ $5.38 for Gate B to fall in the routine tier), and the exact initial `reserved_matters[]` list.
3. **Face location** — default is repo-local `.agents/skills/owner-authority/SKILL.md` (versioned with the spine, §3); confirm or move to a user-level skill dir.
4. **Revocation ceremony** — how the owner signs and commits a revocation, and how quickly the CI audit must reject a poisoned `delegation_ref`.

---

*End of spec v1. Next gate: owner read + approval, then `writing-plans` for the implementation plan.*