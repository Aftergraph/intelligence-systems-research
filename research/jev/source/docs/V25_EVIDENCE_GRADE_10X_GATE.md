# v2.5 — Evidence-Grade 10× Frontier-Efficiency Gate

## Purpose

v2.5 changes the research question from “did Jev reduce control-plane cost?” to the stricter question:

> Can the candidate control plane preserve verified outcome quality on a reserved holdout set while improving cost and frontier-intelligence efficiency, and is a 10× system-level target even mathematically attainable from control-plane offload alone?

The runtime does not claim 10×. It measures what portion of such a target is structurally reachable before a live campaign is run.

## Holdout isolation

A campaign is partitioned into three immutable evidence phases:

```text
shadow → experiment → holdout
```

Only the holdout slice may authorize promotion. Shadow and experiment data are reported, but cannot make a failing holdout pass.

Promotion requires all configured gates:

- paired holdout VSR non-inferiority;
- candidate FCR at or below the ceiling;
- lower candidate CPVO when required;
- minimum frontier-intelligence-efficiency ratio.

The VSR delta interval is a paired percentile bootstrap over exact `(case_id, repeat)` pairs. It is an empirical paired interval, not a proof of generalization.

## Control-plane tax decomposition

Each condition reports:

- generator tokens and cost;
- decision-plane tokens and cost;
- control-plane token tax;
- control-plane cost tax;
- total frontier tokens;
- frontier control tokens;
- frontier control token tax;
- verified outcomes per frontier token.

This avoids claiming that cheaper control decisions imply a 10× end-to-end gain.

## 10× feasibility bound

For an incumbent using frontier intelligence for both generation and control, the control-plane-only theoretical ceiling is:

```text
incumbent frontier tokens / incumbent generator frontier tokens
```

This assumes:

1. the candidate preserves verified outcomes;
2. generator token load stays equal to the incumbent;
3. all frontier control tokens disappear.

If that ceiling is below the requested target, the report explicitly states that generator/context/harness reductions are also required. The ceiling is a feasibility bound, not an observed benchmark result.

## Power planning

`campaign-plan-v25` provides a conservative independent-proportions approximation for initial sample-size planning. Because the live design is paired, pilot discordance should be used to refine the preregistered power model before a consequential promotion campaign.

## Evidence sealing

A v2.5 campaign can seal:

- benchmark manifest;
- operator-supplied pricing;
- raw result JSONL;
- campaign report;

into `CampaignEvidenceBundle/v1`. Every file is SHA-256 bound and the bundle itself is content-hashed. `campaign-verify-v25` fails when any bound artifact changes.

This is integrity evidence, not third-party timestamping or a public-key attestation.

## Post-promotion monitoring

`ContinuousRegressionMonitor` evaluates a bounded rolling window after promotion and can request quarantine when VSR, FCR, or CPVO cross configured limits.

Promotion therefore does not mean permanent trust.

## Commands

```bash
jev-one campaign-plan-v25 --baseline-vsr 0.90 --margin 0.02

jev-one campaign-report-v25 results.jsonl \
  --pricing configs/live-campaign-pricing.example.json \
  --incumbent qwen-frontier-control \
  --candidate qwen-jev-control \
  --shadow-pairs 5 --experiment-pairs 5 --holdout-pairs 20

jev-one live-campaign-v25 benchmarks/hermes_qwen_control_plane_ablation.yaml \
  --pricing configs/live-campaign-pricing.example.json \
  --incumbent qwen-frontier-control \
  --candidate qwen-jev-control

jev-one campaign-verify-v25 live-campaign-v25-results/campaign-evidence.v1.json
jev-one v25-demo
```

## Truth boundary

The bundled `v25-demo` uses synthetic records only. It proves holdout isolation, campaign math, feasibility analysis, evidence sealing, and regression quarantine. It is not evidence that TypeSafe Jev or Dialagram/Qwen achieved any particular live VSR, FCR, CPVO, TVO, or FIE ratio.
