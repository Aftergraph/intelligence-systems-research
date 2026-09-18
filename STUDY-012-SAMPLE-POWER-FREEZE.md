# STUDY-012 Sample / Power Freeze v0.1

**Status:** FROZEN-FOR-REVIEW; execution remains blocked.

Primary design is paired across J/D/JD/DI for each workload trace. Eight R2 classes are frozen, with 30 replicates per class-condition cell.

- 8 adversarial classes
- 4 conditions
- 30 paired replicates per class-condition
- nominal observations = **960**
- paired trace units = **240** per condition

The 30-replicate floor is an estimation floor, not a claim of universal power. All rates report Wilson 95% CIs. Judge-vs-oracle disagreement uses paired McNemar analysis. Any claim requiring a smaller effect than achieved confidence bounds remains underpowered/UNKNOWN rather than interpreted as null evidence.

Execution MUST NOT begin until exact provider/model IDs, deterministic oracle implementations, manifest hashes and analysis code are frozen.
