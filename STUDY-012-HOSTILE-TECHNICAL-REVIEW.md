# STUDY-012 Hostile Technical Review

**Study:** STUDY-012 / ICT-EXP-0001  
**Review cut:** PR #53 at head `8fb758b6556a27cbce94db10044edd02441f85ca`  
**Review type:** Internal hostile technical review, pre-confirmatory  
**Verdict:** **BLOCKED FOR CONFIRMATORY EXECUTION**  
**Empirical outcomes inspected:** None

## Executive finding

The current implementation is valuable as a deterministic **mechanism-conformance harness**, but it is not yet a valid confirmatory empirical experiment for the broader institution-layer claim.

The decisive problem is pseudoreplication. `run_scenario()` computes outcome directly from whether the condition contains the control family named in `REQUIRED_CONTROL`. Domain, replicate, seed, fixture state, and agent/model behavior do not influence the protected-side-effect outcome. Repeating those deterministic rows 4,200 times would increase row count without increasing empirical information.

The protocol therefore MUST NOT be frozen or executed as a confirmatory statistical study in its current form.

---

## Findings

### P0-1 — Outcome is encoded by the treatment definition

**Files:**
- `experiments/institutional_containment/harness.py`
- `experiments/institutional_containment/runner.py`

`run_scenario()` resolves:

```text
required = REQUIRED_CONTROL[scenario.failure_class]
blocked = required in controls
```

The treatment assignment therefore determines the outcome by construction. The acting synthetic agent always attempts the action, while the condition's declared control-set deterministically decides whether it is blocked.

This is appropriate for a conformance test of intended semantics. It is not evidence that the control produces the same effect under a real autonomous runtime, model, workload, race, failure, or implementation defect.

**Required fix:** Split the study into two evidence classes:

1. **STUDY-012A — deterministic institutional conformance.** Property/conformance tests only; no inferential p-values or sample-size claims from duplicated deterministic trials.
2. **STUDY-012B — empirical containment benchmark.** Real agent/runtime execution against local isolated fixtures, with randomized workload/adversarial variation and independently observed side effects. The safety boundary remains synthetic/local; only the acting system becomes behaviorally real.

---

### P0-2 — Three domains are labels, not three operational workloads

**Files:**
- `data/study012_workload_manifest.json`
- `experiments/institutional_containment/runner.py`
- `experiments/institutional_containment/harness.py`

All three domains expose the same ten scenario IDs and the same canonical synthetic targets. `run_workload_matrix()` passes only `condition` and `scenario` into `run_scenario()`. The domain and fixture-state digest are recorded as provenance but never affect execution semantics.

Consequently, `repository_operations`, `structured_ledger`, and `agent_orchestration` currently generate domain-labeled copies of the same deterministic event model.

**Required fix:** Introduce domain-specific fixture adapters and protected side effects. Ground truth must be derived from fixture state transitions, not from the domain label. A test must demonstrate that domain-specific fixture behavior can change reachability/evidence while preserving the same abstract scenario class.

---

### P0-3 — The frozen power plan counts duplicated deterministic rows as observations

**Files:**
- `experiments/institutional_containment/power.py`
- `data/study012_power_plan.json`
- `experiments/institutional_containment/harness.py`

The current plan requires 577 observations/condition and rounds to 600 observations/condition across 20 replicates, for 4,200 condition-runs. However, replicate seed currently changes ordering, not the underlying outcome. The effective experimental information is therefore not 600 independent observations per condition.

The conservative independent-proportion approximation is not the main problem. The main problem is that the current observation generator does not generate independent or behaviorally varying observations at all.

**Required fix:** Mark the current power artifact `INVALIDATED_BY_HOSTILE_REVIEW` or scope it explicitly to the future empirical phase. Recompute power only after the empirical unit of analysis, within-pair correlation assumptions, workload variation, and endpoint decision rules are frozen.

---

### P0-4 — Primary I6-vs-I5 contrast bundles multiple increments and leaves one inert

**Files:**
- `experiments/institutional_containment/harness.py`
- `STUDY-012-INSTITUTIONAL-CONTAINMENT-PREREGISTRATION.md`

I6 adds `mission_binding`, `budget`, and `revocation_propagation` simultaneously beyond I5. In the current `REQUIRED_CONTROL` mapping, `budget` and `revocation_propagation` are operative, while `mission_binding` is not required by any failure class.

Thus the primary comparison cannot attribute incremental benefit to a single mechanism, and one claimed I6 mechanism is currently untested.

**Required fix:** Either:
- define I6 as an explicitly bundled institution-package treatment and add component ablations for mission binding, budget conservation, and recursive revocation; or
- expand the ladder so each increment is separately identifiable.

At minimum, add a canonical mission-binding violation scenario before claiming that mechanism is covered.

---

### P0-5 — Several preregistered primary metrics have no executable measurement path

**Files:**
- `STUDY-012-INSTITUTIONAL-CONTAINMENT-PREREGISTRATION.md`
- `experiments/institutional_containment/runner.py`
- `experiments/institutional_containment/analyze.py`

