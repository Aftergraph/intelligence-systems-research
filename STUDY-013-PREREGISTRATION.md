# STUDY-013-PREREGISTRATION.md

## Title
**STUDY-013: Independent End-to-End Implementation & Cross-Runtime Interoperability of Governed Autonomous Intelligence Systems**

**Status:** PREREGISTERED-DRAFT (pending owner approval)

---

## 1. Research Question (verbatim from §2)
> Kan en uafhængig implementør — uden adgang til vores reference-runtime eller intern coaching — implementere den offentlige systemspecifikation og interoperere korrekt med en anden runtime?

**Full chain under test:**
Human Goal → Conversation/MissionProposal → Mission → AIE authority/delegation → TG admission + execution-time revalidation → WORKS durable execution → failure/recovery → Needs You/human takeover → verification → evidence/quittance → VERIFIED_COMPLETE.

*Not an AIE-schema test. The WHOLE chain.*

---

## 2. Hypotheses (with frozen success bars)

| Hypothesis | Success bar |
|------------|-------------|
| **H1** | Independent implementation reaches **C0 conformance ≥80%** of core vectors |
| **H2** | Cross-runtime interoperability **≥80%** on hard-case suite (HC1-HC8, both directions) |
| **H3** | Unauthorized action rate **UAR=0** across HC1 (revocation), HC5 (idempotency), HC6 (stale authority) |
| **H4** | Evidence bundles verify cross-runtime **≥95%** on HC7 |
| **H5** | Implementation time **≤2x** reference-runtime estimate; clarification requests **≤K** (K pre-registered) |

---

## 3. Design

### Independent Implementer
- **N=1 primary** independent implementer (plus **N=1 secondary** if budget allows)
- Independent implementer receives **ONLY**:
  - Public spec (AIE Draft 0.3 YAML + conformance vectors + open schemas)
  - This preregistration
  - Public repos
- **No reference-runtime source code access. No coaching.

### Arms
| Arm | Description |
|-----|-------------|
| **spec-only** | No coaching, no Q&A |
| **spec+FAQ-baseline** | Public FAQ only |

### Logging
- All contact logged as clarification requests (these ARE data)
- Weekly artifact snapshots

---

## 4. Materials

| Material | Details |
|----------|---------|
| **Public spec bundle** | YAML, vectors, schemas — pinned SHA-256 |
| **Hard-case vector packs** | HC1-HC8 (8 suites, frozen) |
| **Blinded scoring rubric** | Scorer does not know which runtime produced which evidence bundle |

---

## 5. Procedure (G-13a → G-13d)

| Gate | Action |
|------|--------|
| **G-13a** | Recruit implementer; preregistration frozen |
| **G-13b** | Implementation build (time-boxed, log everything) |
| **G-13c** | Cross-runtime test suite + blinded scoring |
| **G-13d** | Results → standard-candidate decision |

### Reference Runtime (pinned)
| Component | Commit |
|-----------|--------|
| **TG** | b2462d6 |
| **AIE** | cc554ec |
| **WORKS** | 5cc6e4e |

---

## 6. Exclusions & Stopping Rules

| Trigger | Action |
|---------|--------|
| Implementer dropout | Switch to secondary arm |
| Irreconcilable spec ambiguity | File amendment (not dataset mutation) |

---

## 7. Analysis

| Measure | Method |
|---------|--------|
| Conformance % | Wilson CIs |
| Interoperability % | Wilson CIs |
| UAR (HC1/HC5/HC6) | Zero-tolerance count |
| Recovery correctness | Automated scoring |
| Evidence completeness | Bundle verification (HC7) |

**Critical:** No pooled analysis with STUDY-011 or STUDY-008 datasets.

---

## 8. Integrity

- **DO NOT OPTIMIZE FOR PASS**; pre-registered failure = valid result
- Deviations logged as amendments
- No dataset mutation after freeze

---

## Appendix: Hard Cases (HC1-HC8)

| HC | Case | Primary claim |
|----|------|---------------|
| HC1 | Revocation propagation | Revoked authority never executes post-revoke, cross-runtime |
| HC2 | Cross-org delegation | Attenuation conserves budget/permissions across org boundary |
| HC3 | Dynamic topology mutation | Org structure changes mid-mission without authority gap |
| HC4 | Budget conservation | No budget escape via delegation chains |
| HC5 | Replay/idempotency | Replayed action_id cannot double-execute or double-count |
| HC6 | Stale authority / partitions | Partitioned runtimes fail closed on stale authority |
| HC7 | Evidence compatibility | L1-L4 bundles verify across independent runtimes |
| HC8 | Human approval/takeover continuity | Takeover survives re-admission, no authority leak |

---

*End of STUDY-013 preregistration draft*
