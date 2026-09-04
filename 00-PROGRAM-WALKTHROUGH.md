# Program Walkthrough — Jonas Abde Intelligence Systems Research Program
**As of:** 2026-09-04 (Wave v0.3.6) · **Status:** READY_FOR_OWNER_APPROVAL · **Audit:** HEALTHY & VERIFIED
**Purpose:** single-file orientation for owner review — claims, tests, registries, ADRs, remaining work.

---

## 1. One-paragraph state

The program's defensible record is **Level C+ / Provisional-D with a submission
hold**. 487 tests pass across 50 test files; the CLI audit returns HEALTHY &
VERIFIED. A controlled LIVE pilot (JAR-EXP-0012, 4/4 LIVE_VALID on
dialagram/deepseek-v4) has validated the confirmatory harness chain end-to-end;
the preregistered confirmatory matrix (464 target) itself remains un-run. All front-door claims are evidence-bound (tests/test_claim_evidence_binding.py,
72 tests). STUDY-011 is pre-registered at manifest v1.0.3 (3 amendments) and has
NEVER executed the confirmatory live matrix — the LIVE_ONLY invariant is intact.
Owner decisions delegated in-session (DEC-030). The two live gates that remain
are environmental (one API key) and external (humans, clean-room team).

## 2. Studies & their evidence class

| Study | Topic | Evidence class | Key result |
|---|---|---|---|
| JAR-EXP-0001 | 4-condition verification ablation (SWE, N=50) | SIMULATED (seed=1337) | Evidence-gated C4 has lowest FCR; hierarchy pinned |
| JAR-EXP-0004 / MISSION-Bench | 8-stage ablation, 800 runs | SIMULATED | FCR 61%→0% in verification-enabled stages; CPVO $0.5791→$0.1081 |
| JAR-EXP-0005 | Model compatibility (Q-001) | SIMULATED (seed=42) | Progressive contracts: small models +33.8% CUA, frontier +5.7% |
| JAR-EXP-0008 (STUDY-008) | Live multi-model pilot | METHODOLOGICAL_PILOT | 275 attempts = 2 LIVE_VALID + 9 provider-fail + 264 SIMULATED |
| STUDY-009 | Durability fault injection | SIMULATED (fault injection) | 7/7 kill points recover; 1 expected pre-commit loss; state-bleed bug fixed |
| STUDY-010 | Assurance adversarial | SIMULATED (attack vectors) | 9/9 hostile vectors safely rejected; 0% compromise |
| STUDY-006 (GOMS pilot) | HCI instrumentation | SIMULATED (N=0 humans) | HEVO 6.59→1.99 (~70%); live trial preregistered, not run |
| STUDY-011 | Cross-provider replication | PRE-REGISTERED (no live runs) | Manifest v1.0.3; harness wired; awaiting keys |
| C-011 Router evaluation | 4 routing policies | SIMULATED | VSR match 84%≈84%, cost −22.2%, 0 constraint violations |
| C-007 Confounder | Retries vs evidence gating | SIMULATED | D>A; FCR=0 only in evidence-gated conditions |

No SIMULATED result has been upgraded to LIVE. STUDY-008's 2 LIVE_VALID runs
remain the only live data in the program.

## 3. Architecture decisions (ADRs)

| ADR | Topic | Status |
|---|---|---|
| ADR-007 | Multi-agent state consistency: Hybrid SS (control plane) + EC (data plane) | PROPOSED, design complete |
| ADR-008 | RFC 8693 Mission Delegation Token chain | Design + impl + dispatcher wiring + chaos tests complete; Phase 10 (live IAM) gated |

## 4. Test architecture (49 files, 473 tests)

Layers:
1. **Claim-evidence binding** (72): every front-door claim pinned to raw evidence; LF canonicalization; overclaim-scope detection.
2. **Study analyzers**: study011 analyze/condition conformance/harness self-test/cell structure; workload design (Q-012).
3. **Script wrappers** (each experiment has pytest coverage): jar_exp_0001, assurance_adversarial, durability_fault_injection, router_evaluation, confounder, statistical_audit, model_compatibility, hci_cognitive_model, dry_run_harness.
4. **Primitives**: LAB hardening (object-identity), sycophancy prevention, provider failover + E2E outage mocks, threat model (16 vectors TH-01..TH-16).
5. **ADR-008 chain**: token exchange (20) + dispatcher wiring (7) + chaos (5).
6. **Governance**: registries (14), CI workflow schema (9), external validation pack (6), economics (5), rate-limit wiring (6).

## 5. Registries

- `data/decision_log.csv` — DEC-001..034 (34 decisions; DEC-030 records the
  owner-delegated approvals: Q-011 budget, Q-007 IP hold, ratifications)
- `data/claim_evidence_audit.csv` — 19 rows, incl. walked-back claims
- `data/open_questions.csv` — 12 questions; Q-001..Q-005, Q-007, Q-008, Q-010, Q-011, Q-012 closed/delegated; **open: Q-006 (live humans), Q-009 (clean-room)**
- `data/experiment_registry.csv` — statuses COMPLETED / METHODOLOGICAL_PILOT / PLANNED (JAR-EXP-0008 correctly not COMPLETED)
- Frozen: `data/study011_workload_manifest.json` (root_hash e823102a…),
  `data/study011_preregistration_manifest.json` v1.0.3 + LF sidecar

## 6. Remaining work (local)

1. STUDY-011 runner loop (LIVE_ONLY execution body) — blocked on API key
2. PROTOCOL_AMENDMENT 004 only if the frozen matrix changes
3. More TH vectors (multi-region consensus, federated token trust)
4. Runner-loop unit tests when the loop is implemented

## 7. External blockers

| Blocker | Class | Unblocks |
|---|---|---|
| OPENROUTER_API_KEY not in env | Environmental (key needed) | Phase 1 LIVE_ONLY (budget already approved via DEC-030) |
| Q-006: N≥30 live humans + IRB | External (people/legal) | STUDY-006 live trial |
| Q-009: clean-room Rust/Go team | External (third party) | SPEC-001 interop claims |
| External security review of ADR-008 | External (expert) | Commercial use of token schemas |

## 8. One-decision resume path

Set `OPENROUTER_API_KEY` in the environment → the frozen harness runs unchanged
(`python experiments/live_benchmark/run_study_011.py --mode LIVE_ONLY --phase 1
--workload-file data/study011_workload_manifest.json`). Rate-limit layer arms
automatically; checkpoint journal enables crash-resume. Everything else is ready.