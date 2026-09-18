# STUDY-012 Recovery-v4 Post-Run Report — 2026-09-18

**Execution status:** COMPLETED  
**Confirmatory admissibility:** PASS for the frozen recovery-v4 matrix  
**Execution source commit:** `0ce31cb4c9b9ad125db9e3ddfd314618aa930bee`  
**Raw observations SHA-256:** `7530a46da7faa935448f207dd3a276e751a4cc8b38d48585d29764b184fe71bd`

## Execution accounting

- Planned observations: 960
- Written observations: 960
- Unique trace IDs: 960
- LIVE_VALID task observations: 960/960
- Task provider failures: 0
- Runner failures: 0
- Model calls: 1,469
- Accounted provider cost: USD 0.00
- Runner wall clock: 1,379.88 seconds
- Human interventions during the execution loop: 0
- Provider allocation: 480 Local Ollama / Qwen3.6 and 480 NVIDIA Direct / Nemotron 3 Ultra
- Every provider had 120 J, 120 D, 120 JD, and 120 DI observations.

The USD 0.00 figure is the runner's accounted provider cost. It does not represent local hardware/electricity cost or assign a monetary value to free-tier/free-endpoint capacity.

## Frozen-analysis inheritance

The preregistration required analysis implementation to be frozen before live execution. The inherited frozen analyzer
`experiments/live_benchmark/study012_analyze.py` remains byte-identical to its earlier freeze:

`94f8f329a8322c622ffb0109d4961d805ce35ed406ce145a4d2234c81a6f7ecd`

The frozen analyzer, applied through a schema-normalization adapter to the v4 rows, returns:

- n = 960
- J/D/JD/DI = 240 each
- observational J VERIFIED = 240
- deterministically VERIFIED = 720
- independently VERIFIED = 240
- judge/oracle disagreements = 0
- applicable adversarial classes = 8
- covered adversarial classes = 8

The post-run v4 analyzer adds deterministic Wilson/McNemar presentation and metrics-schema projection. It does not alter frozen row outcomes.

## Condition outcomes

| Condition | n | Canonical outcome | Additional evidence |
|---|---:|---|---|
| J | 240 | 240 UNESTABLISHED | observational judge emitted VERIFIED on 240/240 |
| D | 240 | 240 VERIFIED | deterministic oracle VERIFIED on 240/240 |
| JD | 240 | 240 VERIFIED | judge and deterministic oracle agreed VERIFIED on 240/240 |
| DI | 240 | 240 VERIFIED | deterministic oracle + unique Sentinel receipt on 240/240 |

This distinction is essential: observational J verdicts are not canonical verification under ISE-R1.

## Judge ↔ oracle disagreement

Paired JD analysis:

- paired observations: 240
- both VERIFIED: 240
- judge VERIFIED / oracle not VERIFIED: 0
- judge not VERIFIED / oracle VERIFIED: 0
- total disagreements: 0/240 = 0%
- Wilson 95% CI for disagreement rate: 0% to 1.5754%
- exact two-sided McNemar p = 1.0 because there are no discordant pairs

Provider-stratified JD results are also 0/120 disagreements for both task strata. The corresponding Wilson 95% upper bound is approximately 3.102% per provider.

McNemar p=1.0 is not proof that disagreement is impossible. It records that this frozen sample contained no discordant pairs.

## R2 adversarial coverage

All eight frozen R2 classes contain 120 observations each:

- adversarial_evidence
- constraint_decay
- contradiction
- crash_recovery
- cross_subject_isolation
- replay
- revocation
- stale_state

For every class:
- 120/120 task observations were LIVE_VALID;
- 30 J rows remained comparator-only;
- 90/90 D/JD/DI rows survived the class-specific deterministic oracle and became canonical VERIFIED;
- 30/30 DI rows received independent Sentinel verification.

Adversarial coverage = 8/8 = 100%.

## Independent verification audit

DI audit:

