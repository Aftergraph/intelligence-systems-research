# STUDY-012 Amendment 006 — Novita Sandbox Fabric and Provider Recovery Registry

**Status:** FROZEN-FOR-REVIEW — NO NEW FULL MATRIX AUTHORIZATION

## Purpose

After the provider-confounded v1 run and quota-stopped recovery-v2 run, this amendment separates **execution fabric** readiness from **inference-provider** readiness.

## Execution fabric

Novita Agent Sandbox is adopted as the prospective recovery execution environment.

Evidence:
- `novita-sandbox==2.1.1`
- sandbox create/command/kill verified live
- checkpoint phase 1: 5 rows
- sandbox A destroyed
- checkpoint imported into a new sandbox B
- final checkpoint: 12/12 unique traces
- no duplicate trace IDs
- no LLM inference was needed for this proof

The Novita $100 Sandbox credit applies to this execution environment and is not treated as Model API credit.

## Provider recovery disposition

The machine-readable source of truth is `data/study012_provider_recovery_registry_v01.json`.

At freeze time:
- NVIDIA Direct is READY with transient-retry semantics.
- Google Developer API is quota-blocked for the 480-call stratum.
- OpenRouter, Novita Model API, Z.ai and OpenCode Go are balance/resource blocked.
- BytePlus Ark credentials are valid but tested models are not activated.
- HF→Groq inference is authorization-blocked.
- OpenCode Zen free MiMo is restricted to OpenCode-client traffic.

## Scientific consequence

There is currently no second READY independent task inference route. Therefore:
- the 70-row recovery-v2 partial run remains `PARTIAL_EXECUTION_NOT_CONFIRMATORY`;
- it cannot be resumed with a substituted provider under the same execution ID;
- no new 960-row confirmatory run is admissible until a second task route passes a bounded live semantic readiness gate.

This amendment does **not** weaken the provider-independence requirement in order to rescue the study after observing failures.
