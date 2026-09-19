# Evidence package INDEX - JAR-EXP-0015 cross-repo TypeSafe advisory boundary

- **Experiment:** JAR-EXP-0015 (parent JAR-EXP-0014)
- **Date:** 2026-09-19
- **Status:** Proposed / read-only. No foreign tree modified. JAR-EXP-0015 remains NO_GO.
- **Frozen 0015 calibration manifest pin:** `dc5d7a94f333908abf09aebe1ca1dbf08f965e604eb2919d0b7a9ca70e149762`

This package records the cross-repo TypeSafe evidence surface for external validation.
It is generated against specific foreign working-copy commits (below) and the frozen
0015 record. Every artifact is content-addressed by SHA-256 so a validator can confirm
byte-for-byte what was reviewed.

## Foreign working copies read (read-only)

| Repo | Path | Branch | HEAD | Tree | Role |
|------|------|--------|------|------|------|
| war-room canonical main | `C:/Users/empir/workspace/war-room-audit-20260916` | `main` | `0313ad91ce96` | clean | harness reads EGAC |
| war-room OER p0 fail-close | `C:/Users/empir/workspace/war-room-oer-p0` | `fix/oer-p0-authority-boundary` | `4a545fb808d1` | clean | harness reads EGAC |
| war-room OER projection | `C:/Users/empir/workspace/war-room-oer-projection` | `feat/oer-war-room-projection` | `13d9ed4c0873` | clean | surface recon only |
| Fihim typesafe layer | `C:/Users/empir/fihim-typesafe-wt` | `feat/typesafe-intelligence-layer` | `34780e8f250c` | clean | emitter suite observed |

The harness `require()`s the real EGAC from the two war-room copies; the canary
re-asserts the OER fail-close and the 0015 pin. If a working copy is absent the
harness SKIPs (exit 2) rather than fabricating a result.

## Artifact manifest (SHA-256)

| File | SHA-256 | Role |
|------|---------|------|
| `ADR-TYPESAFE-ADVISORY-BOUNDARY.md` | `f57b45cea5344235a6612980e491c1cfb57b84a82cbcf8be65fe09a446a00583` | Architecture rule: advisory-only, tier_1-bound, OER precondition |
| `canary-output.txt` | `ebd814b7f39bac7c08cc4f27f9b373fd6a0430f46a8719b51fad3a7ee1757210` | Captured canary output (2/2 PASS) |
| `FIHIM-COVERAGE-REVIEW.md` | `77125ed9fa9b5c817329ad6f9de9ebc87a1c6c7b04be5411d6afb1f5f13e9e93` | Emitter-side review: suite passes, no change warranted |
| `HERMES-CANARY-PROPOSAL.md` | `5302cac092c81d7a77c29a1986fb32de6c11c9e0ba870d5eb69ddd5eae9278d7` | Proposed additive Hermes cron job (exact stanza; not applied) |
| `hermes-pin-projection-smoke.mjs` | `ec4f8c6a5b4cb74238984d6c14c93f01568da04f415bb1eb0b2113b82a6fe36f` | Hermes canary: pin-smoke + projection-smoke (read-only, zero-network) |
| `verification-output.txt` | `9af0928b84c47c55400efa92bff8d8221f70eccdd8895e9bd236a1e28e34bc82` | Captured harness output (8/8 PASS) |
| `verify_typesafe_bridge.mjs` | `f45b67249591b184128bd246135a119e3557bc257e67f065abb6cb881a0b1bc4` | Cross-repo harness: real EGAC (main + OER); proves I1..I5 + precondition |
| `war-room-typesafe-bridge.js` | `efb6348bcbacc84eedae55edced5ea64e85fc6faf5d92f498b86f1afc36ff4f7` | PROPOSED war-room patch: TypeSafe->EGAC tier_1 bridge (invariants I1..I5) |

`INDEX.md` itself is excluded (it embeds the others' hashes).

## Reproduction

```sh
# 1. Bridge invariants against the real foreign EGAC (read-only, zero-network):
node evidence/typesafe-cross-repo/verify_typesafe_bridge.mjs

# 2. Hermes canary (pin-smoke + projection-smoke, read-only, zero-network):
node evidence/typesafe-cross-repo/hermes-pin-projection-smoke.mjs

# 3. Fihim emitter suite (no change; observed pass):
npm --prefix ~/fihim-typesafe-wt run test:typesafe-intelligence

# 4. Frozen 0015 record still green + NO_GO:
python scripts/verify_jar_exp_0015_semantic_review.py
```

## Safety / non-goals

- **No signed `dist/` bundle is regenerated.** The modified `dist/*.zip` and
  `SUBMISSION_MANIFEST.json` in the working tree are left untouched; this package is
  0015-scoped only.
- **Foreign trees are read-only.** War-room (do-not-merge), Fihim, and the Hermes
  `ci-local`-gated convergence branch (4 dirty `renos/` files preserved) are not
  modified. The bridge and canary stanza are *proposed* patches for owner ratification.
- **JAR-EXP-0015 stays NO_GO.** No live TypeSafe/jev provider call is authorized; the
  three human gates (semantic review, owner approval, network authorization) remain
  closed. This package records authority; it never creates it.

