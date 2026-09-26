# v2.10 — Authenticated Provider Request Lineage

v2.10 connects the existing real coding benchmark (`run_manifest`) to the v2.9 signed paired-evidence gate.

## New evidence chain

`fresh broken fixture -> live CodingAgent -> provider response IDs -> deterministic verifier -> paired benchmark row -> Ed25519 receipt -> sealed campaign bundle`

A v2.10 execution qualifies as `live_provider_measurement=true` only when every paired execution has:

1. a real provider/model identity;
2. at least one provider-issued response/request ID captured from the API response body;
3. authenticated provider credentials present at execution time;
4. HTTPS transport;
5. the deterministic benchmark verifier result;
6. a receipt binding payload, metrics, pair order, model/provider, and the complete request-ID set.

Signing alone never establishes liveness. Missing provider request lineage downgrades the bundle to non-live evidence.

## Signing key

Live CLI execution requires a persistent Ed25519 key supplied as either `--signing-key` (32 raw bytes) or `JEV_EVIDENCE_SIGNING_KEY_B64` (base64 of 32 raw bytes). The CLI intentionally refuses ephemeral signing keys for live evidence.

## Current truth state

This release makes the existing provider-backed benchmark path sealable and independently verifiable. The build container has no provider credentials, so no live campaign was executed here and no measured 10x claim is made.
