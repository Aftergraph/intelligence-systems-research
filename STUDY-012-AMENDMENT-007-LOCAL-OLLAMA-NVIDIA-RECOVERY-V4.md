# STUDY-012 Amendment 007 — Local-Ollama + NVIDIA Recovery v4

**Status:** FROZEN-FOR-READINESS — NO v4 FULL-MATRIX EXECUTION YET

This amendment supersedes Amendment 006 for execution planning only. It exists because `data/study012_provider_model_matrix_v3.json` was already frozen for an earlier NVIDIA cross-model design and MUST NOT be overwritten.

## Task strata

M1 — Local Ollama:
- provider ID: `ollama-local`
- model: `qwen3.6:latest`
- transport: `http://127.0.0.1:11434/api/chat`
- `think:false`
- temperature 0
- no external billing
- exact semantic canary observed: `LOCAL_READY_OK`

M2 — NVIDIA Direct:
- provider ID: `nvidia`
- model: `nvidia/nemotron-3-ultra-550b-a55b`
- existing truthful direct adapter
- transient retry/backoff only

Observational judge:
- NVIDIA Direct `nvidia/nemotron-3-super-120b-a12b`
- never canonical authority.

## Checkpoint/evidence fabric

Novita Agent Sandbox remains an external checkpoint/evidence fabric. Its two-sandbox checkpoint→kill→restore proof is preserved. It receives no local Ollama access and no provider secrets.

## Scientific invariants

No change to:
- eight R2 classes;
- J/D/JD/DI condition semantics;
- frozen workload fixtures/oracles;
- Sentinel independent verification;
- 30 replicates per class×condition;
- 960 nominal observations;
- prohibition on pooling prior confounded executions as if they were one preregistered run.

A new v4 readiness gate is required before full-matrix authorization.
