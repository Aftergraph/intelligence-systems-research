# CANONICAL RESEARCH ROADMAP — Unified System Program v2.0

**Program:** Jonas Abde Intelligence Systems Research Program — Q3 2026
**Date:** 2026-09-04 | **Status:** PREREGISTERED STRUCTURE — owner-approved direction
**Supersedes:** 19-ROADMAP-GATES-AND-DECISIONS.md (phases), 24-AFTER-GRAPH-ARCHITECTURE-AND-ROADMAP.md (platform topology unchanged)
**Scope rule:** ÉT samlet research- og systemprogram — ikke isolerede repo-studier. Repo-ejerskab: TG=enforcement, AIE=normative authority, WORKS=durable execution, ISR=labs/evals, GOV=contracts. Evidence-lag blandinges ALDRIG (L1 TG audit / L2 WORKS bundles / L3 AIE decisions / L4 cross-repo quittances).

**Status vocabulary:** IMPLEMENTED (code exists, tests pass) / VALIDATED (empirical evidence committed) / PREREGISTERED (frozen protocol, not executed) / PROPOSED (design exists, not frozen) / BLOCKED (dependency missing).

---

## 0. STUDY-011 SCIENTIFIC CLOSURE (must finish before parallel tracks)

| # | Item | Status |
|---|---|---|
| 0.1 | Canonical dataset freeze (470 LIVE_VALID, 8/8 cells, commit 9e4b36b) | **VALIDATED** — dataset committed; freeze amendment declaring no-further-mutation: **PENDING** |
| 0.2 | Independent lineage/dedupe audit — **DONE**: verdict FAIL→resolved by Amendment 012 (17bc1037 sub-window declared Block 3 continuation, zero run_id overlap, 6 in-flight extras reconciled; commit d484ab9) | **VALIDATED** |
| 0.3 | Analyzer summary-writer fix (KeyError 'chi2' on empty block strata) | **IMPLEMENTED-pending-commit** — results.json authoritative; writer must tolerate EMPTY/NO_OBSERVATIONS strata |
| 0.4 | Final statistical review — **DONE**: SOUND_WITH_HEDGES_REQUIRED; hedge applied to FINAL-CONFIRMATORY-SUMMARY.md (F converts abstention; G adds measured marginal H2 effect); no p-hacking found | **VALIDATED** |
| 0.5 | Update claims registry, papers, roadmap with STUDY-011 verdicts + hedges — **DONE** (commit d4cd629): C-001 refined, C-008 added, C-007 live-reversed | **VALIDATED** |
| 0.6 | Hard invariant: canonical dataset is immutable from now on (append-only corrections via amendment docs only) | **PREREGISTERED** — this roadmap binds it |

**Gate G-S0:** 0.1-0.6 all closed → parallel tracks open. **STATUS: 0.1-0.5 VALIDATED (commits 5cf5d29, d484ab9, 530dc8b, d4cd629); 0.6 immutability binding in force. G-S0 CLOSED.**

---

## 1. PARALLEL VALIDATION TRACKS (post-closure)

### Track A — MISSION-Bench Live (systems evidence)

Move from controlled/simulated bench to live models/providers under real faults.

- A.1 Live workload execution on ≥2 providers, ≥3 models incl. one small/open (per 16-BENCH model matrix) — **PREREGISTERED-DRAFT** (STUDY-008-LIVE-v2-PREREGISTRATION.md, commit 285ff1b; pending owner approval)
- A.2 Real-fault injection: provider 429/5xx, latency spikes, malformed responses, mid-mission crash+resume — **PROPOSED**
- A.3 Metrics: VSR, FCR, UAR (unauthorized action rate), recovery correctness, CPVO, CPT — **PREREGISTERED** in bench docs; live thresholds to freeze in A.1 prereg
- A.4 Blinding/scoring: automated scoring from frozen workloads only, no LLM-judge without inter-rater validation — **PROPOSED**

**Gate G-A1:** preregistration frozen → execution. **Gate G-A2:** results committed → feeds system-level claims (not standard claims).

### Track B — STUDY-006 Live Human Study (human evidence)

- B.1 Chat-only vs Mission/Needs-You/progressive-disclosure arms — **PREREGISTERED** (STUDY-006-PREREG-001, recruitment pending)
- B.2 Measures: human control perception, intervention accuracy, cognitive load (NASA-TLX), trust calibration, takeover success — **PREREGISTERED**
- B.3 Recruitment/IRB (Q-006) — **APPROVED by owner 2026-09-04** (pilots/: recruitment plan, GDPR consent, session scripts) — recruitment may launch
- B.4 System-in-the-loop: arms run against the REAL platform chain (TG admission → AIE → WORKS), not mockups — **PROPOSED** (requires Track A infra stable)

