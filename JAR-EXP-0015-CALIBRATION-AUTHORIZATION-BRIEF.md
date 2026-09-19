# JAR-EXP-0015 — Calibration Authorization Brief

**Status: NOT AUTHORIZED. This brief authorizes nothing. Gate A (the independent
semantic review) is now closed by a real isolated CI run; the one remaining human gate
is Gate B (owner approval), whose signature this brief deliberately does not cast.**

Date prepared: 2026-09-20
Predecessor: JAR-EXP-0014 (returned `CALIBRATION_COMPLETE_NO_THRESHOLD`)
Scope of this brief: **calibration stage only.** Holdout evaluation is a separate
gate, a separate approval, and a separate spend.

---

## 1. What is already frozen and independently verified

Everything below is deterministic, zero-network, and reproducible from this working
tree without a provider credential.

| Item | Value |
| --- | --- |
| Active protocol | `jar-exp-0015.protocol/0.4` (Amendment-004 activation) |
| Dataset | `jar-exp-0015.dataset/0.3`, status `FROZEN_PREEXECUTION` |
| Cases | 3904 = 8 decision types × 488 |
| Split | 1952 calibration / 1952 holdout, seed `150020`, 244 per type per side |
| Dataset SHA-256 | `51846d8b4a95540a8e182a823a7256fbdd69d61b3244f89e078db77ad7e0496e` |
| Split manifest SHA-256 | `46b0123ed31b27d80823e518bef9e24bf4f1cc672f763d7b75e446698a00b745` |
| Calibration manifest pin | `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762` |
| Amendment chain | 001 sample size · 002 rounding metadata · 003 v0.2 non-execution-eligible · 004 v0.3 activation |

Verification state at the pinned manifest:

- `scripts/verify_jar_exp_0015_semantic_review.py` — **38/38 PASS**, verdict `PASS_WITH_FINDINGS`
- `scripts/verify_jar_exp_0015_dataset.py` — **24/24 PASS**
- `scripts/verify_jar_exp_0015_analysis.py` — **14/14 PASS**
- `tests/test_jar_exp_0015_*.py` — **37 passed**

The falsification floor the preflight enforces is 32 attempts; the verifier currently
makes 38. Any future edit to a manifest-tracked file moves the pin, invalidates the
review and the approval simultaneously, and returns the gate to `NO_GO`.

### Why v0.3 and protocol v0.4

JAR-EXP-0014 used a dataset whose projection retained only part of the case semantics,
so the state actually sent to the provider was not the state the labels were derived
from. Amendment-003 ruled dataset v0.2 non-execution-eligible for that reason. v0.3
encodes every semantic in the single `scenario` field, which makes the projection
lossless by construction. The verifier proves this rather than asserting it:
checks 08–10 confirm the projection is an identity over v0.3, that `scenario` is the
only key present, and that no verbatim label token (`fast`, `escalate`, `true`,
`critical`, …) appears in any scenario text. Zero label leakage across all 3904 cases.

No provider call has ever been made under v0.2 or under any superseded protocol.

---

## 2. The two gates that remain — and why neither can be closed from inside this repo

### Gate A: content-addressed semantic review

The preflight requires a record at the gate's `semantic_review_ref` carrying
`independent: true`, a `PASS`/`PASS_WITH_FINDINGS` verdict, the current manifest pin,
at least 32 falsification attempts, and an `evidence_ref` pointing at a hosted run.

**Gate A is CLOSED.** The `jar-exp-0015-semantic-review` job in `.github/workflows/ci.yml`
(added in `fad7fb9`, checkout hardened with `fetch-depth: 0` in `1d5cb40` so check 36 sees
full history) ran `scripts/verify_jar_exp_0015_semantic_review.py` on an isolated GitHub
Actions runner against commit `1d5cb40` and concluded `success`: verdict
`PASS_WITH_FINDINGS`, 38 falsification attempts, `calibration_manifest_sha256 = dc5d7a94…`.
Its real output was transcribed verbatim into
`data/jar_exp_0015_semantic_review_20260919.json` and wired into the gate's
`semantic_review_ref` (commit `1a2dc7f`), exactly as JAR-EXP-0014 did
(`github-actions:Aftergraph/intelligence-systems-research:run/35434484417`). The point of
the field is that the verification happened somewhere without write access to the thing
being verified — this run did (a fresh GitHub-hosted clone), so the record is truthful. Its
`evidence_ref` is
`github-actions:Aftergraph/intelligence-systems-research:run/35473954572:job/105979835931`.

