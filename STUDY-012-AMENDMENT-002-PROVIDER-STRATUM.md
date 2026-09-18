# STUDY-012 Amendment 002 — Provider Stratum Replacement

**Status:** FROZEN-FOR-REVIEW — NO LIVE STUDY EXECUTION  
**Trigger:** Dialagram metadata readiness returned HTTP 402 on 2026-09-18 despite a credential being present.  
**Replacement:** M2 Dialagram -> Google Gemini API (direct).

## Evidence

Credential-safe metadata checks, with no model inference:
- OpenRouter: HTTP 200, 445 catalog entries; `google/gemma-4-31b-it` and `z-ai/glm-5.2` present.
- Google Gemini API direct: HTTP 200, 50 catalog entries; `models/gemini-2.5-flash` present.
- Dialagram: credential present, catalog HTTP 402.
- OpenAI: credential present, catalog HTTP 401.
- Anthropic: credential present, catalog HTTP 401.

## Frozen strata for review

- **M1:** OpenRouter — `google/gemma-4-31b-it` and `z-ai/glm-5.2`.
- **M2:** Google Gemini API direct — `gemini-2.5-flash`.

M2 is a direct provider endpoint and is therefore operationally independent from the OpenRouter gateway. No outcomes from Dialagram are silently substituted into Google observations. Provider results remain stratified.

The change affects provider selection only. R1/R2 hypotheses, workloads, conditions, oracles, sample design and analysis semantics do not change.

Owner approval remains required before live STUDY-012 inference.
