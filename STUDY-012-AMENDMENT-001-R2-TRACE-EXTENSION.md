# STUDY-012 Amendment 001 — R1/R2 Trace Extension

**Status:** FROZEN-FOR-REVIEW — NO LIVE EXECUTION  
**Parent:** ICT-EXP-001 v1.0.0 (immutable; not modified)  
**Extension:** R1/R2-TRACE-EXT v1.0.0

## Reason

The frozen ICT workload set directly covers revocation and adversarial-evidence families but does not prospectively instantiate all Research Protocol v0.2 R2 classes. This amendment adds six synthetic trace fixtures without mutating or reinterpreting the parent observations.

## Added classes

- stale_state
- contradiction
- cross_subject_isolation
- constraint_decay
- replay
- crash_recovery

Together with parent-derived revocation and adversarial_evidence, the prospective dry-run surface reaches 8/8 R2 classes.

No result from this amendment may be pooled with the frozen parent as if it were preregistered in ICT-EXP-001. Reporting remains stratified by source workload set.
