# v2.4 — Resilient Physical Pair + Live Intelligence Campaign

v2.4 turns the v2.3 outbound relay into a restart-resilient deployment seam and connects paired benchmark evidence to the statistical learning campaign.

## Durable relay generations

`RelayGenerationStore` persists the monotonically increasing registration generation for each worker identity in SQLite. A relay restart therefore does not reset a worker to generation 1. The next worker registration gets a strictly larger generation and can fence a pre-restart session at the application layer.

`relay-hub.json` may set:

```json
{"generation_store_file": "state/relay-generations.db"}
```

This is a crash-durable reference mechanism, not a consensus protocol. A horizontally replicated relay requires an external transactional/consensus store.

## Resumable execution journals

`JournalCheckpointStore` persists a coordinator-side `(worker_id, stream_id)` cursor plus the last independently verified execution-event hash. `ResumableJournalFollower` resumes polling from that cursor after process or relay reconnects and checks:

- worker identity;
- stream identity;
- exact cursor continuity;
- event sequence continuity;
- previous-hash continuity;
- canonical event digest;
- terminal head equality when the stream declares completion.

A remote cursor rollback or broken hash chain fails closed.

## Physical-pair doctor

`physical-pair-template` produces a secret-free two-node manifest for `worker:jonas-lenovo` and `worker:vds`. `physical-pair-doctor` validates configuration readiness, including distinct worker identities, distinct verifier trust domains, relay allowlisting and matching relay endpoints.

The doctor deliberately does **not** claim network reachability. A READY result means the configuration is internally coherent, not that either physical machine has connected.

## Live statistical campaign

`live-campaign` composes the existing paired benchmark runner with the statistical promotion gate:

```text
same coding fixtures
      ↓
frontier-control condition ─┐
                           ├─ exact (case_id, repeat) pairing
Jev-control condition ─────┘
      ↓
explicit operator-supplied token prices
      ↓
observed per-mission cost
      ↓
shadow → experiment → holdout
      ↓
VSR non-inferiority + FCR ceiling + lower CPVO
      ↓
PROMOTE / REJECT
```

No model/provider price is hard-coded as fact. `configs/live-campaign-pricing.example.json` contains zero placeholders and must be replaced with current, independently verified prices before a real campaign.

A campaign fails closed on missing or duplicate pairs. It does not manufacture counterfactual outcomes.

## Truth boundary

The v2.4 release proves restart-durable generation counters, resumable journal integrity and statistical campaign plumbing locally. It does not claim that Jonas-Lenovo and VDS executed a physical paired mission, and it does not claim a new authenticated TypeSafe/Dialagram campaign unless `live-campaign` is actually run on a network-capable host with valid runtime-only credentials.
