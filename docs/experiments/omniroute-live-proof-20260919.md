# OmniRoute live-proof experiment — 2026-09-19

## Scope

Controlled Windows GitHub Actions validation of OmniRoute v3.8.50 as a local OpenAI-compatible gateway. The experiment is isolated to the branch `experiment/omniroute-live-proof-20260919` and does not modify production routing.

## Verified local gateway behavior

- OmniRoute v3.8.50 installs and starts successfully on GitHub-hosted Windows Server 2025.
- Local dashboard: `http://localhost:20128`.
- Local API base: `http://localhost:20128/v1`.
- `/healthz` becomes reachable after startup.
- Authenticated local client access to the gateway works.
- `omniroute doctor` completes with 0 failures in the controlled runs.
- Evidence artifacts are uploaded by the workflow for every run.

## Live upstream observations

The live provider sweep executed through OmniRoute against current external free/keyless routes. On the controlled runner, none produced a successful completion in the recorded sweep.

Observed failures included:

- `pollinations/openai-fast` — HTTP 401: valid API key required.
- `pollinations/deepseek` — HTTP 401: valid API key required.
- `pollinations/qwen-coder` — HTTP 401: valid API key required.
- `aihorde/google/gemma-4-31b` — HTTP 406: model not known by the live upstream facade.
- `opencode/big-pickle` — HTTP 403: OpenCode free tier restricted to use from within OpenCode.
- `opencode/mimo-v2.5-free` — HTTP 403: same OpenCode free-tier restriction.
- `uncloseai/Lorbus/Qwen3.6-27B-int4-AutoRound` — HTTP 502 from the upstream path.

Earlier `auto` routing also attempted multiple candidates but terminated because the selected upstream credentials/catalog entries were unavailable or stale on the runner.

## Verdict

**Gateway proof:** PASS.

**Current keyless/free end-to-end inference proof on this runner:** NOT PROVEN.

The experiment shows that OmniRoute itself can be installed, started, authenticated locally, queried, diagnosed, and used as a routing gateway on Windows. It does **not** substantiate the stronger claim that a fresh installation currently provides reliable 100% free inference across the advertised external providers without provider credentials. The live external provider state observed on 2026-09-19 contradicts treating that claim as guaranteed behavior.

This is a bounded negative result, not a claim that all OmniRoute provider integrations are broken. Provider credentials, account-backed free tiers, local authenticated CLIs, or later upstream changes may produce different results.

## Evidence

Primary workflow: `.github/workflows/omniroute-live-proof.yml`

Key controlled run:
- run id: `35458707590`
- job id: `105938533376`
- branch head before final verdict-only change: `fbf8ee9a540788024caacce658840428df54865d`

The workflow stores:
- `host.json`
- `models.json`
- `direct-provider-attempts.json`
- `verdict.json`
- `doctor.json`
- OmniRoute stdout/stderr
- Node/npm/OmniRoute version evidence

## Interpretation boundary

A passing final workflow means the **experiment completed and produced evidence**. It must not be interpreted as a successful free-model completion unless `verdict.json` reports `directInference: true` and `inference-proof.json` exists.
