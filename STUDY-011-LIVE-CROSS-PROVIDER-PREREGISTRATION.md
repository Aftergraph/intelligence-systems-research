# STUDY-011: Live Cross-Provider Replication — Pre-Registration

**Study ID:** STUDY-011
**Program:** Jonas Abde Intelligence Systems Research Program Q3 2026
**Status:** PRE-REGISTERED — FROZEN v1.0.0 (no live confirmatory execution yet)
**Version:** 1.0.0
**Freeze Timestamp (UTC):** 2026-09-04T03:00:00Z
**Authors:** Jonas Abde
**Classification:** PROTOCOL FREEZE (frozen before first live look; no post-hoc editing without PROTOCOL_AMENDMENT)

> [!IMPORTANT]
> Pre-registration of design, analysis plan, decision rules, and exclusion
> criteria **before** any confirmatory live run. Any change after first
> live look requires a numbered PROTOCOL_AMENDMENT entry in
> `STUDY-011-AMENDMENTS.md` with version bump + recomputed SHA-256.

---

## 1. Pre-Registration Statement

By freezing this document, the study authors commit to the following:

1. The hypotheses, design, sampling, and analysis plan below are **frozen**
   before any confirmatory look at live data.
2. The frozen workload set, frozen provider/model matrix, and the analysis
   script `experiments/live_benchmark/study011_analyze.py` together define
   the confirmatory analysis.
3. Any deviation from this protocol after first live look invalidates the
   pre-registration and requires a numbered amendment that is itself
   publicly recorded.
4. The simulation/live distinction is enforced at the harness level:
   `enforce_live_only_invariant()` rejects any `LIVE_ONLY` run that
   arrives with `execution_class != LIVE_VALID/LIVE_PROVIDER_FAILURE/LIVE_PROTOCOL_FAILURE`.
5. STUDY-011 is confirmatory for the questions listed in §3 and **does not
   overwrite** STUDY-008's findings (which are explicitly reclassified as
   methodological, not inferential).

---

## 2. Hypotheses (Confirmatory)

All hypotheses are tested at per-hypothesis α = 0.01 with **Bonferroni
correction** for the 3 primary hypotheses in H1 (k = 3, α_adj ≈ 0.0033).
Two-sided unless otherwise noted.

### H1 — Assurance effect (primary)
H1a. **G vs A** on FCR (False Completion Rate) per (provider, workload)
cell — paired discordant cells, McNemar with continuity correction.
- H0: π_G+ == π_A+  (proportion discordant G+ / A− equals A+ / G−)
- H1: π_G+ ≠ π_A+

H1b. **G vs A** on VSR (Verified Success Rate) per (provider, workload)
cell — paired discordant cells, McNemar.
- H0: π_G+ == π_A+
- H1: π_G+ ≠ π_A+

H1c. **F vs A** on FCR — same construction, isolates the assurance
component from the recovery loop in G.

### H2 — Authority/Budget effect (secondary)
**G vs F** on FCR — same McNemar construction. Tests whether the
authority + budget tracking layer adds the predicted effect over F alone.
- Per-hypothesis α = 0.01 (not part of the Bonferroni group).

### H3 — Retry effect (secondary)
**C vs A** on VSR — same McNemar. Tests whether the retry loop alone
adds the predicted effect without assurance.
- Per-hypothesis α = 0.01 (not part of the Bonferroni group).

### Decision rules
- A cell's pair is included only if **both** paired observations
  (`A` and comparator) are present AND the workload_id + replicate_id
  match exactly.
- Discordant pair count b + c < 10 ⇒ flag `LOW_DISCORDANT`; report
  exact binomial 95% CI on the discordant ratio; **do not** report
  McNemar χ² as decisive.
- Wilson 95% CIs on marginal rates.
- Cohen's h reported as effect size alongside any significant McNemar.

---

## 3. Design (Frozen)

| Item | Value | Source |
|---|---|---|
| Conditions (within-subjects) | A, C, F, G | `apply_condition()` in `run_study_011.py` |
| Provider strata (Phase 1) | `dialagram`, `openrouter` | Frozen matrix §6 |
| Models per stratum (Phase 1) | 3 (dialagram) + 2 (openrouter) | Frozen matrix §6 |
| Frozen workload set | 20 workloads (5 families × 4) | `data/study011_workload_manifest.json` v1.0.0 |
| Replicates per cell | 3 | `data/study011_workload_manifest.json` `replication_plan.replicates_per_cell` |
| `LIVE_VALID` per cell (target) | 58 | `replication_plan.power_target_per_cell` |
| Phase 1 total `LIVE_VALID` target | 464 (4 cond × 2 strata × 58) | `replication_plan.phase1_target` |
| `LIVE_VALID` per cell (planned max attempts) | 60 (= 20 workloads × 3 reps) | `replication_plan.live_valid_per_cell` |
| Phase 1 `LIVE_VALID` (planned max) | 480 | `replication_plan.phase1_live_valid` |
| Total Phase 1 `LIVE_ONLY` attempts (worst case incl. provider failures) | 619 | 4 × 2 × ~77 attempts (incl. `LIVE_PROVIDER_FAILURE`/`LIVE_PROTOCOL_FAILURE`) |
| Analysis unit | (provider_stratum, model, workload_id, replicate_id) cell | `pairing_key()` in `study011_analyze.py` |
| Missing-data rule | Listwise per paired-test cell | §5 |

