# Executive Summary — Jonas Abde Intelligence Systems Research Program
**Principal Researcher:** Jonas Abde
**Program State:** RESEARCH & ENGINEERING LIFECYCLE PHASES 1–10 COMPLETED; STUDY-011 LIVE CONFIRMATORY RUN EXECUTED AND FROZEN
**Defensible Outcome:** **Level C+ (Validated Research Result with In-Tree Alternative Implementation) / Provisional-D (Candidate Specification pending Blind External Reproduction)**
**Gate Evaluation:** **No defensible D1/D2/D3 percentages are supported by the audited record. Final preregistered STUDY-011 verdicts are H1 REVERSED / H2 SUPPORTED / H3 REVERSED.**
**Audit Status:** AUDIT-EVID-001 + STUDY-011 post-execution reconciliation — current through 11 September 2026
**Snapshot Date:** 11 September 2026

> [!IMPORTANT]
> **Current evidence boundary:** earlier revisions of this program overstated
> simulation, pilot and readiness evidence. STUDY-008 remains a methodological
> pilot with 2/275 `LIVE_VALID` runs. STUDY-011 has now supplied the first frozen
> preregistered cross-provider confirmatory dataset: 470 `LIVE_VALID` records,
> 8/8 cells with at least 58 observations. The frozen outcomes are not a blanket
> validation of the original thesis: H1 and H3 were **REVERSED**; H2 was
> **SUPPORTED** in both provider strata. Historical contrary language remains
> provenance, not current program truth.

---

## 1. The Core Research Finding

Modern artificial intelligence engineering is transitioning from stateless conversational inference to long-horizon, autonomous, multi-agent systems. The program now has three distinct evidence layers that must not be collapsed into one claim: deterministic/simulated benchmark evidence, live confirmatory provider evidence, and still-unexecuted human/external-replication evidence.

1. **Deterministic reliability evidence remains useful but scoped.** MISSION-Bench and related in-tree testbeds show large false-completion, recovery, authority and cost effects under controlled failure injection. Those figures are reproducible engineering/benchmark evidence; they are not population-level live-provider estimates.
2. **STUDY-011 changed the live interpretation.** The frozen `canonical-run-002` dataset contains 470 `LIVE_VALID` records across 8/8 adequately populated cells. H1 (assurance lowers FCR) was **REVERSED** because models in A/C frequently abstained, driving baseline FCR to a floor near zero. H3 (retry alone adds effect) was also **REVERSED**: retry without assurance did not overcome abstention.
3. **The strongest live confirmatory result is the marginal authority+budget effect.** H2 was **SUPPORTED** in both provider strata (`p < 0.001`, effect size `h ≈ 2.5`). Condition F already converts much of the abstention into successful action through assurance invocation; Condition G adds a separately measured authority+budget effect over F. The defensible claim is that the full governance stack adds measurable value over assurance alone in this frozen study, not that governance generally “unlocks” models.
4. **The architecture remains compositional, not a claim of a wholly new discipline.** SPEC-001/AIE work composes existing transport, telemetry, identity and policy substrates rather than replacing them. External work such as STEAD narrows the novelty surface further and is explicitly part of the current overlap/delta program.
5. **Human and external replication gates remain open.** Human preference/HEVO claims are untested with live humans (`N=0`); the 6.6 → 2.0 turn result is GOMS/persona simulation. The alternate runtime implementations are in-tree/same-program evidence, not blind independent reproduction. External standards/publication maturity must therefore remain below those unresolved gates.

---

## 2. Program Artifacts & Current Status