### Gate B: owner approval + budget authorization

The preflight requires a record at `owner_approval_ref` with `approved: true` and
`network_calls_authorized: true`, attributed to a named principal with a
timezone-aware timestamp, and with four fields byte-identical to the gate:
`requested_typesafe_model`, `calibration_manifest_sha256`, `max_provider_calls`,
`max_cost_usd`.

An unsigned template is at
`data/jar_exp_0015_calibration_approval_PENDING.json`. It is deliberately **not**
referenced by the gate — both authority booleans are `false`, so wiring it would
change nothing except the blocker name. The gate's refs stay `null`, which is the
truthful state.

---

## 3. What signing actually buys, and what it costs

Pricing is frozen in `data/jar_exp_0015_typesafe_pricing_v01.json` and re-validated
against live provider documentation both before every reservation and immediately
before every atomic transport claim.

| Term | Value |
| --- | --- |
| Model | `jev-1.13.0` (concrete pin; floating tags are rejected by the preflight) |
| Input | $0.042 / Mtok |
| Output | free |
| Conservative per-request bound | 65 536 input tokens |
| Worst case per request | `ceil(65536 × 0.042 / 1e6 × 1e6)` = **2753 µUSD** |
| Calibration stage (1952 calls) | 1952 × 2753 = **5 373 856 µUSD = $5.373856** |
| Rounded stage ceiling | **$5.38** |
| Both stages, if holdout is later approved | **10 747 712 µUSD = $10.747712** |

Signing Gate B authorizes **$5.38 and 1952 provider calls, calibration stage only.**
It does not authorize holdout. It does not authorize retries: `RetryPolicy(max_retries=0)`
is frozen, `sdk_retries_allowed` is `false` in both gates, and a lost response is a
failed case, not a re-spend.

For reference, JAR-EXP-0014 spent $0.44 across 158 calls and returned `NO_THRESHOLD`
with 3 critical-risk errors. The 0015 design is the correction of the measurement
fault, not a rerun of the same measurement.

### The feasibility bar you are buying an answer to

The preregistered acceptance rule is a Wilson upper bound on the error rate at or
below 0.05. `wilson_upper(0, 73) ≤ 0.05`, so **74 accepted cases with zero errors is
the floor**; below that the stage can only ever return `NO_THRESHOLD`. At 1952 calls
the stage has ample headroom to clear it *if* the model is accurate — but the bound
is what makes a negative result informative rather than merely underpowered. That is
the difference between this experiment and 0014's.

---

## 4. Exact steps to authorize

1. **Produce the semantic review.** ✅ DONE (commit `1a2dc7f`). The branch was pushed and
   the `jar-exp-0015-semantic-review` CI job dispatched on an isolated hosted runner (run
   `35473954572` / job `105979835931`, `success`); its real verdict, 38 falsification
   attempts and `calibration_manifest_sha256 = dc5d7a94…` were transcribed into
   `data/jar_exp_0015_semantic_review_20260919.json` and wired into the gate's
   `semantic_review_ref`. Nothing further is needed here unless a manifest-tracked file
   changes — which moves the pin and invalidates the record.
2. **Sign the approval.** Copy `data/jar_exp_0015_calibration_approval_PENDING.json`
   to `data/jar_exp_0015_calibration_approval_<YYYYMMDD>.json`. Set `approved: true`
   and `network_calls_authorized: true`. Fill `approved_by` and `approved_at`
   (timezone-aware ISO 8601). Drop the `_`-prefixed metadata keys. Do not touch the
   four binding fields.
3. **Wire the gate.** In `data/jar_exp_0015_calibration_gate_v01.json`, set
   `semantic_review_ref` and `owner_approval_ref` to those two paths. The gate is
   excluded from the manifest by design, so this does not move the pin.
4. **Confirm.** Run
   `python scripts/run_jar_exp_0015_live_calibration.py --preflight-only`. It
   executes the real preflight with zero network and no API key (it short-circuits
   before any credential check or SDK import), prints HEAD, the manifest hash, the
   decision and the ceilings, and exits `0` only on `READY_TO_CALIBRATE` with zero
   blockers (`2` otherwise). Anything but `0` means step 1–3 drifted.
5. **Execute.** `python scripts/run_jar_exp_0015_live_calibration.py` with
   `TYPESAFE_API_KEY` set. It re-checks preflight and exits non-zero unless
   `READY_TO_CALIBRATE`; it prints HEAD, the manifest, the decision and the ceilings
   before a single call; it writes observations, a receipt and a summary atomically
   via `os.replace` into `data/jar_exp_0015_calibration_live_20260920/`.