**Gate G-B1:** IRB/consent + ≥N participants → run. **Gate G-B2:** results → HCI claims registry (C-004/H-003).

### Sequencing rule
A and B run in PARALLEL after G-S0. B's system-in-the-loop arm (B.4) depends on A.1-A.2 being stable; B.1-B.3 (protocol, instruments) proceed independently now.

---

## 2. STUDY-013 — Independent End-to-End Implementation & Cross-Runtime Interoperability of Governed Autonomous Intelligence Systems

*(Numbering: STUDY-012 name is taken by the custom-agent pilot; the new study is STUDY-013.)*

**Classification:** APPROVED by owner 2026-09-04 — ACTIVE (G-13a recruitment may open).

**Core research question:**
> Kan en uafhængig implementør — uden adgang til vores reference-runtime eller intern coaching — implementere den offentlige systemspecifikation og interoperere korrekt med en anden runtime?

**Full chain under test:**
Human Goal → Conversation/MissionProposal → Mission → AIE authority/delegation → TG admission + execution-time revalidation → WORKS durable execution → failure/recovery → Needs You/human takeover → verification → evidence/quittance → VERIFIED_COMPLETE.

Not an AIE-schema test. The WHOLE chain.

### 2.1 Hard cases (all eight mandatory)

| HC | Case | Primary claim | Current support |
|---|---|---|---|
| HC1 | Revocation propagation | revoked authority never executes post-revoke, cross-runtime | TH-12 revalidate IMPLEMENTED; propagation latency unmeasured |
| HC2 | Cross-org delegation | attenuation conserves budget/permissions across org boundary | spec attenuateScope/conserveBudget; cross-org path PROPOSED |
| HC3 | Dynamic topology mutation | org structure changes mid-mission without authority gap | PROPOSED |
| HC4 | Budget conservation | no budget escape via delegation chains | BudgetLedger EXISTS; triple-tracking (WE/AIE/TG) PARTIAL |
| HC5 | Replay/idempotency | replayed action_id cannot double-execute or double-count | replayProtection: action-id in spec; cross-runtime test PROPOSED |
| HC6 | Stale authority / partitions | partitioned runtimes fail closed on stale authority | fail-closed IMPLEMENTED in TG; partition semantics PROPOSED |
| HC7 | Evidence compatibility | L1-L4 bundles verify across independent runtimes | bundle.go + hash-chain IMPLEMENTED; cross-runtime verify PROPOSED |
| HC8 | Human approval/takeover continuity | takeover survives re-admission, no authority leak | PARTIAL (approval flow exists, takeover UX not built) |

### 2.2 Measures

conformance % (C0/D1/T1/E1 profiles) · interoperability % (cross-implementation test pass rate) · implementation time · clarification requests · spec ambiguities found · semantic deviations · unauthorized action rate · recovery correctness · evidence completeness · developer friction (per 24-ROADMAP platform invariants).

### 2.3 Design constraints

- Independent implementer gets ONLY: public spec (AIE Draft 0.3 YAML + conformance vectors + open schemas), THIS preregistration, and the public repos. No reference-runtime source reading. No coaching. All contact logged as clarification requests (these ARE data).
- Reference runtime = our live stack (TG b2462d6, AIE cc554ec, WORKS 5cc6e4e). Cross-runtime tests: both runtimes pass identical vector packs on the 8 hard cases.
- Blinding: scorer does not know which runtime produced which evidence bundle.
- Success bar: C0 pass + ≥80% cross-implementation vectors + zero unauthorized actions in HC1/HC5/HC6.

**Gate G-13a:** preregistration frozen + implementer recruited. **Gate G-13b:** implementation runs (time logged). **Gate G-13c:** cross-runtime test suite + blinded scoring. **Gate G-13d:** results → standard-candidate decision.

---

## 3. Study map (whole program)

