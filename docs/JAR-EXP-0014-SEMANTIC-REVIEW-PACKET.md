# JAR-EXP-0014 Semantic Independent Review Packet

Status: REVIEW_REQUESTED_NOT_SATISFIED  
Experiment: JAR-EXP-0014  
Review target code head: `1f1b2e52b3082596430a7c2ff89f911126c883af`  
Base: `1cd86e42f5c78fee12f4290b68213f0c5170120c`  
PR: #112  
Related blocker: #114

## Purpose

This packet exists to make the repository-required independent semantic review executable without granting the reviewer merge, calibration, network, spending, approval, or authority permissions.

The implementing agent must not treat this packet, CI, unit tests, or its own analysis as satisfying the independent-review requirement.

## Architecture boundary to preserve

Jev / System One is advisory only for bounded typed decisions such as model/tool routing, continue/stop, result sufficiency, human-gate detection, risk classification, retryability, and evidence-conflict classification.

It must not become:
- an authority plane;
- an execution truth source;
- a verifier;
- an approval source;
- a durable work-state authority.

AIE / Trust Gateway retain authority and admission. WORKS retains durable execution. Sentinel/deterministic verification retains verification.

## Frozen financial assumptions

Provider/model: TypeSafe AI `jev-1.13.0`

Frozen evidence assumptions:
- input price: USD 0.042 / 1M input tokens;
- output tokens: USD 0;
- documented context limit: 64k tokens/request;
- conservative local interpretation: 65,536 input tokens/request.

Independent arithmetic:
- max request reservation = ceil(65,536 × 0.042) = 2,753 micro-USD;
- 158 calibration cases = 434,974 micro-USD = USD 0.434974;
- frozen calibration ceiling = USD 0.44;
- frozen provider-call ceiling = 158;
- SDK retry policy = zero retries per call.

## Cost-guard state machine

Expected durable states:

`RESERVED → TRANSPORT_STARTED → COMPLETED`

Required semantics:
- reservation occurs before provider transport;
- exact same request-id/hash may resume while status remains `RESERVED` without consuming budget twice;
- different hash under the same request-id is rejected;
- transition to `TRANSPORT_STARTED` is atomic;
- only one worker can claim transport;
- once transport is claimed, replay/retry fails closed because provider delivery may be ambiguous;
- crash after reservation but before transport claim is resumable;
- crash after transport claim remains fail-closed;
- reservations are not refunded after transport ambiguity;
- cumulative spend authority is durable across restart and checkout changes.

## Pricing provenance / TOCTOU

The implementation validates the frozen TypeSafe pricing/context markers:
1. before creating/resuming a reservation; and
2. again immediately before the atomic transport claim.

The reviewer must explicitly decide whether the remaining non-atomic interval between provider documentation validation and the provider billing event is:
- an acceptable external-provider limitation under the frozen evidence model; or
- a blocker to calling this a verifiable USD hard stop.

Do not silently convert this limitation into a PASS.

## Exact request binding

Reservation SHA-256 binds the semantic payload:
- pinned model;
- projected decision-specific state;
- one frozen question contract.

The calibration runner must transport the same projected state, same decision, same concrete model and semantically equivalent typed question represented by that reservation.

Reviewer should inspect the SDK-object construction boundary for any mutation or implicit defaults that materially change billable request semantics after the reservation hash is created.

## Mandatory falsification attempts

Reviewer should attempt to produce a concrete sequence for each of these:

1. Budget overrun through concurrent reservations.
2. Budget overrun through concurrent resumes of the same request.
3. Fresh-ledger/reset-path bypass across checkout/restart.
4. Same request-id with a substituted request hash.
5. Same hash replay after transport claim.
6. Crash before transport and successful safe resume.
7. Crash after transport claim and accidental duplicate send.
8. Hidden SDK retry/fallback.
9. Pricing page drift before reservation.
10. Pricing drift after reservation but before transport claim.
11. Model alias/version drift.
12. Context-limit or price arithmetic under-reservation.
13. Malformed or missing provider usage.
14. Returned-model mismatch after a billed call.
15. Mutation between reserved semantic request and SDK transport.
16. Calibration execution while approval receipt is absent.
17. Calibration execution while network authorization is false.
18. Any path that lets Jev acquire authority or verification status.

## Current automated evidence

Exact code head `1f1b2e52b3082596430a7c2ff89f911126c883af`:
- focused two-phase cost/runner suite: 20/20 PASS;
- complete `tests/test_system_one_*.py`: 125/125 PASS;
- independent no-network cost-guard verifier: PASS;
- calibration preflight: `NO_GO`;
- current blockers exactly:
  - `calibration_approval_not_recorded`
  - `calibration_network_calls_not_authorized`
- hosted workflow run `35430294924`: SUCCESS;
- hosted jobs:
  - Python tests + audit;
  - JAR-EXP-0014 cost guard verifier;
  - Python conformance pack;
  - Node.js conformance;
  - Frozen artifact SHA verification;
  - STUDY-011 no-live-call pre-execution gate.

Automated evidence is not semantic independent review.

## Known review-history facts

- GitHub submitted reviews on PR #112: none as of this packet's creation.
- Copilot reviewer request did not register while PR remained draft.
- Draft status was intentionally not changed merely to obtain review.
- Two Hermes review workers failed to produce review evidence and were terminated.
- A local Qwen run produced a summary rather than the required hostile semantic verdict and is explicitly inadmissible as independent review evidence.

## Reviewer output contract

Return exactly one verdict:

- `PASS`
- `PASS_WITH_FINDINGS`
- `FAIL`

For every finding include:
- severity: Critical / High / Medium / Low;
- exact file + function/area;
- concrete failure or exploit sequence;
- whether current tests catch it;
- whether it is a spend/authority bypass or a design limitation;
- smallest safe fix.

A PASS must explicitly state that all 18 mandatory falsification attempts were considered.

## Protected actions

This review packet does not authorize:
- marking PR ready;
- merging;
- live calibration;
- network calls;
- spending;
- approval-receipt creation;
- changing Trust Gateway/AIE authority;
- confirmatory execution.