If any manifest-tracked file changes at any point, the pin moves and steps 1–4 must
be repeated. That is the control working, not a malfunction.

---

## 5. Fail-closed guarantees already proven

- **Budget is a hard stop, not an estimate.** The ledger reserves the full worst case
  before transport and claims the transport atomically. Checks 15–20 exercise budget
  denial, a two-thread race, resume, atomic claim, post-claim replay and request-id
  substitution; all fail closed with zero overspend.
- **Durable state is namespaced.** 0015's ledger and checkpoint live under
  `~/.aftergraph/research/jar-exp-0015/` (`*-v04`), never sharing 0014's frozen
  budget. Check 26 proves the paths are disjoint and outside the repo.
- **The authority boundary is advisory only.** `route_system_one_decision` returns a
  recommendation; `authority_bypassed` is `Literal[False]` and cannot be set true.
  Ineligible decision types fall back, authority-sensitive ambiguity escalates.
  Check 27 exercises both.
- **Calibration and holdout cannot contaminate each other.** Checks 28–29 feed a
  holdout case into calibration selection and vice versa; both raise.
- **The receipt binds the corpus.** A receipt whose observation ids do not equal the
  frozen case ids in order is refused (check 32).
- **0014 was not disturbed.** Check 36 proves commit-set disjointness: no commit
  touching a 0015 path touches a 0014-manifest path, and the working tree is clean
  for those paths. 0014's own CI pin is stale in this scratch clone for 0014-internal
  reasons (its post-freeze terminal-state commits edit `calibration_preflight.py`);
  re-validating that belongs to the canonical repo, not to 0015.
- **The human gates are the only thing between `NO_GO` and `READY_TO_CALIBRATE`.**
  `evidence/typesafe-cross-repo/verify_gate_plumbing_dry_run.py` (added in `add0042`,
  15/15 PASS) drives the *real* `evaluate_jar15_calibration_preflight` against a
  throwaway copy of the tree, flips all three human-gate blockers off at once to reach
  `READY_TO_CALIBRATE`, then reverts each gate alone to show it re-blocks with only
  that blocker. It never writes a persistent record and leaves the real tree `NO_GO`
  with the pin unchanged.

## 6. Known limitation carried forward

`finding=pricing validation cannot make provider-side post-check billing drift impossible`

Client-side validation narrows the drift window to the interval between the final
pricing check and provider billing. It cannot close it. This is the same Medium
finding 0014 accepted, with the same disposition: observable drift fails closed,
post-claim automatic retry is prohibited, and the residual risk is an
external-provider limitation rather than a local authority bypass.

---

## 7. What is committed, and what is left to a human

The 0015 execution path is committed on `feat/jar-exp-0015-execution-path` and pushed to
`origin` across eleven commits (`1984577` dataset freeze → `4cc9ddf` protocol v0.4
activation → `0b771f0` guarded calibration + semantic verifier → `f49aa91` pending
approval packet + this brief → `7646966`/`38ead85` cross-repo TypeSafe evidence →
`fad7fb9` the `jar-exp-0015-semantic-review` CI job → `add0042` the gate-plumbing dry-run
proof → `7a3d2cf` this brief's first refresh → `1d5cb40` the `fetch-depth: 0` checkout
hardening → `1a2dc7f` the Gate A close). The content-addressed pin `dc5d7a94…` reproduces
from `HEAD`, not merely from a working tree.

The only working-tree dirt left is unrelated to 0015 and none of it is a manifest path:
the signed `dist/*` submission bundles, `data/durability_fault_injection_results.json`,
and untracked `live_benchmark_dry_runs/`. They were deliberately never staged.

Gate A is closed by a real isolated CI run (see section 2). **What remains is one human
gate and two execution prerequisites:**

- **Gate B — owner signature.** Sign `data/jar_exp_0015_calibration_approval_PENDING.json`
  per section 4 step 2, then wire `owner_approval_ref` and set the gate's
  `network_calls_authorized: true`. This is the only gate left, and it is yours by the
  control's design — the agent that executes must not be the agent that authorizes the
  spend. It has not been fabricated here.
- **Execution prerequisites.** `pip install typesafe-sdk==0.7.0` (it is not installed in
  this clone) and set `TYPESAFE_API_KEY`. Until both are present the live script fails at
  `import typesafe_sdk` regardless of the gate state.

After those, `--preflight-only` exits `0` and the live calibration runs. Everything else is
built, verified and ready.