**Critical accounting invariant (frozen before data):**
- 464 = the *minimum* `LIVE_VALID` count required to reach the per-cell
  target of 58. This is the **live confirmatory floor**.
- 619 = the *maximum* `LIVE_ONLY` attempts we will permit before
  declaring the provider stratum non-viable. The 619 figure includes
  `LIVE_PROVIDER_FAILURE` and `LIVE_PROTOCOL_FAILURE` outcomes and
  corresponds to ~3 retries per cell beyond the nominal 60 (informed by
  STUDY-008's 9/275 = 3.3% provider-failure rate, with a 3× buffer).
- The two numbers must **never be conflated**. Reporting "we did 619
  live runs" is wrong; reporting "we got 464 `LIVE_VALID` runs" is
  wrong if the cell-level `LIVE_VALID` count is < 58.

---

## 4. Sampling Plan (Frozen)

- **Workload sample:** all 20 frozen workloads (no subsampling).
- **Replicate sample:** 3 deterministic replicates per cell, identified by
  `replicate_id ∈ {0, 1, 2}`.
- **Provider/model sample:** all frozen models per stratum (matrix §6).
- **Order randomization:** replicate IDs are drawn from a frozen seed
  table in `data/study011_replicate_seed_table.json` (created at first
  run, then frozen). No re-randomization between runs.
- **Stopping rule:** continue until every cell hits 58 `LIVE_VALID`
  OR the 619-attempt ceiling is reached. Document stopping reason
  per stratum.

---

## 5. Exclusion Criteria (Frozen)

A run is classified as one of:

| Class | Condition | Counts toward denominator? |
|---|---|---|
| `LIVE_VALID` | Genuine remote call, `is_live=True`, `http_status ∈ {200, 4xx_client_error}`, `provider_request_id` present, manifest_hash matches frozen | Yes |
| `LIVE_PROVIDER_FAILURE` | Genuine remote call, `is_live=True`, transient upstream issue (timeout, 429, 5xx, connection error, malformed provider JSON) | Yes (denominator only) |
| `LIVE_PROTOCOL_FAILURE` | Genuine remote call, `is_live=True`, but harness contract violated (e.g. malformed response shape that fails integrity check) | Yes (denominator only) |
| `INVALID_PROTOCOL` | Rec lacks required fields or has wrong schema (e.g. STUDY-008 dry-run records without `is_live`/`http_status`) | No |
| `EXCLUDED` | Rec has `is_live=False` or `execution_class=SIMULATED` in any confirmatory condition | No (and a `LIVE_ONLY` violation) |

The harness rejects any `LIVE_ONLY` attempt that would yield `EXCLUDED` or
`SIMULATED`. The five classes above are mutually exclusive and exhaustive.

**Pre-registered exclusions (applied before unblinding):**
1. Any run whose `request_hash` does not match the SHA-256 of the
   payload that was actually sent.
2. Any run with `provider_request_id` shorter than 8 chars or matching
   `^(0+|test|debug)$` regex (placeholder detection).
3. Any pair where the `A`-side and comparator-side runs have
   different `manifest_hash` (workload drift between paired attempts).
4. Any cell where the same `replicate_id` is hit more than once.

---

## 6. Frozen Provider/Model Matrix (Phase 1)

Computed below; full JSON at `data/study011_provider_model_matrix.json`.
Each model is locked to a specific `exact_model_id` as returned by the
provider API. No silent substitution is permitted.

| Stratum | `exact_model_id` | Rationale |
|---|---|---|
| `dialagram` | `qwen-3.8-max` | Highest-context Dialagram model (256k); tools + reasoning supported |
| `dialagram` | `deepseek-v4` | Distinct family; was the only model to produce a `LIVE_VALID` in STUDY-008 |
| `dialagram` | `xiaomi-mimo-2.5` | Third family; also produced a STUDY-008 `LIVE_VALID` |
| `openrouter` | `google/gemma-4-31b-it:free` | Mid-tier Google free LLM, 256k ctx, distinct family from Dialagram stratum |
| `openrouter` | `z-ai/glm-5.2:free` | Mid-tier Z-AI free LLM, 256k ctx, distinct family from both Dialagram and Gemma slots |

> **Note on locking:** Both OpenRouter slots are constrained to **free**
> models (per Phase 1 budget) with context window ≥ 65k, drawn from
> distinct provider families (Google, Z-AI) to maximize independence.
> Locked against `data/openrouter_model_catalog.json` snapshot at
> `retrieved_at: 2026-09-04T01:41:00Z` (catalog SHA-256 in §8). The
> three Dialagram models are locked against
> `providers/dialagram.py` MODELS_CATALOG (source SHA-256 in §8).

---

## 7. Analysis Pipeline (Frozen)

Pre-data offline analysis script (no network): `experiments/live_benchmark/study011_analyze.py`

- Inputs: directory of run-record JSON files (one per `LIVE_ONLY` attempt).
- Integrity: validates required fields, paired keys
  (`provider_stratum, model, workload_id, replicate_id`), and the
  `LIVE_ONLY` invariant.
- Classification: each record becomes one of LIVE_VALID /
  LIVE_PROVIDER_FAILURE / LIVE_PROTOCOL_FAILURE / INVALID_PROTOCOL /
  EXCLUDED.
- Pairing: per cell, `A` paired with each of C, F, G on identical
  `(provider_stratum, model, workload_id, replicate_id)`.
- Tests: McNemar with continuity correction on discordant pairs;
  Wilson 95% CI on marginal rates; Cohen's h as effect size.
- Multiplicity: Bonferroni for H1 (3 tests, α_adj = 0.0033).
- Stratification: per-stratum inference is primary; pooled is
  exploratory only and reported as `EXPLORATORY_POOLED`.

Test file: `tests/test_study011_analyze.py` (12 tests as of freeze).

---

## 8. Freeze Manifest

| Artifact | Path | SHA-256 |
|---|---|---|
| Workload manifest | `data/study011_workload_manifest.json` | `b4d1c07b6168a5febd94be4acc67a1e91e5e417fda99a36d81a084e9870c4a4e` |
| Workload manifest root hash | (computed) | `e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06` |
| Frozen workload set | `data/study011_workloads_frozen.json` | `59f5f12cee984b71666ef7c09fdbc10ca26aa7e595a903f24f34d222a3302f14` |
| Provider/model matrix | `data/study011_provider_model_matrix.json` | (computed at freeze) |
| OpenRouter catalog snapshot | `data/openrouter_model_catalog.json` | `74237a034aa14184c600f558d6a4935bdea7aaa5c8bfbf2e306dd432c4caae10` |
| Dialagram provider source | `providers/dialagram.py` | `6ea140af0946ac5b23789f8d3b75eee5e8a1e911a2474933646cb2c849defd3e` |
| Analysis script | `experiments/live_benchmark/study011_analyze.py` | (computed at freeze) |
| Harness | `experiments/live_benchmark/run_study_011.py` | (computed at freeze) |
| Analysis test suite | `tests/test_study011_analyze.py` | (computed at freeze) |
| This document | `STUDY-011-LIVE-CROSS-PROVIDER-PREREGISTRATION.md` | (computed at freeze) |
| Frozen manifest (this section) | `data/study011_preregistration_manifest.json` | (computed at freeze) |

`data/study011_preregistration_manifest.json` is the canonical machine-readable
version of this table, with `freeze_version: "1.0.0"`, `freeze_timestamp_utc`,
and a `version: "1.0.0"` field.

---

## 9. Stopping / Go-No-Go Decision

- Phase 1 (this freeze): go if (a) all blockers in
  `STUDY-011-READINESS-REPORT.md` are closed and (b) the readiness
  report carries status `READY_FOR_OWNER_APPROVAL`. No confirmatory
  live execution without owner approval.
- Phase 2 (paid providers): requires separate preregistration amendment.

---

## 10. Limitations (Pre-Declared)

- **N per cell = 58** is below the Bonferroni-adjusted N ≈ 80
  recommended by `study011_power_analysis.py` (SEOI h = 0.5,
  α_adj = 0.0033, power = 0.80). Phase 1 will be reported with
  effect sizes and exact CIs; we will not claim a non-significant
  null result for effects below the detectable threshold.
- **Two provider strata in Phase 1** (both routed gateways). The
  "provider independence" claim in the abstract is therefore weaker
  than the Phase 2 design (which adds OpenAI, Anthropic, Google direct).
- **No double-blind external implementer** in Phase 1.
- **Live model evidence cannot reach STUDY-011's full target without
  the legal hold being lifted** for one of the paid providers.

---

## 11. Change Control

Any post-freeze change to this document or its referenced artifacts
requires a numbered `PROTOCOL_AMENDMENT_NNN` entry in
`STUDY-011-AMENDMENTS.md` with: trigger event, exact diff, before/after
SHA-256, justification, and the timestamp. Amendments are themselves
frozen at append-time.