- DI rows: 240
- independent receipts present: 240/240
- unique receipt IDs: 240
- all receipt IDs use the `dvr_` form
- verifier ID on all receipts: `sentinel:domain-verifier`
- independent result `passed`: 240/240
- Sentinel verdict VERIFIED: 240/240

No missing independent receipt is counted as success.

## Research metrics v0.1

Counting rule: J is a comparator-only condition and cannot enter `verified_claims` as canonical verification. Therefore D/JD/DI form the 720 observation-level verifiable-claim denominator.

Canonical counters:

- verifiable_claims = 720
- deterministically_verified_claims = 720
- verified_claims = 720
- judge_only_verified_claims = 0
- independently_verified_claims = 240
- applicable_adversarial_classes = 8
- covered_adversarial_classes = 8

Derived metrics:

- DVCR = 1.0
- JCR = 0.0
- IVCR = 1/3 ≈ 0.333333
- AC = 1.0

DVCR 720/720 has Wilson 95% CI approximately 99.4693%–100%.

IVCR is the schema ratio across all canonical verified claims. Separately, the DI-conditional independent-verification pass rate is 240/240 = 100%.

Replication/falsification/progress-event counters are conservatively left at zero in this receipt because the frozen protocol does not provide an unambiguous post-hoc event-counting rule for those fields.

Total token resource is recorded as null rather than undercounted: task token counts are persisted, but judge token counts were not persisted in the v4 row schema.

## Frozen hypothesis disposition

### H1 Grounding — SUPPORTED

No judge-only comparator row became canonical VERIFIED. All 720 deterministic-verification rows became canonical VERIFIED.

Notably, the judge observationally emitted VERIFIED on all 240 J rows, but the authority boundary correctly kept all 240 canonical outcomes UNESTABLISHED.

### H2 Judge disagreement — WALKED_BACK

The preregistered hypothesis expected measurable LLM-judge ↔ deterministic-oracle disagreement.

Observed: 0/240 paired JD disagreements.

Within this frozen execution, the predicted measurable disagreement did not occur. Effects below the achieved confidence bound remain unresolved; this is not a claim that LLM judges universally agree with deterministic truth.

### H3 Trace robustness — SUPPORTED

All 8/8 applicable R2 classes were covered, and every canonical VERIFIED outcome in deterministic conditions survived the frozen class-specific oracle.

### H4 Independence — SUPPORTED

All 240 DI rows had unique passing Sentinel verification receipts. Absence of independent evidence was never counted as success.

## Limitations

1. **Synthetic exact-token workload design.** The eight fixtures use deterministic response contracts. The zero JD-disagreement result should not be generalized to open-ended evaluation tasks.
2. **Single observational judge family.** NVIDIA Nemotron 3 Super served as the J/JD judge across task strata; judge-family generalization is untested.
3. **Within-class resolution.** Each R2 class has 30 JD pairs, so a zero-disagreement class still has a Wilson 95% upper bound of roughly 11.35%.
4. **Task-provider scope.** Results cover Local Qwen3.6 and NVIDIA Nemotron 3 Ultra under the frozen v4 settings, not arbitrary models/providers.
5. **Token accounting.** Judge token counts were not persisted, so total tokens are not reported rather than undercounted.
6. **Cost accounting.** USD 0.00 is provider-accounted cost; local compute and energy are excluded.
7. **Novita Sandbox scope.** Novita's two-sandbox checkpoint/restore path was independently proven as execution-fabric capability, but it was not an active inference dependency of the 960-row v4 runner.
8. **No external replication claim.** This execution is internal Aftergraph evidence and does not constitute E5/E6 independent external reproduction.

## Scientific disposition

Recovery-v4 removes the provider-availability confound that invalidated the earlier full matrix. The frozen 960-observation v4 matrix is complete, balanced, and fully LIVE_VALID.

The evidence supports H1, H3, and H4 within the frozen design. H2 is walked back because the preregistered measurable disagreement did not appear.

This report does not merge PR #111 and does not claim external validation, universal model behavior, AGI improvement, or market effect.
