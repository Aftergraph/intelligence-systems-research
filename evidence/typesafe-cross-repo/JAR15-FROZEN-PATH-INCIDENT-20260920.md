# JAR-EXP-0015 frozen-path edit incident — 2026-09-20

**Status:** CLOSED / BYTES RESTORED  
**Evidence class:** repository-integrity incident record; not experiment outcome evidence.

## What happened

During repair of the owner-authority handoff, commit
`01bfc8d114b1e7fc65f0eabc85f231dfcf5bafe5` unintentionally edited two paths that
belong to `JAR15_CALIBRATION_INTEGRITY_PATHS`:

- `requirements-typesafe.txt`
- `scripts/verify_jar_exp_0015_semantic_review.py`

The edits were detected before any owner root existed and before any authorization or
provider call. The live calibration gate remained `NOT_AUTHORIZED`,
`owner_approval_ref=null`, and `network_calls_authorized=false`.

## Containment and restoration

Commit `d372d18f9d5e019b1d7ba9d283289e3ceb572171` restored both files byte-for-byte to
their verified `beb4db9b8f2e1b1fc5f1c24ae12246d0ec33c61d` blobs:

- `requirements-typesafe.txt` -> `0fdc024c39a13605cdf1b7f3bc53b7ffda4cceaf`
- `scripts/verify_jar_exp_0015_semantic_review.py` -> `63e6fa535cb885c47f4472cc95cc37cb2a7620a8`

No manifest pin was updated. No owner signature, approval record, ledger row, budget,
holdout authority, or network authorization was minted to compensate for the mistake.

## Durable fix

The post-authorization CI problem is now solved outside the frozen 30-path manifest:

- `evidence/typesafe-cross-repo/verify_jar15_semantic_review_state.py` runs the
  frozen semantic verifier unchanged in a detached exact-HEAD worktree with only the
  excluded mutable calibration gate projected to its pre-authorization view.
- It then verifies the real tree's Gate-B/preflight coherence, later-stage network
  closure, retry closure, and manifest pin.
- CI invokes that compatibility verifier instead of mutating the frozen verifier.

## Verification

A compare from `beb4db9b8f2e1b1fc5f1c24ae12246d0ec33c61d` to the repaired head showed no
net changes to any path in `JAR15_CALIBRATION_INTEGRITY_PATHS`. The compatibility
verifier's Git blob `dbe6dca6aa95b17ec43bc53dcd65f162fd15aa39` was independently
reconstructed and passed Python syntax compilation.

The intermediate commits are intentionally not force-rewritten away. Rewriting shared
branch history is a separate consequential action and requires explicit approval. This
record makes the incident visible instead of erasing it.