| Study | Topic | Status |
|---|---|---|
| STUDY-001 | Engineering standards gap | VALIDATED |
| STUDY-002 | JAR-EXP-0001 empirical eval | VALIDATED |
| STUDY-003 | MISSION-Bench ablation + economics | VALIDATED (deterministic testbed) |
| STUDY-004 | Model compatibility | VALIDATED |
| STUDY-005 | Confounder analysis | VALIDATED |
| STUDY-006 | HCI preregistration | PREREGISTERED (recruitment BLOCKED→unblock via Track B) |
| STUDY-008 | Live multi-model MISSION-Bench | VALIDATED (v1.1-AUDITED) |
| STUDY-009 | Durable mission recovery | VALIDATED |
| STUDY-010 | Assurance adversarial evaluation | VALIDATED |
| STUDY-011 | Live cross-provider confirmatory | VALIDATED (closure §0 pending) |
| STUDY-012 | Custom agent efficiency | VALIDATED (E0-E1 pilot, no claims) |
| STUDY-013 | Independent implementation + interoperability | PROPOSED → preregister (§2 skeleton) |
| Track A | MISSION-Bench Live | PROPOSED → preregister after G-S0 |
| Track B | STUDY-006 live execution | PREREGISTERED + BLOCKED (recruitment) |

## 4. Dependency / gate graph

```
G-S0 (STUDY-011 closure: 0.1-0.6)
 ├─→ Track A (Bench Live): G-A1 → G-A2
 ├─→ Track B (HCI): B.1-B.3 now; B.4 needs A.1-A.2
 └─→ STUDY-013: G-13a → G-13b → G-13c → G-13c → standard-candidate decision
```

Chain thesis (no overclaiming): validated system → independent implementation → external interoperability → real pilots → standard candidate. NO "platform proven" claim from any single study.

## 5. What exists vs missing

**Exists:** STUDY-011 dataset+analysis+verdicts · full-chain architecture (TH-12, plugin contract, model router, e2e demo) · evidence L1-L4 formats · conformance vectors · 8 hard-case designs mapped to real code · STUDY-006 protocol · STUDY-008 live bench precedent + infra · 24-ROADMAP platform invariants · Institution-Layer-v4 absorption (governance commit cf2e5a1).

**Missing:** dataset-freeze amendment · independent lineage audit pass · analyzer writer fix committed · independent stats review · MISSION-Bench live prereg · fault-injection harness · HCI recruitment/consent · STUDY-013 prereg full draft · independent implementer recruitment channel (EXTERNAL-IMPLEMENTER-OUTREACH.md exists — reuse) · blinded scorer · cross-runtime test suite packaging.

## 6. Execution order (exact)

1. **Now (parallel, cheap):** commit analyzer writer fix (0.3); draft STUDY-011 dataset-freeze amendment (0.1).
2. **Then:** dispatch independent lineage/dedupe audit (0.2) + independent stats review (0.4) as two separate reviewers (different model families).
3. **Then:** claims/papers/roadmap update (0.5) → declare G-S0.
4. **After G-S0:** write MISSION-Bench Live prereg (A.1-A.4) AND STUDY-013 prereg from §2 skeleton in parallel.
5. **In parallel with 4:** STUDY-006 recruitment/consent instrument (B.3 unblock).
6. **After preregs frozen:** Track A execution; STUDY-013 G-13a recruitment opens; B.4 integration begins once A.1-A.2 stable.
7. **STUDY-013 G-13c:** cross-runtime tests + blinded scoring → evidence → G-13c verdict → standard-candidate decision.

## Appendix — STUDY-013 preregistration skeleton

```
STUDY-013-PREREG-001
1. Research question (verbatim §2 above)
2. Hypotheses
   H1: independent implementation reaches C0 conformance ≥80% of core vectors
   H2: cross-runtime interoperability ≥80% on hard-case suite (both directions)
   H3: unauthorized action rate = 0 across HC1/HC5/HC6
   H4: evidence bundles verify cross-runtime ≥95% (HC7)
   H5: implementation time within 2x reference-runtime estimate; clarification
       requests ≤ K (pre-registered K); spec ambiguities catalogued with severity
3. Design
   - N=1 primary independent implementer (+N=1 secondary if budget allows)
   - arms: spec-only (no coaching) vs spec+FAQ-baseline (public FAQ only)
   - all contacts logged; weekly artifact snapshots
4. Materials
   - public spec bundle (YAML, vectors, schemas), pinned SHA-256
   - hard-case vector packs HC1-HC8 (8 suites, frozen)
   - blinded scoring rubric
5. Procedure
   - G-13a recruit → G-13b build (time-boxed, log everything) → G-13c cross-tests
   - reference runtime pinned at TG b2462d6 / AIE cc554ec / WORKS 5cc6e4e
6. Exclusions & stopping
   - implementer dropout → secondary arm; irreconcilable spec ambiguity → amendment
7. Analysis
   - conformance %, interop %, UAR, recovery correctness, evidence completeness
   - Wilson CIs; no pooled analysis with STUDY-011/008 datasets
8. Integrity
   - DO NOT OPTIMIZE FOR PASS; pre-registered failure = valid result
   - deviations logged as amendments; no dataset mutation after freeze
```
