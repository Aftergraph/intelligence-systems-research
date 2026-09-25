# v2.9 — Authenticated Live A/B Evidence

v2.9 closes a truth-gap left by earlier provider-backed campaign commands: a network request to a provider is not, by itself, authenticated experimental evidence.

## Invariants

1. Incumbent and candidate execute the same preregistered payload digest.
2. Pair ordering remains deterministic and counterbalanced.
3. Every execution must provide a provider/model/request attestation.
4. Every execution observation is sealed with an Ed25519 public-key receipt.
5. `live_provider_measurement=true` is permitted only when every observation is both authenticated and declares `evidence_origin=live-provider`.
6. Synthetic and replay observations may be signed, but can never become live evidence.
7. Promotion remains holdout-only and has no execution-authority side effect.
8. A verified live report must pass receipt verification before the evidence evaluator runs.

## Legacy correction

`live-campaign` and `live-campaign-v25` previously marked provider-backed runs as `live_provider_measurement=true` after execution. v2.9 narrows that claim: those legacy paths now record `provider_execution_performed=true` while leaving `live_provider_measurement=false` and `authenticated_live_ab_executed=false`, because they do not emit the v2.9 signed paired-provider receipt set.

## Remaining frontier

The code path for authenticated evidence is now implemented, but this release does **not** contain an actual provider-backed A/B run produced through the new receipt pipeline. Therefore no measured 10x claim is promoted by v2.9 itself.
