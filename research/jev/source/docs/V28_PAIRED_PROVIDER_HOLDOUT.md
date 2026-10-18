# v2.8 — Paired Provider Holdout Execution

## Purpose

v2.7 can execute one mission through a cheap-first/frontier-escalation path and emit measured token/cost telemetry. v2.5 can evaluate paired campaign evidence and reserve promotion decisions to holdout. v2.8 connects those two evidence boundaries with a provider-agnostic paired execution harness.

## Invariants

1. **Same workload** — incumbent and candidate receive the same `case_id`, `repeat`, payload, and payload SHA-256.
2. **Phase blindness at execution** — the condition callback is not told whether a mission belongs to shadow, experiment, or holdout.
3. **Counterbalanced order** — deterministic seed + pair identity chooses which condition executes first, limiting systematic order bias while remaining reproducible.
4. **Fail-closed telemetry** — missing or negative token/cost/time counters reject the record before evidence evaluation.
5. **Holdout-only promotion evidence** — the runner delegates evaluation to `evaluate_evidence_campaign`; shadow/experiment outcomes cannot make holdout pass.
6. **No authority mutation** — the runner cannot activate a route, grant authority, or promote a model. It emits evidence only.

## Live campaign path

```text
preregister fixtures + repeats + phase allocation
                 ↓
        PairedHoldoutCampaignRunner
         ↙                    ↘
 incumbent provider        candidate/Jev path
         ↘                    ↙
      normalized paired telemetry
                 ↓
     EvidenceCampaignPolicy gate
                 ↓
    sealed campaign evidence bundle
                 ↓
       external promotion workflow
```

## Claim boundary

The implementation proves deterministic pairing, payload identity, telemetry validation, phase isolation, and holdout composition locally. It does **not** prove a live provider efficiency ratio. `live_provider_measurement=true` is metadata supplied by the caller and must only be set by an authenticated live execution environment. A 10× claim remains contingent on paired holdout evidence meeting the preregistered VSR/FCR/CPVO/FIE policy.
