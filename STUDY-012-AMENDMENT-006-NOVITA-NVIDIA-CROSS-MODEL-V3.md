# STUDY-012 Amendment 006 — Novita Sandbox / NVIDIA Cross-Model Replication v3

**Status:** FROZEN-FOR-READINESS — NO v3 FULL-MATRIX EXECUTION YET

## Why a new replication

The provider-independent recovery attempts were falsified by real external constraints:

- OpenRouter paid: HTTP 402 insufficient credits.
- Google Direct: free-tier request quota exhausted during recovery-v2.
- Novita Model API: HTTP 403 insufficient model balance; the separate $100 Novita **Sandbox** credit is active and verified.
- Z.ai general API: HTTP 429 code 1113, insufficient balance/resource package.
- BytePlus general ModelArk: catalog is reachable but selected model is not activated.
- Hugging Face Inference Providers: local token/connector lacks inference authorization.

The v2 partial run (70 rows) is retained as S12-INC-002 and is not pooled.

## Execution fabric

Novita Agent Sandbox becomes the isolated execution environment:
- SDK `novita-sandbox==2.1.1`
- explicit checkpoint export
- resume into a different sandbox
- no secret persistence in checkpoints
- provider credentials injected ephemerally only when executing live inference

A two-sandbox proof already established 5-row checkpoint → kill → new sandbox → restore → 12/12 unique rows.

## v3 scientific scope

v3 intentionally drops any claim of **cross-provider model generalization**.

Task model strata are two distinct models on the same NVIDIA Direct provider:
- M1: `nvidia/nemotron-3-ultra-550b-a55b`
- M2: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`

Observational judge:
- J1: `nvidia/nemotron-3-super-120b-a12b`

This retains:
- R1 deterministic-grounding tests
- R2 eight-class adversarial traces
- J vs D vs JD vs DI semantics
- Sentinel-independent verification in DI
- exact frozen fixtures and deterministic oracles

It does **not** support provider-independence conclusions.

## Reliability changes

- shared NVIDIA concurrency: 1 for readiness, max 2 for execution
- max 2 attempts per call
- retry only timeout/URL error/HTTP 408/429/5xx
- no retries for 4xx authorization/payment/model-not-found
- append-only observations
- external checkpoint export after every completed batch
- fresh `S12V3-*` trace namespace
- v1/v2/v3 pooling forbidden

Full v3 execution requires a new exact readiness gate and a separate owner authorization after the freeze is complete.