| Deliverable Area | Concrete Artifacts | Current Evidence Status |
| :--- | :--- | :--- |
| **Foundational Gap Study** | [`STUDY-001-ENGINEERING-STANDARDS-GAP.md`](STUDY-001-ENGINEERING-STANDARDS-GAP.md) | Prior-art/gap analysis; novelty is being narrowed against newer formal work |
| **Normative Specification** | [`SPEC-001-MISSION-CONTRACT-v0.1.md`](SPEC-001-MISSION-CONTRACT-v0.1.md), schemas | Deterministic/formalization evidence; candidate specification |
| **Human-First Experience** | `prototype/`, [`STUDY-006-HCI-PREREGISTRATION.md`](STUDY-006-HCI-PREREGISTRATION.md) | GOMS/persona simulation only; **N=0 live humans** |
| **Reference Implementation** | `runtime/`, `assurance/`, `delegation/` | In-tree implementation and adversarial tests |
| **Alternative Implementations / Adapters** | `validation/`, `external_validation_pack/`, `adapters/` | In-tree conformance; blind external reproduction still pending |
| **Deterministic Benchmarks** | STUDY-002/003/004 and MISSION-Bench data | Simulation/deterministic evidence; do not label as live provider efficacy |
| **Live Pilot** | [`STUDY-008`](STUDY-008-LIVE-MISSION-BENCH-RESULTS.md) | 2 `LIVE_VALID` / 275 attempts; **METHODOLOGICAL_PILOT** |
| **Live Confirmatory** | STUDY-011 preregistration + `canonical-run-002` + frozen analysis | **470 LIVE_VALID; H1 REVERSED / H2 SUPPORTED / H3 REVERSED** |
| **Security & Threat Model** | `security/`, threat-model and adversarial suites | Deterministic/adversarial fixture evidence; not a universal security guarantee |
| **Normative Conformance** | `conformance/` | 14/14 in the current normative suite; implementation conformance, not external adoption |
| **Research Registries** | `data/claim_registry.csv`, `data/claim_evidence_audit.csv`, `data/hypothesis_registry.csv` | Being reconciled to evidence-scoped status; historical rows retained |
| **Scientific Publications** | `PAPERS/` Papers 01–05 | Paper 01 superseded pending reconciliation; Papers 02–04 re-audit hold; Paper 05 working manuscript with disclosures |
| **SDO / External Contribution Track** | `standards/`, publication/export artifacts | Candidate work only; blind external reproduction and other maturity gates remain open |

---

## 3. Frozen STUDY-011 Confirmatory Result

Canonical evidence:

- Dataset: `data/study011_runs/confirmatory/canonical-run-002/`
- Analysis: `data/study011_runs/confirmatory/canonical-run-002-analysis/`
- Freeze: `STUDY-011-AMENDMENT-011-POST-EXECUTION-FREEZE.md`
- Valid sample: **470 `LIVE_VALID` records; 8/8 cells ≥58**

| Hypothesis | Frozen verdict | Interpretation |
|---|---|---|
| **H1 — assurance lowers FCR** | **REVERSED** | Baseline A/C models often abstained, so FCR(A) was already at/near zero; G cannot improve a zero floor |
| **H2 — authority+budget adds effect over F** | **SUPPORTED** | Both provider strata show the preregistered direction with `p < 0.001` and `h ≈ 2.5` |
| **H3 — retry alone adds effect** | **REVERSED** | C behaves like A; retry without assurance does not overcome abstention |

The independent statistical review disposition is **SOUND_WITH_HEDGES_REQUIRED**. The mechanism should therefore be described as: assurance invocation (F) drives the main abstention→action transition; authority+budget (G) adds a measurable marginal effect over F. This is deliberately narrower than earlier “full stack universally wins” language.

---

## 4. Audited Metrics and Evidence Classes

```text
============================================================================================
 RESULT / METRIC                         VALUE / VERDICT              EVIDENCE CLASS
============================================================================================
 MISSION-Bench observed FCR              0.0% in evaluated sample     DETERMINISTIC / SIMULATED
 MISSION-Bench CPVO change               -81.3% in tested cost model  SIMULATION_SUPPORTED
 Human HEVO                              6.6 -> 2.0 turns             GOMS SIMULATION; N=0 HUMANS
 SPEC-001 conformance                     14/14                        DETERMINISTIC IN-TREE
 STUDY-008                                2 / 275 LIVE_VALID           METHODOLOGICAL PILOT
 STUDY-011 canonical sample               470 LIVE_VALID               LIVE CONFIRMATORY
 STUDY-011 H1                             REVERSED                     LIVE CONFIRMATORY
 STUDY-011 H2                             SUPPORTED                    LIVE CONFIRMATORY
 STUDY-011 H3                             REVERSED                     LIVE CONFIRMATORY
 Blind external reproduction              PENDING                      NOT YET SATISFIED
 Live human UX validation                 PENDING                      N=0 HUMANS
============================================================================================
```

## 5. Current Research Rule

No current-facing paper, README, registry, generated export or public documentation may claim a maturity level stronger than the exact evidence it cites. In particular:

- simulation must not silently become live evidence;
- in-tree alternative implementations must not be described as blind external reproduction;
- `N=0` human studies must not become human-validation claims;
- a preregistered reversed hypothesis remains visibly **REVERSED**;
- `PUBLICATION_READY` is an evidence gate, not a formatting/completeness label;
- historical claims remain addressable for provenance but cannot masquerade as current truth.
