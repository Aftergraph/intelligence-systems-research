# STUDY-015 G15-0 Methodology Review

**Status:** BUILT — draft review; protocol not frozen.

## Question reviewed

Can STUDY-015 measure system-level compositional improvement without reusing or contaminating STUDY-011 and without collapsing safety, capability, cost and latency into one opaque score?

## Findings and implemented controls

| Finding | Risk | Control now in branch |
|---|---|---|
| Low FCR can be caused by abstention | false claim of improvement | VSR + abstention reported beside FCR |
| FULL-vs-baseline cannot identify composition | attribution failure | cumulative ladder + FULL-minus + pre-specified interactions |
| Dry-run evidence can resemble live evidence | dataset contamination | explicit `execution_class` + `is_live` schema invariants |
| Disabled learning/routing can leak state | condition contamination | executable condition isolation + store reset rule |
| Implementation drift can invalidate comparisons | causal ambiguity | exact source-head manifest + canonical fingerprint |
| One composite score can hide regressions | tradeoff laundering | primary performance vector; no primary scalar score |
| EGAC multiplicative FCR claim assumes dependence structure | invalid bound | excluded from generic proof absent separately established assumptions |
| Recovery after revocation can violate containment | unsafe metric optimization | continuity vs containment failure classes |
| Post-hoc interactions invite p-hacking | multiplicity / selection bias | interaction family must freeze before execution |
| Existing STUDY-011 protocol is immutable | contamination | STUDY-015 separate ID, manifests, envelopes and admissibility rules |

## Review verdict

**READY TO BUILD, NOT READY TO FREEZE.**

G15-1 through G15-8 must be executable and green; G15-9 remains an explicit owner approval.
