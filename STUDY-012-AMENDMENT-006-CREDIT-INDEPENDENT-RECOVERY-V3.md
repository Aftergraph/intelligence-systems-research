# STUDY-012 Amendment 006 — Credit-Independent Recovery v3

**Status:** FROZEN-FOR-READINESS — NO v3 FULL-MATRIX EXECUTION YET

## Trigger

Recovery-v2 was stopped fail-closed after Google Direct hit a documented free-tier request quota. Subsequent recovery forensics established:
- OpenRouter: HTTP 402 insufficient credits.
- Novita Model API: HTTP 403 not enough balance; Novita Sandbox compute itself is live and checkpoint/resume proven.
- Z.ai Direct: HTTP 429 code 1113, insufficient balance/resource package.
- Hugging Face inference route: HTTP 401; connected OAuth lacks inference-provider scope.
- OpenCode Go: transport fixed with session header, then HTTP 402 insufficient account funds.
- OpenCode Zen free: restricted to native OpenCode; native CLI transport is unsuitable in current remote execution context.
- Ollama Cloud: manifest pull succeeds, inference returns HTTP 403 because subscription payment is past due.
- Local Ollama Qwen3.6 and Nemotron 3.5 Lightning both return the exact semantic canary when `think:false`.
- Qwen3.6 is selected for throughput: the observed exact-token canary completed in ~0.55 s versus ~38.7 s for local Nemotron.

## v3 frozen task strata

M1 — Local Ollama:
- provider: `ollama-local`
- model: `qwen3.6:latest`
- transport: `http://127.0.0.1:11434/api/chat`
- `think:false`
- temperature 0
- no external model billing

M2 — NVIDIA Direct:
- provider: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- endpoint: NVIDIA hosted API
- frozen retry/backoff from v2

Observational judge:
- NVIDIA Direct `nvidia/nemotron-3-super-120b-a12b`
- remains observational only; J cannot establish canonical VERIFIED.

## Execution/evidence fabric

Novita Agent Sandbox remains the cloud checkpoint/evidence fabric. Two-sandbox checkpoint/restore has been empirically proven. Provider credentials are not persisted in sandbox checkpoints.

Inference execution remains on the Lenovo runner because M1 is a localhost Ollama provider. Novita does not receive access to the user's local Ollama daemon.

## Unchanged scientific design

- 8 R2 classes
- J / D / JD / DI
- 30 replicates per class×condition
- 960 observations
- deterministic oracles unchanged
- Sentinel independent verifier unchanged
- v1/v2/v3 results may not be silently pooled
- no provider substitution after first v3 observation

A final readiness gate must prove repeated local Qwen + NVIDIA task + NVIDIA judge semantic canaries before owner authorization becomes effective.