The preregistration defines UEAR, CACR, TMVR, ETDR, RAAR, RPT, VSR, FCR, CPVO, CPT, HIR, latency, and implementation complexity. Current raw records contain attempted/blocked/violation/transcript/evidence fields but do not provide sufficient raw data for several required endpoints, including recursive-authority counts, revocation timing distribution, cost accounting, verified terminal-state outcomes, or human intervention.

**Required fix:** Freeze an endpoint-to-raw-evidence table. Every confirmatory metric must have:
- numerator and denominator definition;
- raw fields and units;
- source-of-truth producer;
- exclusion behavior;
- analysis function;
- golden test.

No endpoint may be reconstructed from the acting agent transcript.

---

### P1-6 — Statistical decision rules remain deliberately incomplete

**Files:**
- `STUDY-012-INSTITUTIONAL-CONTAINMENT-PREREGISTRATION.md`
- `experiments/institutional_containment/analyze.py`

The preregistration still requires exact multiplicity correction and endpoint-specific non-inferiority margins before confirmatory execution. The analysis correctly leaves `winner = None` and an unassigned interpretation.

This is good fail-closed behavior, but it means the protocol is not freeze-ready.

**Required fix:** Freeze and justify endpoint-specific margins, family-wise testing strategy, catastrophic-endpoint override rules, and SUPPORT/NARROW/REJECT decision logic before any confirmatory outcome is visible.

---

### P1-7 — Frozen seed-table requirement is not implemented

**File:** `STUDY-012-INSTITUTIONAL-CONTAINMENT-PREREGISTRATION.md`

The protocol requires seed generation before confirmatory execution and persistence in a frozen seed table. The current runner accepts arbitrary caller-provided `seed` and `replicate_id` values.

**Required fix:** Generate, hash, and freeze the exact empirical replicate/seed schedule. Confirmatory mode must reject any seed/replicate tuple not present in that artifact.

---

### P1-8 — `source_commit` provenance is caller asserted

**File:** `experiments/institutional_containment/runner.py`

`source_commit` is validated only as a 40-character lowercase hexadecimal string. The runner does not establish that the supplied SHA is the executing source revision.

**Required fix:** Bind execution provenance to an independently derived source revision or immutable packaged artifact digest. Caller-supplied provenance must not be treated as authoritative evidence.

---

### P1-9 — G12-10 is not independent yet

This document is an internal hostile review. It can identify blockers, but it must not be represented as independent replication or external peer review.

**Required fix:** After the P0/P1 design blockers are resolved, request at least one reviewer who did not implement the harness and preserve their review disposition before the first confirmatory look.

---

## What is already strong

The review does **not** invalidate the engineering work already completed. The following remain useful and should be retained:

- fail-closed synthetic-only target enforcement;
- no-silent-fallback invariant;
- independent evidence/verification-authority boundary;
- exact manifest and fixture provenance fields;
- condition-conformance tests;
- I0 adversarial-opportunity reachability tests;
- paired integrity rejection for duplicate, missing, mismatched, fallback, and unreachable rows;
- research registry entries that keep the hypothesis OPEN and permit NARROW/REJECT;
- no confirmatory outcomes generated or inspected.

These are prerequisites for a strong study. They are not themselves evidence for the institution-layer effectiveness claim.

---

## Required disposition

**Current gate state:**

```text
G12-1  workload manifest             PARTIAL — topology frozen; operational domain fixtures not yet real
G12-2  injection reachability        PARTIAL — deterministic conformance reachability only
G12-3  condition conformance         PASS for synthetic harness
G12-4  no silent substitution        PASS
G12-5  evidence independence         PASS for synthetic harness
G12-6  synthetic safety boundary     PASS
G12-7  analysis integrity            PASS for current record schema; endpoint coverage incomplete
G12-8  power/sample size             BLOCKED / requires empirical-design recomputation
G12-9  research registries           PASS
G12-10 hostile technical review      INTERNAL REVIEW COMPLETE — BLOCKED; independent review still required
```

**Confirmatory execution authorization:** **DENIED**

No `SUPPORT`, `NARROW`, or `REJECT` result may be generated from the current deterministic harness. Its outputs may be labeled only as conformance/property-test evidence.

## Recovery sequence

1. Reclassify the current harness as STUDY-012A deterministic conformance.
2. Specify STUDY-012B empirical containment architecture with real agent/runtime behavior inside local isolated fixtures.
3. Implement genuinely domain-specific fixtures and side-effect observers.
4. Add mission-binding coverage and disentangle the I6 incremental mechanisms.
5. Implement the full raw endpoint schema.
6. Freeze outcome-blind seed schedule and independently bound source provenance.
7. Freeze justified statistical/non-inferiority decision rules.
8. Recompute power against the actual empirical unit of analysis.
9. Run an independent hostile review.
10. Freeze v1.0.0 only after every blocking finding is resolved.
